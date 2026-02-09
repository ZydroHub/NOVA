import cv2
import numpy as np
from picamera2 import Picamera2
from picamera2.devices import Hailo

# --- CONFIGURATION ---
MODEL_FILE = "/usr/share/hailo-models/yolov8s_h8.hef"
# Lowering this to match rpicam-still defaults
CONFIDENCE_THRESHOLD = 0.45 

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

def draw_detections(frame, results):
    """
    Draws boxes using the 'Squish' logic.
    Since the whole image was squished to 640x640, xmin=0 is left, xmax=1 is right.
    We just map 0-1 back to the screen width/height.
    """
    if not results: 
        return

    detections = results[0]
    if len(detections.shape) == 3: 
        detections = detections[0]

    # Get dimensions of the SCREEN
    height, width, _ = frame.shape

    for det in detections:
        # Parse Row
        if len(det) == 6:
            ymin, xmin, ymax, xmax, score, class_id = det
        elif len(det) == 5:
            ymin, xmin, ymax, xmax, score = det
            class_id = 0
        else:
            continue

        if score < CONFIDENCE_THRESHOLD:
            continue

        # SIMPLE MAPPING (No padding math needed)
        x0 = int(xmin * width)
        y0 = int(ymin * height)
        x1 = int(xmax * width)
        y1 = int(ymax * height)

        # Draw
        label = COCO_LABELS.get(int(class_id), "Object")
        cv2.rectangle(frame, (x0, y0), (x1, y1), (0, 255, 0), 2)
        cv2.putText(frame, f"{label} {int(score*100)}%", (x0, y0-10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

def main():
    try:
        print(f"Loading Model: {MODEL_FILE}")
        with Hailo(MODEL_FILE) as hailo:
            picam2 = Picamera2()
            
            config = picam2.create_preview_configuration(
                main={"size": (2304, 1296), "format": "XRGB8888"}
            )
            picam2.configure(config)
            picam2.start()
            picam2.set_controls({"AfMode": 2, "AfRange": 0}) 

            print("Running... Press 'q' to quit.")

            while True:
                # 1. Capture Wide Image
                frame_wide = picam2.capture_array('main')
                frame_bgr = cv2.cvtColor(frame_wide, cv2.COLOR_BGRA2BGR)

                # 2. THE SQUISH (Replaces Letterbox)
                # Force the wide image into the square 640x640
                frame_ai = cv2.resize(frame_bgr, (640, 640))

                # 3. Run AI
                results = hailo.run(frame_ai)

                # 4. Draw
                draw_detections(frame_bgr, results)
                
                cv2.imshow("Hailo Object Detection", frame_bgr)

                if cv2.waitKey(1) == ord('q'):
                    break

    except Exception as e:
        print(f"Error: {e}")
    finally:
        picam2.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()