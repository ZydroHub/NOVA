import sys
import cv2
import numpy as np
from picamera2 import Picamera2
from picamera2.devices import Hailo

# --- 1. CONFIGURATION ---
# UPDATED PATH based on your grep result
MODEL_FILE = "/usr/share/hailo-models/yolov8s_h8l.hef"

# Simple COCO Label Map (Top 80 object classes)
# This maps the Class ID (0, 1, 2...) to the Name ("Person", "Car"...)
COCO_LABELS = {
    0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 4: 'airplane',
    5: 'bus', 6: 'train', 7: 'truck', 8: 'boat', 9: 'traffic light',
    10: 'fire hydrant', 11: 'stop sign', 12: 'parking meter', 13: 'bench',
    14: 'bird', 15: 'cat', 16: 'dog', 17: 'horse', 18: 'sheep', 19: 'cow',
    20: 'elephant', 21: 'bear', 22: 'zebra', 23: 'giraffe', 24: 'backpack',
    25: 'umbrella', 26: 'handbag', 27: 'tie', 28: 'suitcase', 29: 'frisbee',
    30: 'skis', 31: 'snowboard', 32: 'sports ball', 33: 'kite', 34: 'baseball bat',
    35: 'baseball glove', 36: 'skateboard', 37: 'surfboard', 38: 'tennis racket',
    39: 'bottle', 40: 'wine glass', 41: 'cup', 42: 'fork', 43: 'knife',
    44: 'spoon', 45: 'bowl', 46: 'banana', 47: 'apple', 48: 'sandwich',
    49: 'orange', 50: 'broccoli', 51: 'carrot', 52: 'hot dog', 53: 'pizza',
    54: 'donut', 55: 'cake', 56: 'chair', 57: 'couch', 58: 'potted plant',
    59: 'bed', 60: 'dining table', 61: 'toilet', 62: 'tv', 63: 'laptop',
    64: 'mouse', 65: 'remote', 66: 'keyboard', 67: 'cell phone', 68: 'microwave',
    69: 'oven', 70: 'toaster', 71: 'sink', 72: 'refrigerator', 73: 'book',
    74: 'clock', 75: 'vase', 76: 'scissors', 77: 'teddy bear', 78: 'hair drier',
    79: 'toothbrush'
}

# --- 2. HELPER FUNCTIONS ---
def draw_detections(frame, results, width, height, threshold=0.5):
    """
    Parses results and draws boxes on the frame.
    """
    for detection in results:
        # Get the score
        score = detection['score']
        if score < threshold:
            continue

        # Get the class ID and Name
        class_id = detection['class_id']
        label_name = COCO_LABELS.get(class_id, f"ID: {class_id}")

        # Get coordinates (Normalized 0.0 - 1.0)
        ymin, xmin, ymax, xmax = detection['ymin'], detection['xmin'], detection['ymax'], detection['xmax']

        # Convert to Pixels
        x0 = int(xmin * width)
        y0 = int(ymin * height)
        x1 = int(xmax * width)
        y1 = int(ymax * height)

        # Draw the Box (Green)
        cv2.rectangle(frame, (x0, y0), (x1, y1), (0, 255, 0), 2)

        # Draw the Label (Black text on Green background)
        text = f"{label_name}: {int(score * 100)}%"
        (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(frame, (x0, y0 - 20), (x0 + text_w, y0), (0, 255, 0), -1)
        cv2.putText(frame, text, (x0, y0 - 5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

# --- 3. MAIN SCRIPT ---
def main():
    try:
        # Load the Hailo Chip
        print(f"Loading Hailo Model: {MODEL_FILE}")
        with Hailo(MODEL_FILE) as hailo:
            
            # Initialize Camera
            picam2 = Picamera2()
            
            # Configure Streams:
            # 'main': 1280x720 (What you see)
            # 'lores': 640x640 (What the AI sees - standard for YOLOv8)
            config = picam2.create_preview_configuration(
                main={"size": (1280, 720), "format": "XRGB8888"},
                lores={"size": (640, 640), "format": "RGB888"}
            )
            picam2.configure(config)
            picam2.start()

            # Enable Auto-Focus
            picam2.set_controls({"AfMode": 2, "AfRange": 0})
            
            print("Camera Running. Press 'q' to quit.")

            while True:
                # 1. Capture the AI frame (Blocking)
                frame_ai = picam2.capture_array('lores')
                
                # 2. Run Inference (Async-like speed)
                # The Hailo chip does this part
                results = hailo.run(frame_ai)

                # 3. Capture the Display frame
                frame_display = picam2.capture_array('main')
                
                # 4. Prepare for OpenCV (XRGB -> BGR)
                frame_display = cv2.cvtColor(frame_display, cv2.COLOR_RGB2BGR)
                h, w, _ = frame_display.shape

                # 5. Draw!
                draw_detections(frame_display, results, w, h)

                # 6. Show
                cv2.imshow("Hailo-8L Detection", frame_display)
                
                if cv2.waitKey(1) == ord('q'):
                    break

    except Exception as e:
        print(f"\nError: {e}")
        # Check specifically for the file error again
        if "No such file" in str(e) or "HAILO_OPEN_FILE_FAILURE" in str(e):
             print(f"\nCRITICAL: The file {MODEL_FILE} was not found.")
             print("Please double check the path in the script.")
    
    finally:
        try:
            picam2.stop()
        except:
            pass
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()