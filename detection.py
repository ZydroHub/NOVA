import sys
import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib
import cv2
import hailo
import multiprocessing
import queue

from hailo_apps.python.core.common.hailo_logger import get_logger
from hailo_apps.python.core.gstreamer.gstreamer_app import app_callback_class
from hailo_apps.python.pipeline_apps.detection.detection_pipeline import GStreamerDetectionApp
from hailo_apps.python.core.gstreamer.gstreamer_helper_pipelines import (
    SOURCE_PIPELINE,
    INFERENCE_PIPELINE,
    INFERENCE_PIPELINE_WRAPPER,
    TRACKER_PIPELINE,
    USER_CALLBACK_PIPELINE,
    DISPLAY_PIPELINE,
)
from hailo_apps.python.core.common.buffer_utils import get_numpy_from_buffer

hailo_logger = get_logger(__name__)

# -----------------------------------------------------------------------------------------------
# Robust get_caps_from_pad implementation
# -----------------------------------------------------------------------------------------------
def robust_get_caps_from_pad(pad: Gst.Pad):
    """
    Robustly extracts width, height, and format from the GStreamer pad caps.
    Handles different structure objects returned by GStreamer bindings.
    """
    caps = pad.get_current_caps()
    if not caps:
        hailo_logger.warning("No caps found on pad.")
        return None, None, None

    structure = caps.get_structure(0)
    if not structure:
        return None, None, None

    width, height, format = None, None, None

    try:
        # Try different ways to access structure fields
        if hasattr(structure, 'get_value'):
            format = structure.get_value("format")
            width = structure.get_value("width")
            height = structure.get_value("height")
        elif hasattr(structure, 'get_string') and hasattr(structure, 'get_int'):
            # Some bindings use get_string/get_int
            success_w, width = structure.get_int("width")
            success_h, height = structure.get_int("height")
            if not success_w or not success_h:
                 # Try property access if get_int fails
                 width = structure.width if hasattr(structure, "width") else None
                 height = structure.height if hasattr(structure, "height") else None
            
            format = structure.get_string("format")
            if not format and hasattr(structure, "format"):
                format = structure.format
        else:
            # Fallback to direct attribute access (common in some gi versions)
            if hasattr(structure, "width"): width = structure.width
            if hasattr(structure, "height"): height = structure.height
            if hasattr(structure, "format"): format = structure.format

        # Sanity check and fallback parsing if needed
        if width is None or height is None:
             import re
             caps_str = caps.to_string()
             w_match = re.search(r'width=\(int\)(\d+)', caps_str)
             h_match = re.search(r'height=\(int\)(\d+)', caps_str)
             f_match = re.search(r'format=\(string\)([A-Z0-9]+)', caps_str)
             if w_match: width = int(w_match.group(1))
             if h_match: height = int(h_match.group(1))
             if f_match: format = f_match.group(1)

        return format, width, height
    except Exception as e:
        hailo_logger.error(f"Error parsing caps: {e}")
        return None, None, None

import threading
import time
import copy

# -----------------------------------------------------------------------------------------------
# Shared State for Integration
# -----------------------------------------------------------------------------------------------
class SharedState:
    def __init__(self):
        self.frame = None
        self.detections = []
        self.lock = threading.Lock()

    def update(self, frame, detections):
        with self.lock:
            self.frame = frame
            self.detections = detections

    def update_frame(self, frame):
        with self.lock:
            self.frame = frame

    def update_detections(self, detections):
        with self.lock:
            self.detections = detections

    def get_latest(self):
        with self.lock:
            return self.frame, self.detections

shared_state = SharedState()

# -----------------------------------------------------------------------------------------------
# User-defined class to be used in the callback function
# -----------------------------------------------------------------------------------------------
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.use_frame = True # Force frame usage for integration

# -----------------------------------------------------------------------------------------------
# User-defined callback function
# -----------------------------------------------------------------------------------------------
def app_callback(element, buffer, user_data):
    if buffer is None:
        return Gst.PadProbeReturn.OK

    pad = element.get_static_pad("src")
    format, width, height = robust_get_caps_from_pad(pad)
    
    # DEBUG: Print caps info occasionally
    print(f"DEBUG: app_callback detected caps: Fmt={format}, W={width}, H={height}")

    frame = None
    if user_data.use_frame and format is not None and width is not None and height is not None:
        frame = get_numpy_from_buffer(buffer, format, width, height)
    else:
        # Check if we are failing to get caps
        if user_data.use_frame:
             print(f"WARNING: Missing caps info. Fmt={format}, W={width}, H={height}")

    # Get detections
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    detection_list = []
    for detection in detections:
        label = detection.get_label()
        confidence = detection.get_confidence()
        bbox = detection.get_bbox()
        
        detection_list.append({
            "label": label,
            "confidence": confidence,
            "bbox": [bbox.xmin(), bbox.ymin(), bbox.xmax(), bbox.ymax()]
        })

    # Update shared state
    if frame is not None:
        # NOTE: Frame is RGB. If you need BGR for OpenCV elsewhere, convert it there.
        # For web streaming (MJPEG), RGB is often converted to JPEG which is fine.
        shared_state.update(frame, detection_list)

    return Gst.PadProbeReturn.OK

# -----------------------------------------------------------------------------------------------
# Improved Picamera Thread with Robust Cleanup
# -----------------------------------------------------------------------------------------------
def robust_picamera_thread(pipeline, video_width, video_height, video_format, picamera_config=None):
    hailo_logger.info("robust_picamera_thread started")
    appsrc = pipeline.get_by_name("app_source")
    if appsrc is None:
        hailo_logger.error("app_source not found in pipeline")
        return

    appsrc.set_property("is-live", True)
    appsrc.set_property("format", Gst.Format.TIME)
    
    # Retry mechanism for camera acquisition
    max_retries = 3
    picam2 = None
    
    for attempt in range(max_retries):
        try:
            from picamera2 import Picamera2
            picam2 = Picamera2()
            
            if picamera_config is None:
                # Use a reliable configuration
                main = {"size": (1280, 720), "format": "RGB888"}
                lores = {"size": (video_width, video_height), "format": "RGB888"}
                controls = {"FrameRate": 30}
                config = picam2.create_preview_configuration(main=main, lores=lores, controls=controls)
            else:
                config = picamera_config

            picam2.configure(config)
            picam2.start() 
            hailo_logger.info("Camera acquired and started successfully.")
            break
        except Exception as e:
            hailo_logger.warning(f"Failed to acquire camera (attempt {attempt+1}/{max_retries}): {e}")
            if picam2:
                try:
                    picam2.stop()
                    picam2.close()
                except:
                    pass
                picam2 = None
            time.sleep(1.0) # Wait before retry

    if picam2 is None:
        hailo_logger.error("Could not acquire camera after retries.")
        # Signal error or exit?
        return

    try:
        # Configuration successful, proceed with loop
        lores_stream = config["lores"]
        format_str = "RGB" if lores_stream["format"] == "RGB888" else video_format
        width, height = lores_stream["size"]
        
        appsrc.set_property(
            "caps",
            Gst.Caps.from_string(
                f"video/x-raw, format={format_str}, width={width}, height={height}, framerate=30/1, pixel-aspect-ratio=1/1"
            ),
        )

        frame_count = 0
        while True:
            # Exit quickly when stop is requested (e.g. user pressed back)
            if _process_stop_event is not None and _process_stop_event.is_set():
                hailo_logger.info("Stop event set; exiting camera thread.")
                break

            # Non-blocking capture if possible, but capture_array is blocking.
            # We trust that GStreamer flow return will tell us when to stop.
            try:
                # Add a small timeout to allow checking for exit signals if supported by lib
                # But picamera2 capture_array doesn't support timeout natively in all versions?
                # It waits for a request.
                frame_data = picam2.capture_array("lores")
            except Exception as e:
                hailo_logger.warning(f"Capture error: {e}")
                break

            if frame_data is None:
                hailo_logger.warning("Frame capture returned None")
                break

            frame = cv2.cvtColor(frame_data, cv2.COLOR_BGR2RGB)
            buffer = Gst.Buffer.new_wrapped(frame.tobytes())
            buffer_duration = Gst.util_uint64_scale_int(1, Gst.SECOND, 30)
            buffer.pts = frame_count * buffer_duration
            buffer.duration = buffer_duration
            
            try:
                ret = appsrc.emit("push-buffer", buffer)
                if ret != Gst.FlowReturn.OK:
                    hailo_logger.info(f"Pipeline stopped accepting buffers ({ret}). Stopping camera thread.")
                    break
            except Exception as e:
                hailo_logger.error(f"Error pushing buffer: {e}")
                break

            frame_count += 1
            
    finally:
        hailo_logger.info("Closing camera resources...")
        if picam2:
            try:
                picam2.stop()
                picam2.close()
            except Exception as e:
                hailo_logger.error(f"Error closing camera: {e}")
        hailo_logger.info("Camera thread exited.")


# -----------------------------------------------------------------------------------------------
# Custom GStreamer Application to fix RGB issue and threading/args quirks
# -----------------------------------------------------------------------------------------------
class CustomGStreamerDetectionApp(GStreamerDetectionApp):
    def __init__(self, app_callback, user_data, headless=False):
        # PATCH: Temporarily mock signal.signal to avoid ValueError in thread
        import signal
        original_signal = signal.signal
        
        def mock_signal(sig, handler):
            hailo_logger.warning(f"Skipping signal registration for {sig} in background thread")
        
        signal.signal = mock_signal
        
        self.force_headless = headless
        
        # We still need to clean sys.argv for GStreamerApp if --headless remains
        if "--headless" in sys.argv:
            sys.argv.remove("--headless")

        try:
             super().__init__(app_callback, user_data)
        finally:
             signal.signal = original_signal

    def run(self):
        # Override run to use our robust_picamera_thread
        from hailo_apps.python.core.common.defines import RPI_NAME_I
        
        hailo_logger.debug("Running CustomGStreamerDetectionApp main loop")
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.bus_call, self.loop)

        self._connect_callback()

        hailo_display = self.pipeline.get_by_name("hailo_display")
        if hailo_display is None and not getattr(self.options_menu, "ui", False):
            hailo_logger.warning("hailo_display not found in pipeline")

        # Disable QoS to prevent frame drops
        from hailo_apps.python.core.gstreamer.gstreamer_common import disable_qos
        disable_qos(self.pipeline)

        if self.options_menu.use_frame:
            from hailo_apps.python.core.gstreamer.gstreamer_common import display_user_data_frame
            hailo_logger.debug("Starting display_user_data_frame process")
            display_process = multiprocessing.Process(
                target=display_user_data_frame, args=(self.user_data,)
            )
            display_process.start()

        if self.source_type == RPI_NAME_I:
            hailo_logger.debug("Starting robust_picamera_thread")
            picam_thread = threading.Thread(
                target=robust_picamera_thread,
                args=(self.pipeline, self.video_width, self.video_height, self.video_format),
            )
            self.threads.append(picam_thread)
            picam_thread.start()

        self.pipeline.set_state(Gst.State.PAUSED)
        self.pipeline.set_latency(self.pipeline_latency * Gst.MSECOND)
        self.pipeline.set_state(Gst.State.PLAYING)

        if self.watchdog_enabled and not self.watchdog_running:
            self.watchdog_running = True
            self.watchdog_thread = threading.Thread(target=self._watchdog_monitor, daemon=True)
            self.watchdog_thread.start()

        if self.options_menu.dump_dot:
            GLib.timeout_add_seconds(3, self.dump_dot_file)

        self.loop.run()

        try:
            hailo_logger.debug("Cleaning up after loop exit")
            self.user_data.running = False
            self.pipeline.set_state(Gst.State.NULL)
            if self.options_menu.use_frame:
                display_process.terminate()
                display_process.join()
            for t in self.threads:
                t.join()
        except Exception as e:
            hailo_logger.error(f"Error during cleanup: {e}")
        finally:
            if self.error_occurred:
                hailo_logger.error("Exiting with error")
                # sys.exit(1) # Do not exit the whole process in thread!
            else:
                hailo_logger.info("Exiting successfully")
                # sys.exit(0)

    def get_pipeline_string(self):
        source_pipeline = SOURCE_PIPELINE(
            video_source=self.video_source,
            video_width=self.video_width,
            video_height=self.video_height,
            frame_rate=self.frame_rate,
            sync=self.sync,
        )
        detection_pipeline = INFERENCE_PIPELINE(
            hef_path=self.hef_path,
            post_process_so=self.post_process_so,
            post_function_name=self.post_function_name,
            batch_size=self.batch_size,
            config_json=self.labels_json,
            additional_params=self.thresholds_str,
        )
        detection_pipeline_wrapper = INFERENCE_PIPELINE_WRAPPER(detection_pipeline)
        tracker_pipeline = TRACKER_PIPELINE(class_id=1)
        user_callback_pipeline = USER_CALLBACK_PIPELINE()
        
        if self.force_headless:
             display_pipeline = f"fakesink name=hailo_display sync={self.sync}"
        else:
             display_pipeline = DISPLAY_PIPELINE(
                video_sink=self.video_sink, sync=self.sync, show_fps=self.show_fps
            )

        pipeline_string = (
            f"{source_pipeline} ! "
            f"{detection_pipeline_wrapper} ! "
            f"{tracker_pipeline} ! "
            f"videoconvert ! video/x-raw,format=RGB ! "
            f"{user_callback_pipeline} ! "
            f"{display_pipeline}"
        )
        hailo_logger.debug("Pipeline string: %s", pipeline_string)
        return pipeline_string

    def shutdown(self, signum=None, frame=None):
        """Override to quit the main loop immediately instead of blocking on pipeline state.
        Pipeline and thread cleanup is done in run()'s finally block. This avoids deadlock
        where the main thread blocks in set_state(PAUSED) waiting for the pipeline while
        the camera thread is blocked in capture_array()."""
        hailo_logger.warning("Shutdown initiated (quitting loop first)")
        if self.watchdog_running:
            self.watchdog_running = False
            if self.watchdog_thread and self.watchdog_thread.is_alive():
                self.watchdog_thread.join(timeout=2.0)
            self.watchdog_thread = None
        # Quit the loop so run() returns and finally block does pipeline NULL + thread joins.
        GLib.idle_add(self.loop.quit)

    def run_with_frame_queue(self, detection_queue, stop_event, video_width, video_height):
        """Run pipeline with frames from detection_queue (5 fps) instead of camera thread."""
        from hailo_apps.python.core.gstreamer.gstreamer_common import disable_qos

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.bus_call, self.loop)
        self._connect_callback()
        disable_qos(self.pipeline)

        appsrc = self.pipeline.get_by_name("app_source")
        if appsrc is None:
            hailo_logger.error("app_source not found for queue input")
            return
        appsrc.set_property("is-live", True)
        appsrc.set_property("format", Gst.Format.TIME)
        appsrc.set_property(
            "caps",
            Gst.Caps.from_string(
                f"video/x-raw, format=RGB, width={video_width}, height={video_height}, "
                "framerate=5/1, pixel-aspect-ratio=1/1"
            ),
        )

        def feeder_loop():
            frame_count = 0
            while not stop_event.is_set():
                try:
                    frame = detection_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                if frame is None:
                    break
                buffer = Gst.Buffer.new_wrapped(frame.tobytes())
                buffer_duration = Gst.util_uint64_scale_int(1, Gst.SECOND, 5)
                buffer.pts = frame_count * buffer_duration
                buffer.duration = buffer_duration
                try:
                    ret = appsrc.emit("push-buffer", buffer)
                    if ret != Gst.FlowReturn.OK:
                        break
                except Exception as e:
                    hailo_logger.error(f"Feeder push error: {e}")
                    break
                frame_count += 1
                time.sleep(0.2)

        feeder_thread = threading.Thread(target=feeder_loop, daemon=True)
        self.threads.append(feeder_thread)
        feeder_thread.start()

        def monitor_stop():
            while not stop_event.is_set():
                time.sleep(0.5)
            hailo_logger.info("Stop event received; shutting down detection app.")
            GLib.idle_add(self.shutdown)

        stop_monitor = threading.Thread(target=monitor_stop, daemon=True)
        stop_monitor.start()

        self.pipeline.set_state(Gst.State.PAUSED)
        self.pipeline.set_latency(self.pipeline_latency * Gst.MSECOND)
        self.pipeline.set_state(Gst.State.PLAYING)
        self.loop.run()

        try:
            self.pipeline.set_state(Gst.State.NULL)
            for t in self.threads:
                t.join(timeout=2.0)
        except Exception as e:
            hailo_logger.error(f"Cleanup error: {e}")

# -----------------------------------------------------------------------------------------------
# Stream process (30 fps, no Hailo) + Detection process (5 fps, Hailo)
# -----------------------------------------------------------------------------------------------
stream_process = None
stream_consumer_thread = None
stream_queue = None
stream_stop_event = multiprocessing.Event()
detection_enabled = None  # multiprocessing.Value('b', False)
detection_queue = None   # multiprocessing.Queue for frames to Hailo

detection_process = None
detection_monitor_thread = None
detections_output_queue = None
detection_stop_event = multiprocessing.Event()

# Used by robust_picamera_thread in standalone run(); None when not in queue-fed detection process
_process_stop_event = None

# Stream ref-count and shutdown (camera view open/close)
ref_count = 0
shutdown_timer = None
session_lock = threading.Lock()

# Detection process dimensions (must match camera_stream)
DETECTION_WIDTH = 640
DETECTION_HEIGHT = 384


def _stream_consumer_loop(q):
    """Consumes stream_queue in main process; updates shared_state.frame (30 fps)."""
    while True:
        try:
            frame = q.get(timeout=1.0)
            shared_state.update_frame(frame)
        except queue.Empty:
            if stream_process is None or not stream_process.is_alive():
                break
            continue
        except Exception as e:
            hailo_logger.debug("Stream consumer error: %s", e)
            break


def run_detection_process(detection_queue_in, detections_output_queue_out, stop_event_in):
    """
    Runs the detection app in a separate process. Reads frames from detection_queue_in at 5 fps,
    runs Hailo pipeline, pushes detections to detections_output_queue_out.
    """
    try:
        import setproctitle
        setproctitle.setproctitle("pocket-ai-detection")
    except ImportError:
        pass

    hailo_logger.info("Starting Detection Process (5 fps from queue).")

    if "--input" not in sys.argv:
        sys.argv.extend(["--input", "rpi"])
    if "--width" not in sys.argv:
        sys.argv.extend(["--width", str(DETECTION_WIDTH)])
    if "--height" not in sys.argv:
        sys.argv.extend(["--height", str(DETECTION_HEIGHT)])

    def process_callback(element, buffer, user_data):
        if buffer is None:
            return Gst.PadProbeReturn.OK

        pad = element.get_static_pad("src")
        format, width, height = robust_get_caps_from_pad(pad)

        roi = hailo.get_roi_from_buffer(buffer)
        detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

        detection_list = []
        for detection in detections:
            bbox = detection.get_bbox()
            detection_list.append({
                "label": detection.get_label(),
                "confidence": detection.get_confidence(),
                "bbox": [bbox.xmin(), bbox.ymin(), bbox.xmax(), bbox.ymax()]
            })

        try:
            detections_output_queue_out.put_nowait(detection_list)
        except Exception:
            pass
        return Gst.PadProbeReturn.OK

    user_data = user_app_callback_class()
    user_data.use_frame = False
    app = CustomGStreamerDetectionApp(process_callback, user_data, headless=True)

    try:
        app.run_with_frame_queue(
            detection_queue_in, stop_event_in,
            video_width=DETECTION_WIDTH, video_height=DETECTION_HEIGHT
        )
    except Exception as e:
        hailo_logger.error(f"Detection process exception: {e}")
    finally:
        hailo_logger.info("Detection process exiting.")

def _detection_monitor_loop(q):
    """Reads detections from queue and updates shared_state.detections. Main process thread."""
    while True:
        try:
            if detection_process is None or not detection_process.is_alive():
                break
            try:
                detections = q.get(timeout=1.0)
                shared_state.update_detections(detections)
            except queue.Empty:
                continue
        except Exception as e:
            hailo_logger.debug("Detection monitor error: %s", e)
            break


def _spawn_stream_process():
    """Start stream process and stream consumer thread. Caller holds session_lock for ref_count."""
    global stream_process, stream_consumer_thread, stream_queue, stream_stop_event
    global detection_enabled, detection_queue

    import camera_stream

    stream_stop_event = multiprocessing.Event()
    stream_stop_event.clear()
    stream_queue = multiprocessing.Queue(maxsize=2)
    detection_enabled = multiprocessing.Value("b", False)
    detection_queue = multiprocessing.Queue(maxsize=2)

    stream_process = multiprocessing.Process(
        target=camera_stream.run_stream_process,
        args=(stream_queue, stream_stop_event, detection_enabled, detection_queue),
        kwargs={"width": DETECTION_WIDTH, "height": DETECTION_HEIGHT},
        daemon=False,
    )
    stream_process.start()

    stream_consumer_thread = threading.Thread(target=_stream_consumer_loop, args=(stream_queue,), daemon=True)
    stream_consumer_thread.start()


def _spawn_detection_process():
    """Start detection process and detection monitor thread. Requires stream already running (detection_queue set)."""
    global detection_process, detection_monitor_thread, detections_output_queue, detection_stop_event
    global detection_queue, detection_enabled

    if detection_queue is None or detection_enabled is None:
        hailo_logger.warning("Cannot start detection: stream not running.")
        return

    detection_stop_event.clear()
    detections_output_queue = multiprocessing.Queue(maxsize=4)

    detection_process = multiprocessing.Process(
        target=run_detection_process,
        args=(detection_queue, detections_output_queue, detection_stop_event),
        daemon=False,
    )
    detection_process.start()

    detection_monitor_thread = threading.Thread(
        target=_detection_monitor_loop,
        args=(detections_output_queue,),
        daemon=True,
    )
    detection_monitor_thread.start()

    detection_enabled.value = True


def start_detection(session_id=None):
    """
    Starts the stream process (30 fps camera, no Hailo) if not already running.
    Increments ref count for camera view. Returns shared_state for video feed.
    """
    global stream_process, ref_count, shutdown_timer

    with session_lock:
        ref_count += 1
        hailo_logger.info(f"Start stream requested (session_id={session_id}). Ref count: {ref_count}")

        if shutdown_timer is not None:
            shutdown_timer.cancel()
            shutdown_timer = None

        if stream_process is not None and stream_process.is_alive():
            hailo_logger.info("Stream process already running.")
            return shared_state

        hailo_logger.info("Spawning stream process (30 fps, no Hailo)...")
        _spawn_stream_process()

    return shared_state


def stop_detection(session_id=None):
    """Decrements ref count. If 0, schedules stream shutdown. Also stops detection if active."""
    global ref_count, shutdown_timer

    with session_lock:
        if ref_count > 0:
            ref_count -= 1
        hailo_logger.info(f"Stop stream requested (session_id={session_id}). Ref count: {ref_count}")

        if ref_count == 0:
            stop_detection_mode()
            if shutdown_timer is not None:
                shutdown_timer.cancel()
            # 1.5s delay so React Strict Mode's second mount can send start and cancel this
            shutdown_timer = threading.Timer(1.5, perform_actual_shutdown)
            shutdown_timer.start()

    return True


def perform_actual_shutdown():
    """Stops the stream process. Does not hold lock during join."""
    global stream_process, stream_queue, stream_stop_event
    global detection_enabled, detection_queue, shutdown_timer, ref_count

    with session_lock:
        if ref_count > 0:
            return
        proc = stream_process
        hailo_logger.info("Performing stream shutdown...")

    stream_stop_event.set()
    if proc and proc.is_alive():
        proc.join(timeout=5.0)
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=2.0)
        if proc.is_alive():
            proc.kill()
            proc.join()

    with session_lock:
        stream_process = None
        stream_queue = None
        shutdown_timer = None
        if ref_count > 0:
            hailo_logger.info("Ref count > 0 after shutdown; spawning new stream.")
            _spawn_stream_process()


def start_detection_mode(session_id=None):
    """Starts the Hailo detection process (5 fps). Stream must already be running."""
    global detection_process, detection_enabled

    with session_lock:
        if detection_process is not None and detection_process.is_alive():
            hailo_logger.info("Detection already running.")
            return True
        if stream_process is None or not stream_process.is_alive():
            hailo_logger.warning("Stream not running; start camera first.")
            return False
        _spawn_detection_process()
    return True


def stop_detection_mode(session_id=None):
    """Stops the Hailo detection process and clears detections."""
    global detection_process, detection_monitor_thread, detections_output_queue
    global detection_stop_event, detection_enabled

    with session_lock:
        if detection_enabled is not None:
            detection_enabled.value = False
        proc = detection_process
        detection_process = None

    if proc and proc.is_alive():
        detection_stop_event.set()
        proc.join(timeout=5.0)
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=2.0)
        if proc.is_alive():
            proc.kill()
            proc.join()

    shared_state.update_detections([])
    detection_stop_event = multiprocessing.Event()
    hailo_logger.info("Detection mode stopped.")
    return True

def main():
    # Standalone run
    hailo_logger.info("Starting Custom Detection App (Standalone).")
    
    if "--input" not in sys.argv:
        sys.argv.extend(["--input", "rpi"])

    user_data = user_app_callback_class()
    app = CustomGStreamerDetectionApp(app_callback, user_data)
    app.run()

if __name__ == "__main__":
    main()
