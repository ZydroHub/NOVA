import sys
import time
import hailo
import threading

# -----------------------------------------------------------------------------------------------
# 1. Imports
# -----------------------------------------------------------------------------------------------
try:
    from hailo_apps.python.pipeline_apps.detection.detection_pipeline import GStreamerDetectionApp
    from hailo_apps.python.core.common.hailo_logger import get_logger
    from hailo_apps.python.core.gstreamer.gstreamer_app import app_callback_class
except ImportError:
    print("Error: Could not import hailo_apps. Did you run ./run_app.sh?")
    sys.exit(1)

hailo_logger = get_logger(__name__)

# -----------------------------------------------------------------------------------------------
# 2. Custom Logic with State Control
# -----------------------------------------------------------------------------------------------
class PocketAI_Callback(app_callback_class):
    def __init__(self):
        super().__init__()
        # Ensure detection is strictly OFF at startup
        self.is_detecting = False 
        
        # FPS Calculation Variables
        self.frame_count = 0
        self.start_time = time.time()
        self.fps = 0.0

def app_callback(element, buffer, user_data):
    if buffer is None:
        return

    # --- FPS CALCULATION ---
    # Increment frame counter
    user_data.frame_count += 1
    
    # Check if 1 second has passed
    current_time = time.time()
    elapsed_time = current_time - user_data.start_time
    
    if elapsed_time >= 1.0:
        # Calculate FPS: frames / seconds
        user_data.fps = user_data.frame_count / elapsed_time
        # Reset counter and timer
        user_data.frame_count = 0
        user_data.start_time = current_time

    # Get the Region of Interest (ROI) containing metadata
    roi = hailo.get_roi_from_buffer(buffer)

    # --- IF DETECTION IS OFF ---
    if not user_data.is_detecting:
        # We must manually REMOVE existing detections from the buffer
        # so that the video overlay element doesn't draw them.
        detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
        for detection in detections:
            roi.remove_object(detection)
        return

    # --- IF DETECTION IS ON ---
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    found_objects = []
    for detection in detections:
        # Only show high-confidence detections
        if detection.get_confidence() > 0.50:
            found_objects.append(detection.get_label())

    # Format the FPS string
    fps_text = f"FPS: {user_data.fps:.1f}"

    # Print objects found along with FPS
    if found_objects:
        objects_str = ", ".join(found_objects)
        print(f"\r[{fps_text}] Detected: {objects_str} " + " "*20, end="", flush=True)
    else:
        print(f"\r[{fps_text}] Scanning... " + " "*20, end="", flush=True)

# -----------------------------------------------------------------------------------------------
# 3. Input Listener
# -----------------------------------------------------------------------------------------------
def input_listener(user_data):
    while True:
        try:
            # Use a slightly more robust input method for threads
            cmd = input().strip().lower()
            if cmd == "detect":
                user_data.is_detecting = True
                # Reset timer on start to avoid weird initial calculation
                user_data.start_time = time.time()
                user_data.frame_count = 0
                print("\n>>> Object Detection: STARTED")
            elif cmd == "stop":
                user_data.is_detecting = False
                print("\n>>> Object Detection: STOPPED. (Type 'detect' to resume)")
            elif cmd == "exit":
                print("\nExiting...")
                # We need to force kill because GStreamer threads can hang
                import os
                os._exit(0)
        except EOFError:
            break

# -----------------------------------------------------------------------------------------------
# 4. Main
# -----------------------------------------------------------------------------------------------
def main():
    user_data = PocketAI_Callback()
    app = GStreamerDetectionApp(app_callback, user_data)

    print("------------------------------------------")
    print("Camera Started. Detection is currently OFF.")
    print("Commands: 'detect' to start, 'stop' to pause, 'exit' to quit.")
    print("------------------------------------------")

    # Start the input thread
    listener_thread = threading.Thread(target=input_listener, args=(user_data,), daemon=True)
    listener_thread.start()
    
    try:
        app.run()
    except KeyboardInterrupt:
        print("\nStopping...")

if __name__ == "__main__":
    main()