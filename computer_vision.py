import sys
import time
import threading
import signal
import gi
import cv2
import numpy as np

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

# Ensure Gstreamer is initialized
Gst.init(None)

# -----------------------------------------------------------------------------------------------
# 1. SHARED MEMORY
# -----------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------
# 1. SHARED MEMORY & UTILS
# -----------------------------------------------------------------------------------------------

class FrameManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._current_frame = None
        self._metadata = {}

    def update(self, frame, metadata={}):
        with self._lock:
            self._current_frame = frame
            self._metadata = metadata

    def get_latest(self):
        with self._lock:
            if self._current_frame is None:
                return None, {}
            return self._current_frame.copy(), self._metadata.copy()

frame_manager = FrameManager()

def get_latest_frame():
    return frame_manager.get_latest()

# -----------------------------------------------------------------------------------------------
# 2. DEBUGGING & GSTREAMER UTILITIES
# -----------------------------------------------------------------------------------------------
class CapsCache:
    def __init__(self):
        self.fmt = None
        self.width = 0
        self.height = 0
        self.valid = False

    def reset(self):
        """Invalidate cache so the next pipeline can negotiate fresh caps."""
        self.fmt = None
        self.width = 0
        self.height = 0
        self.valid = False

    def update(self, pad):
        if self.valid: return
        
        try:
            caps = pad.get_current_caps()
            if not caps: return

            structure = caps.get_structure(0)
            if hasattr(structure, 'get_int'):
                success_w, self.width = structure.get_int("width")
                success_h, self.height = structure.get_int("height")
                self.fmt = structure.get_value("format") if hasattr(structure, "get_value") else structure.get_string("format")
            elif hasattr(structure, 'width') and hasattr(structure, 'height'):
                self.width = structure.width
                self.height = structure.height
                self.fmt = structure.format
            else:
                 # Fallback parsing
                caps_str = caps.to_string()
                import re
                w_match = re.search(r'width=\(int\)(\d+)', caps_str)
                h_match = re.search(r'height=\(int\)(\d+)', caps_str)
                f_match = re.search(r'format=\(string\)([A-Z0-9]+)', caps_str)
                
                if w_match: self.width = int(w_match.group(1))
                if h_match: self.height = int(h_match.group(1))
                if f_match: self.fmt = f_match.group(1)

            if self.width and self.height:
                self.valid = True

        except Exception as e:
            print(f"[DEBUG] Error parsing caps: {e}")

global_caps_cache = CapsCache()

def custom_get_caps_from_pad(pad):
    """
    Extracts width, height, and format from the GStreamer pad caps.
    Uses a global cache to avoid repetitive parsing.
    """
    if global_caps_cache.valid:
        return global_caps_cache.fmt, global_caps_cache.width, global_caps_cache.height
    
    global_caps_cache.update(pad)
    return global_caps_cache.fmt, global_caps_cache.width, global_caps_cache.height

def get_numpy_from_buffer_safe(buffer, format, width, height):
    """Safe wrapper for buffer conversion."""
    try:
        success, map_info = buffer.map(Gst.MapFlags.READ)
        if not success:
            raise RuntimeError("Could not map buffer data")
        
        try:
            # We are forcing RGB in the pipeline now, so we assume 3 channels
            frame = np.ndarray(
                shape=(height, width, 3),
                dtype=np.uint8,
                buffer=map_info.data
            )
            return frame.copy()
        finally:
            buffer.unmap(map_info)
            
    except Exception as e:
        print(f"[DEBUG] Buffer conversion error: {e}")
        return None

# -----------------------------------------------------------------------------------------------
# 3. GLOBAL STATE
# -----------------------------------------------------------------------------------------------
current_thread = None
current_app = None

def start_task(target_func):
    global current_thread
    stop_task()
    current_thread = threading.Thread(target=target_func)
    current_thread.daemon = True 
    current_thread.start()

def stop_task():
    global current_app, current_thread
    
    # 1. Invalidate caps cache so the next pipeline gets fresh caps
    global_caps_cache.reset()
    
    if current_app:
        try:
            # Follow the Hailo framework's own shutdown sequence:
            # PLAYING → PAUSED → READY → NULL (with delays between each)
            if hasattr(current_app, 'pipeline') and current_app.pipeline is not None:
                current_app.pipeline.set_state(Gst.State.PAUSED)
                GLib.usleep(100000)  # 100ms
                current_app.pipeline.set_state(Gst.State.READY)
                GLib.usleep(100000)  # 100ms
                current_app.pipeline.set_state(Gst.State.NULL)
            
            # Now quit the GLib main loop (this lets app.run() return)
            if hasattr(current_app, 'loop') and current_app.loop is not None:
                if current_app.loop.is_running():
                    GLib.idle_add(current_app.loop.quit)
        except Exception as e:
            print(f"Error stopping app: {e}")
        current_app = None

    if current_thread and current_thread.is_alive():
        current_thread.join(timeout=5.0)
        current_thread = None
    
    # Delay to ensure the camera device is fully released
    time.sleep(0.5)

# -----------------------------------------------------------------------------------------------
# 4. WORKER FUNCTIONS
# -----------------------------------------------------------------------------------------------
try:
    import hailo
    from hailo_apps.python.core.gstreamer.gstreamer_app import GStreamerApp, app_callback_class
    from hailo_apps.python.core.gstreamer.gstreamer_helper_pipelines import (
        SOURCE_PIPELINE, INFERENCE_PIPELINE, INFERENCE_PIPELINE_WRAPPER, 
        TRACKER_PIPELINE, USER_CALLBACK_PIPELINE
    )
    from hailo_apps.python.core.common.core import get_pipeline_parser
    from hailo_apps.python.pipeline_apps.detection.detection_pipeline import GStreamerDetectionApp
    from hailo_apps.python.pipeline_apps.pose_estimation.pose_estimation_pipeline import GStreamerPoseEstimationApp
except ImportError:
    pass

def run_app_safely(app):
    original_signal = signal.signal
    def no_op(*args, **kwargs): pass
    signal.signal = no_op
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            app.run()
            # If run() returns normally (not error), break loop
            break
        except SystemExit:
            # GStreamerApp.run() calls sys.exit() on completion — catch it
            # so it doesn't kill the whole application from a daemon thread.
            break
        except Exception as e:
            print(f"App run error (Attempt {retry_count+1}/{max_retries}): {e}")
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(1) # Wait before retry
                # Reset caps cache just in case
                global_caps_cache.reset()
        finally:
            signal.signal = original_signal

def run_raw_camera_app():
    global current_app
    sys.argv = [sys.argv[0], "--input", "rpi"]

    class HeadlessRawApp(GStreamerApp):
        def __init__(self, parser, user_data):
            original = signal.signal
            signal.signal = lambda *args: None
            try:
                super().__init__(parser, user_data)
                self.create_pipeline()
            finally:
                signal.signal = original

        def get_pipeline_string(self):
            source = SOURCE_PIPELINE(self.video_source, self.video_width, self.video_height, self.frame_rate, self.sync)
            user_cb = USER_CALLBACK_PIPELINE()
            # Force RGB
            return (f"{source} ! videoconvert ! video/x-raw,format=RGB ! "
                    f"queue leaky=downstream max-size-buffers=5 ! "
                    f"{user_cb} ! "
                    f"fakesink name=hailo_display sync=false")

    def app_callback(element, buffer, user_data):
        try:
            pad = element.get_static_pad("sink")
            # Uses cached caps
            format, width, height = custom_get_caps_from_pad(pad)
            
            if width and height:
                frame = get_numpy_from_buffer_safe(buffer, format, width, height)
                if frame is not None:
                    # Raw camera has no detection metadata
                    frame_manager.update(frame, {})
        except Exception as e:
            print(f"Frame error: {e}")
        return Gst.PadProbeReturn.OK

    user_data = app_callback_class()
    parser = get_pipeline_parser()
    app = HeadlessRawApp(parser, user_data)
    app.app_callback = app_callback
    current_app = app
    run_app_safely(app)

def run_detection_app():
    global current_app
    sys.argv = [sys.argv[0], "--input", "rpi"]

    class HeadlessDetectionApp(GStreamerDetectionApp):
        def get_pipeline_string(self):
            source = SOURCE_PIPELINE(self.video_source, self.video_width, self.video_height, self.frame_rate, self.sync)
            
            detection = INFERENCE_PIPELINE(
                self.hef_path, 
                self.post_process_so, 
                self.batch_size, 
                self.post_function_name, 
                self.labels_json, 
                self.thresholds_str
            )

            wrapper = INFERENCE_PIPELINE_WRAPPER(detection)
            tracker = TRACKER_PIPELINE(class_id=1)
            user_cb = USER_CALLBACK_PIPELINE()
            
            # --- FIX 1: FORCE RGB HERE ---
            # We inject 'videoconvert ! video/x-raw,format=RGB' before the user callback.
            # This ensures the buffer we get in python is RGB, fixing the blue tint.
            return (f"{source} ! {wrapper} ! {tracker} ! "
                    f"videoconvert ! video/x-raw,format=RGB ! " 
                    f"{user_cb} ! queue ! fakesink name=hailo_display sync=false")

    def app_callback(element, buffer, user_data):
        if buffer is None: return
        try:
            pad = element.get_static_pad("src")
            # Uses cached caps
            format, width, height = custom_get_caps_from_pad(pad)
            
            frame = None
            if width and height:
                frame = get_numpy_from_buffer_safe(buffer, format, width, height)

            roi = hailo.get_roi_from_buffer(buffer)
            detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

            # Prepare metadata list
            meta_list = []

            if frame is not None:
                for detection in detections:
                    bbox = detection.get_bbox()
                    label = detection.get_label()
                    conf = detection.get_confidence()
                    
                    # Store normalized coordinates directly
                    # The Kivy overlay will handle scaling to the display size
                    meta_list.append({
                        "type": "detection",
                        "label": label,
                        "confidence": conf,
                        "bbox": [bbox.xmin(), bbox.ymin(), bbox.xmax(), bbox.ymax()]
                    })
                
                # Update frame manager with clean frame and metadata
                frame_manager.update(frame, {"detections": meta_list})
        except Exception as e:
            pass
        return Gst.PadProbeReturn.OK

    user_data = app_callback_class()
    user_data.use_frame = True 
    original = signal.signal
    signal.signal = lambda *args: None
    try:
        app = HeadlessDetectionApp(app_callback, user_data)
    finally:
        signal.signal = original

    current_app = app
    run_app_safely(app)

def run_pose_app():
    global current_app
    sys.argv = [sys.argv[0], "--input", "rpi"]
    
    # ... (Keep existing Pose implementation, but applying similar fixes recommended)
    # For brevity, I am applying the FIX 1 (Force RGB) to the Pose app below as well.

    KEYPOINTS = {
        "nose": 0, "left_eye": 1, "right_eye": 2, "left_ear": 3, "right_ear": 4,
        "left_shoulder": 5, "right_shoulder": 6, "left_elbow": 7, "right_elbow": 8,
        "left_wrist": 9, "right_wrist": 10, "left_hip": 11, "right_hip": 12,
        "left_knee": 13, "right_knee": 14, "left_ankle": 15, "right_ankle": 16,
    }
    
    SKELETON_PAIRS = [
        ("nose", "left_eye"), ("nose", "right_eye"),
        ("left_eye", "left_ear"), ("right_eye", "right_ear"),
        ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
        ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
        ("left_shoulder", "right_shoulder"),
        ("left_shoulder", "left_hip"), ("right_shoulder", "right_hip"),
        ("left_hip", "right_hip"),
        ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
        ("right_hip", "right_knee"), ("right_knee", "right_ankle")
    ]

    class HeadlessPoseApp(GStreamerPoseEstimationApp):
        def get_pipeline_string(self):
            source = SOURCE_PIPELINE(self.video_source, self.video_width, self.video_height, self.frame_rate, self.sync)
            func_name = getattr(self, "post_process_function", "filter_letterbox")
            inference = INFERENCE_PIPELINE(
                hef_path=self.hef_path,
                post_process_so=self.post_process_so,
                batch_size=self.batch_size,
                post_function_name=func_name
            )
            wrapper = INFERENCE_PIPELINE_WRAPPER(inference)
            tracker = TRACKER_PIPELINE(class_id=1)
            user_cb = USER_CALLBACK_PIPELINE()
            
            # FORCE RGB
            return (f"{source} ! {wrapper} ! {tracker} ! "
                    f"videoconvert ! video/x-raw,format=RGB ! "
                    f"{user_cb} ! queue ! fakesink name=hailo_display sync=false")

    def app_callback(element, buffer, user_data):
        try:
            pad = element.get_static_pad("src")
            # Uses cached caps
            format, width, height = custom_get_caps_from_pad(pad)
            
            frame = None
            if width and height:
                frame = get_numpy_from_buffer_safe(buffer, format, width, height)

            if frame is not None:
                roi = hailo.get_roi_from_buffer(buffer)
                detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
                
                # Prepare pose metadata
                pose_list = []

                if frame is not None:
                    # We pass frame dimensions to helper if needed, but normalization is better.
                    # However, pose points are often easier if we just pass processed points or normalized.
                    # Let's stick to normalized if possible, but the `detection.get_objects_typed` returns relative to bbox?
                    # The original code did: x = (point.x * bbox.w + bbox.x) * width
                    # So point.x is relative to bbox.
                    
                    for detection in detections:
                        bbox = detection.get_bbox()
                        
                        # Store bbox for context (optional)
                        # pose_data = {"bbox": [bbox.xmin(), bbox.ymin(), bbox.xmax(), bbox.ymax()], "keypoints": [], "skeleton": []}
                        
                        landmarks = detection.get_objects_typed(hailo.HAILO_LANDMARKS)
                        if len(landmarks) > 0:
                            points = landmarks[0].get_points()
                            
                            # Convert to global normalized coordinates
                            current_points = {}
                            for name, index in KEYPOINTS.items():
                                point = points[index]
                                # Global normalized X = (local_x * bbox_w) + bbox_x
                                norm_x = (point.x() * bbox.width()) + bbox.xmin()
                                norm_y = (point.y() * bbox.height()) + bbox.ymin()
                                current_points[name] = (norm_x, norm_y)
                            
                            # Add to list
                            pose_list.append({
                                "keypoints": current_points,
                                "pairs": SKELETON_PAIRS # Pass structure so UI knows what to connect
                            })

                    frame_manager.update(frame, {"pose": pose_list})
        except Exception as e:
            pass
        return Gst.PadProbeReturn.OK

    user_data = app_callback_class()
    user_data.use_frame = True
    original = signal.signal
    signal.signal = lambda *args: None
    try:
        app = HeadlessPoseApp(app_callback, user_data)
    finally:
        signal.signal = original

    current_app = app
    run_app_safely(app)