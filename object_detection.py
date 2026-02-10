import sys
import time
import multiprocessing
import os

# -----------------------------------------------------------------------------------------------
# 1. Worker Functions (Run in separate processes)
# -----------------------------------------------------------------------------------------------

def run_raw_camera_app():
    """
    Runs a simple GStreamer pipeline: Source -> Display (No AI).
    """
    try:
        import setproctitle
        from hailo_apps.python.core.gstreamer.gstreamer_app import GStreamerApp, dummy_callback, app_callback_class
        from hailo_apps.python.core.gstreamer.gstreamer_helper_pipelines import SOURCE_PIPELINE, DISPLAY_PIPELINE
        from hailo_apps.python.core.common.core import get_pipeline_parser
        from hailo_apps.python.core.common.hailo_logger import get_logger
    except ImportError:
        print("Error importing Hailo apps.")
        return

    # Define a simple App class that just connects Source to Sink
    class GStreamerRawApp(GStreamerApp):
        def __init__(self, app_callback, user_data):
            parser = get_pipeline_parser()
            super().__init__(parser, user_data)
            setproctitle.setproctitle("Hailo Raw Stream")
            self.create_pipeline()

        def get_pipeline_string(self):
            # Just connect the camera source directly to the display
            source = SOURCE_PIPELINE(
                video_source=self.video_source,
                video_width=self.video_width,
                video_height=self.video_height,
                frame_rate=self.frame_rate,
                sync=self.sync
            )
            display = DISPLAY_PIPELINE(
                video_sink=self.video_sink, 
                sync=self.sync, 
                show_fps=self.show_fps
            )
            # Simple pass-through pipeline
            return f"{source} ! {display}"

    user_data = app_callback_class()
    app = GStreamerRawApp(dummy_callback, user_data)
    print("\n>>> Starting Raw Camera Feed...")
    app.run()


def run_detection_app():
    """
    Runs the Object Detection pipeline.
    """
    try:
        import hailo
        from hailo_apps.python.pipeline_apps.detection.detection_pipeline import GStreamerDetectionApp
        from hailo_apps.python.core.gstreamer.gstreamer_app import app_callback_class
    except ImportError:
        return

    class DetectionCallback(app_callback_class):
        def __init__(self):
            super().__init__()
            self.frame_count = 0
            self.start_time = time.time()
            self.fps = 0.0

    def app_callback(element, buffer, user_data):
        if buffer is None: return
        
        user_data.frame_count += 1
        elapsed = time.time() - user_data.start_time
        if elapsed > 1.0:
            user_data.fps = user_data.frame_count / elapsed
            user_data.frame_count = 0
            user_data.start_time = time.time()

        roi = hailo.get_roi_from_buffer(buffer)
        detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
        
        found_objects = []
        for detection in detections:
            if detection.get_confidence() > 0.50:
                found_objects.append(detection.get_label())
        
        fps_text = f"FPS: {user_data.fps:.1f}"
        if found_objects:
            print(f"\r[{fps_text}] [DETECT] Found: {', '.join(found_objects)}" + " "*20, end="", flush=True)
        else:
            print(f"\r[{fps_text}] [DETECT] Scanning..." + " "*20, end="", flush=True)

    user_data = DetectionCallback()
    app = GStreamerDetectionApp(app_callback, user_data)
    app.run()


def run_pose_app():
    """
    Runs the Pose Estimation pipeline.
    """
    try:
        import hailo
        from hailo_apps.python.pipeline_apps.pose_estimation.pose_estimation_pipeline import GStreamerPoseEstimationApp
        from hailo_apps.python.core.gstreamer.gstreamer_app import app_callback_class
    except ImportError:
        return

    class PoseCallback(app_callback_class):
        def __init__(self):
            super().__init__()
            self.frame_count = 0
            self.start_time = time.time()
            self.fps = 0.0

    def app_callback(element, buffer, user_data):
        if buffer is None: return

        user_data.frame_count += 1
        elapsed = time.time() - user_data.start_time
        if elapsed > 1.0:
            user_data.fps = user_data.frame_count / elapsed
            user_data.frame_count = 0
            user_data.start_time = time.time()

        roi = hailo.get_roi_from_buffer(buffer)
        detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
        
        fps_text = f"FPS: {user_data.fps:.1f}"
        if len(detections) > 0:
            print(f"\r[{fps_text}] [POSE] Person Tracked" + " "*20, end="", flush=True)
        else:
            print(f"\r[{fps_text}] [POSE] Searching..." + " "*20, end="", flush=True)

    user_data = PoseCallback()
    app = GStreamerPoseEstimationApp(app_callback, user_data)
    app.run()

# -----------------------------------------------------------------------------------------------
# 2. Main Controller
# -----------------------------------------------------------------------------------------------
if __name__ == "__main__":
    current_process = None
    
    print("------------------------------------------")
    print("AI Camera Controller")
    print("Commands: 'detect', 'pose', 'stream' (reset), 'stop', 'exit'")
    print("------------------------------------------")

    # --- STARTUP: Automatically launch Raw Camera ---
    print("Initializing Camera...")
    current_process = multiprocessing.Process(target=run_raw_camera_app)
    current_process.start()

    while True:
        try:
            cmd = input().strip().lower()

            # Helper to kill current process safely
            def kill_active_process():
                if current_process and current_process.is_alive():
                    # print("\n...Switching...") 
                    current_process.terminate()
                    current_process.join()

            # --- COMMANDS ---
            if cmd == "exit":
                print("Exiting...")
                kill_active_process()
                sys.exit(0)

            elif cmd == "stop":
                print("\n>>> Stopping video feed.")
                kill_active_process()

            elif cmd == "stream" or cmd == "reset":
                kill_active_process()
                print("\n>>> Switching to Raw Stream...")
                current_process = multiprocessing.Process(target=run_raw_camera_app)
                current_process.start()

            elif cmd == "detect":
                kill_active_process()
                print("\n>>> Switching to DETECTION...")
                current_process = multiprocessing.Process(target=run_detection_app)
                current_process.start()

            elif cmd == "pose":
                kill_active_process()
                print("\n>>> Switching to POSE ESTIMATION...")
                current_process = multiprocessing.Process(target=run_pose_app)
                current_process.start()
            
            else:
                print(f"Unknown command: '{cmd}'")

        except KeyboardInterrupt:
            print("\nForce stopping...")
            if current_process:
                current_process.terminate()
            break