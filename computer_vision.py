import sys
import time
import threading
import signal
import gi
import cv2
import numpy as np

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

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
        self._read_frame = None

    def update(self, frame):
        with self._lock:
            self._current_frame = frame

    def get_latest(self):
        with self._lock:
            if self._current_frame is None:
                return None
            # Return a copy to ensure thread safety for the consumer (GUI)
            # Optimization: In some cases, we might swap buffers, but copy is safest for now.
            return self._current_frame.copy()

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
    Now uses a global cache to avoid repetitive parsing.
    """
    if global_caps_cache.valid:
        return global_caps_cache.fmt, global_caps_cache.width, global_caps_cache.height
    
    global_caps_cache.update(pad)
    return global_caps_cache.fmt, global_caps_cache.width, global_caps_cache.height

    try:
        caps = pad.get_current_caps()
        if not caps:
            return None, None, None

        structure = caps.get_structure(0)
        width, height, fmt = 0, 0, None

        if hasattr(structure, 'get_int'):
            success_w, width = structure.get_int("width")
            success_h, height = structure.get_int("height")
            fmt = structure.get_value("format") if hasattr(structure, "get_value") else structure.get_string("format")
            
        elif hasattr(structure, 'width') and hasattr(structure, 'height'):
            width = structure.width
            height = structure.height
            fmt = structure.format
        
        else:
            caps_str = caps.to_string()
            import re
            w_match = re.search(r'width=\(int\)(\d+)', caps_str)
            h_match = re.search(r'height=\(int\)(\d+)', caps_str)
            f_match = re.search(r'format=\(string\)([A-Z0-9]+)', caps_str)
            
            if w_match: width = int(w_match.group(1))
            if h_match: height = int(h_match.group(1))
            if f_match: fmt = f_match.group(1)

        return fmt, width, height

    except Exception as e:
        print(f"[DEBUG] Error in custom_get_caps: {e}")
        # Invalidate cache on error so we try again next time
        global_caps_cache.valid = False
        return None, None, None

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
    if current_app:
        try:
            if hasattr(current_app, 'loop') and current_app.loop is not None:
                if current_app.loop.is_running(): current_app.loop.quit()
            elif hasattr(current_app, 'pipeline') and current_app.pipeline is not None:
                current_app.pipeline.set_state(Gst.State.NULL)
        except Exception as e:
            print(f"Error stopping app: {e}")
        current_app = None

    if current_thread and current_thread.is_alive():
        current_thread.join(timeout=2.0)
        current_thread = None

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
    try:
        app.run()
    except Exception as e:
        print(f"App run error: {e}")
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
                    frame_manager.update(frame)
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

            if frame is not None:
                for detection in detections:
                    bbox = detection.get_bbox()
                    label = detection.get_label()
                    conf = detection.get_confidence()
                    
                    # --- FIX 2: UN-LETTERBOXING COORDINATES ---
                    # Hailo models (like YOLO) work on square images (e.g. 640x640).
                    # Your camera is 4:3 (e.g. 640x480).
                    # The pipeline adds black bars (padding) to make it square.
                    # We must undo this padding to draw boxes correctly on the original frame.
                    
                    # 1. Get raw normalized coordinates (0.0 to 1.0 relative to 640x640)
                    xmin_norm = bbox.xmin()
                    ymin_norm = bbox.ymin()
                    xmax_norm = bbox.xmax()
                    ymax_norm = bbox.ymax()
                    
                    # 2. Define Network Dimension (Assuming 640x640 for standard Hailo models)
                    # If using a different model resolution, change this (e.g. 300, 512)
                    NETWORK_DIM = 640 
                    
                    # 3. Calculate Scale and Padding
                    img_w, img_h = width, height
                    scale = min(NETWORK_DIM / img_w, NETWORK_DIM / img_h)
                    
                    pad_w = (NETWORK_DIM - img_w * scale) / 2
                    pad_h = (NETWORK_DIM - img_h * scale) / 2
                    
                    # 4. Map back to original image pixels
                    x1 = int((xmin_norm * NETWORK_DIM - pad_w) / scale)
                    y1 = int((ymin_norm * NETWORK_DIM - pad_h) / scale)
                    x2 = int((xmax_norm * NETWORK_DIM - pad_w) / scale)
                    y2 = int((ymax_norm * NETWORK_DIM - pad_h) / scale)

                    # Clamp to frame boundaries
                    x1 = max(0, min(x1, width))
                    y1 = max(0, min(y1, height))
                    x2 = max(0, min(x2, width))
                    y2 = max(0, min(y2, height))

                    # Draw
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, f"{label} {conf:.2f}", (x1, y1-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                frame_manager.update(frame)
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
                
                for detection in detections:
                    bbox = detection.get_bbox()
                    
                    # NOTE: Pose models usually handle letterboxing differently or output relative to bbox
                    # But if you see offsets, apply the same "Fix 2" logic here.
                    # For now, we use standard scaling.
                    xmin = int(bbox.xmin() * width)
                    ymin = int(bbox.ymin() * height)
                    xmax = int(bbox.xmax() * width)
                    ymax = int(bbox.ymax() * height)
                    
                    cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
                    
                    landmarks = detection.get_objects_typed(hailo.HAILO_LANDMARKS)
                    if len(landmarks) > 0:
                        points = landmarks[0].get_points()
                        coords = {}
                        for name, index in KEYPOINTS.items():
                            point = points[index]
                            x = int((point.x() * bbox.width() + bbox.xmin()) * width)
                            y = int((point.y() * bbox.height() + bbox.ymin()) * height)
                            coords[name] = (x, y)
                            cv2.circle(frame, (x, y), 4, (0, 255, 255), -1)

                        for start_part, end_part in SKELETON_PAIRS:
                            if start_part in coords and end_part in coords:
                                cv2.line(frame, coords[start_part], coords[end_part], (255, 0, 0), 2)

                frame_manager.update(frame)
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