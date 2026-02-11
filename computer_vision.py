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
frame_lock = threading.Lock()
current_frame = None

def get_latest_frame():
    global current_frame
    with frame_lock:
        if current_frame is None:
            return None
        return current_frame.copy()

# -----------------------------------------------------------------------------------------------
# 2. DEBUGGING UTILITIES (The Fix)
# -----------------------------------------------------------------------------------------------
def custom_get_caps_from_pad(pad):
    """
    A replacement for Hailo's get_caps_from_pad that includes deep debugging
    and robust error handling for StructureWrapper objects.
    """
    try:
        caps = pad.get_current_caps()
        if not caps:
            print("[DEBUG] No caps found on pad.")
            return None, None, None

        # 1. Inspect the Caps object
        structure = caps.get_structure(0)
        
        # DEBUGGING: Uncomment these lines if you need to see the raw structure schema in logs
        # print(f"[DEBUG] Caps String: {caps.to_string()}") 
        # print(f"[DEBUG] Structure Type: {type(structure)}")
        
        # 2. Robust Extraction (Standard GStreamer vs Wrapper)
        width, height, fmt = 0, 0, None

        # Try dictionary-style access (Standard Python GStreamer)
        if hasattr(structure, 'get_int'):
            success_w, width = structure.get_int("width")
            success_h, height = structure.get_int("height")
            success_f, fmt = structure.get_string("format"), None
            # Gst 1.20+ get_string returns just the string, older might be different. 
            # We assume 'format' is returned directly if valid.
            fmt = structure.get_value("format") if hasattr(structure, "get_value") else structure.get_string("format")
            
        # Try direct attribute access (Some Wrappers)
        elif hasattr(structure, 'width') and hasattr(structure, 'height'):
            width = structure.width
            height = structure.height
            fmt = structure.format
        
        # Fallback: Parse the string representation (Ultimate failsafe)
        else:
            # e.g., video/x-raw, format=(string)RGB, width=(int)1280, height=(int)720
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
        print(f"[DEBUG] CRITICAL ERROR in custom_get_caps: {e}")
        # Print directory to see what attributes actually exist
        if 'structure' in locals():
            print(f"[DEBUG] Structure Dir: {dir(structure)}")
        return None, None, None

def get_numpy_from_buffer_safe(buffer, format, width, height):
    """Safe wrapper for buffer conversion."""
    try:
        # Standard GStreamer Buffer to Numpy
        success, map_info = buffer.map(Gst.MapFlags.READ)
        if not success:
            raise RuntimeError("Could not map buffer data")
        
        try:
            # Assume RGB/BGR for simplicity in this raw app context
            # Calculate expected size
            expected_size = width * height * 3 # for RGB/BGR
            
            if map_info.size != expected_size:
                # Fallback for other formats or padding issues
                # print(f"[DEBUG] Size mismatch: Buffer {map_info.size} vs Expected {expected_size}")
                pass

            # Create the array
            frame = np.ndarray(
                shape=(height, width, 3),
                dtype=np.uint8,
                buffer=map_info.data
            )
            return frame.copy() # Copy so we can unmap safely
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
    from hailo_apps.python.core.gstreamer.gstreamer_app import GStreamerApp, dummy_callback, app_callback_class
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
            # Explicitly force RGB to make numpy conversion predictable
            return (f"{source} ! videoconvert ! video/x-raw,format=RGB ! "
                    f"queue leaky=downstream max-size-buffers=5 ! "
                    f"{user_cb} ! "
                    f"fakesink name=hailo_display sync=false")

    def app_callback(element, buffer, user_data):
        try:
            pad = element.get_static_pad("sink")
            # USE CUSTOM DEBUG FUNCTION HERE
            format, width, height = custom_get_caps_from_pad(pad)
            
            if width and height:
                frame = get_numpy_from_buffer_safe(buffer, format, width, height)
                if frame is not None:
                    with frame_lock:
                        global current_frame
                        current_frame = frame
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
            
            # --- CHANGED: Swapped post_function_name and batch_size ---
            detection = INFERENCE_PIPELINE(
                self.hef_path, 
                self.post_process_so, 
                self.batch_size,          # <--- batch_size comes 3rd
                self.post_function_name,  # <--- function_name comes 4th
                self.labels_json, 
                self.thresholds_str
            )
            # ----------------------------------------------------------

            wrapper = INFERENCE_PIPELINE_WRAPPER(detection)
            tracker = TRACKER_PIPELINE(class_id=1)
            user_cb = USER_CALLBACK_PIPELINE()
            return f"{source} ! {wrapper} ! {tracker} ! {user_cb} ! queue ! fakesink name=hailo_display sync=false"

    def app_callback(element, buffer, user_data):
        if buffer is None: return
        try:
            pad = element.get_static_pad("src")
            # USE CUSTOM DEBUG FUNCTION
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
                    x1 = int(bbox.xmin() * width)
                    y1 = int(bbox.ymin() * height)
                    x2 = int(bbox.xmax() * width)
                    y2 = int(bbox.ymax() * height)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, f"{label} {conf:.2f}", (x1, y1-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                with frame_lock:
                    global current_frame
                    current_frame = frame
        except Exception as e:
            # print(f"Detection error: {e}")
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

    # 1. Define Keypoints and Skeleton connections for visualization
    KEYPOINTS = {
        "nose": 0, "left_eye": 1, "right_eye": 2, "left_ear": 3, "right_ear": 4,
        "left_shoulder": 5, "right_shoulder": 6, "left_elbow": 7, "right_elbow": 8,
        "left_wrist": 9, "right_wrist": 10, "left_hip": 11, "right_hip": 12,
        "left_knee": 13, "right_knee": 14, "left_ankle": 15, "right_ankle": 16,
    }
    
    # Pairs of keypoints to connect with lines
    SKELETON_PAIRS = [
        # Face
        ("nose", "left_eye"), ("nose", "right_eye"),
        ("left_eye", "left_ear"), ("right_eye", "right_ear"),
        # Arms
        ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
        ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
        ("left_shoulder", "right_shoulder"),
        # Torso
        ("left_shoulder", "left_hip"), ("right_shoulder", "right_hip"),
        ("left_hip", "right_hip"),
        # Legs
        ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
        ("right_hip", "right_knee"), ("right_knee", "right_ankle")
    ]

    class HeadlessPoseApp(GStreamerPoseEstimationApp):
        def get_pipeline_string(self):
            source = SOURCE_PIPELINE(self.video_source, self.video_width, self.video_height, self.frame_rate, self.sync)
            
            # Use the attribute name found in your uploaded pose_estimation_pipeline.py
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
            return f"{source} ! {wrapper} ! {tracker} ! {user_cb} ! queue ! fakesink name=hailo_display sync=false"

    def app_callback(element, buffer, user_data):
        try:
            pad = element.get_static_pad("src")
            format, width, height = custom_get_caps_from_pad(pad)
            
            frame = None
            if width and height:
                frame = get_numpy_from_buffer_safe(buffer, format, width, height)

            if frame is not None:
                roi = hailo.get_roi_from_buffer(buffer)
                detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
                
                for detection in detections:
                    # 1. Draw Bounding Box
                    bbox = detection.get_bbox()
                    confidence = detection.get_confidence()
                    
                    # Bbox coordinates
                    xmin = bbox.xmin() * width
                    ymin = bbox.ymin() * height
                    xmax = bbox.xmax() * width
                    ymax = bbox.ymax() * height
                    w_box = bbox.width() * width
                    h_box = bbox.height() * height
                    
                    cv2.rectangle(frame, (int(xmin), int(ymin)), (int(xmax), int(ymax)), (0, 255, 0), 2)
                    
                    # 2. Get Landmarks (The Stick Figure)
                    landmarks = detection.get_objects_typed(hailo.HAILO_LANDMARKS)
                    if len(landmarks) > 0:
                        points = landmarks[0].get_points()
                        
                        # Dictionary to store calculated coordinates for skeleton drawing
                        coords = {}
                        
                        # Loop through all keypoints
                        for name, index in KEYPOINTS.items():
                            point = points[index]
                            # IMPORTANT: Points are relative to the Bounding Box, not the Frame!
                            # Formula: (point_rel * box_dim) + box_min
                            x = int((point.x() * bbox.width() + bbox.xmin()) * width)
                            y = int((point.y() * bbox.height() + bbox.ymin()) * height)
                            
                            coords[name] = (x, y)
                            
                            # Draw the joint (circle)
                            cv2.circle(frame, (x, y), 4, (0, 255, 255), -1) # Yellow joints

                        # Draw the bones (lines)
                        for start_part, end_part in SKELETON_PAIRS:
                            if start_part in coords and end_part in coords:
                                cv2.line(frame, coords[start_part], coords[end_part], (255, 0, 0), 2) # Blue bones

                with frame_lock:
                    global current_frame
                    current_frame = frame
        except Exception as e:
            # print(f"Pose callback error: {e}")
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