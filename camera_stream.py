"""
Lightweight 30 fps camera stream process. No GStreamer, no Hailo.
Used for live view when camera screen is open. When detection is enabled,
every 3rd frame is also pushed to detection_queue for 10 fps inference.
"""
import time
import multiprocessing


# Default lores size; match common Hailo input for detection
STREAM_WIDTH = 640
STREAM_HEIGHT = 384
STREAM_FPS = 30
# Every Nth frame goes to detection (~10 fps when capture is 30 fps)
DETECTION_FRAME_INTERVAL = 3


def run_stream_process(
    stream_queue: multiprocessing.Queue,
    stop_event: multiprocessing.Event,
    detection_enabled: multiprocessing.Value = None,
    detection_queue: multiprocessing.Queue = None,
    width: int = STREAM_WIDTH,
    height: int = STREAM_HEIGHT,
):
    """
    Captures from Picamera2 at 30 fps. Puts every frame in stream_queue.
    When detection_enabled is true, puts every 3rd frame in detection_queue (non-blocking).
    """
    try:
        import setproctitle
        setproctitle.setproctitle("pocket-ai-stream")
    except ImportError:
        pass

    picam2 = None
    max_retries = 3
    for attempt in range(max_retries):
        try:
            from picamera2 import Picamera2
            picam2 = Picamera2()
            main = {"size": (1280, 720), "format": "RGB888"}
            lores = {"size": (width, height), "format": "RGB888"}
            controls = {"FrameRate": STREAM_FPS, "AfMode": 2, "AfRange": 2}
            config = picam2.create_preview_configuration(main=main, lores=lores, controls=controls)
            picam2.configure(config)
            picam2.start()
            break
        except Exception as e:
            if picam2:
                try:
                    picam2.stop()
                    picam2.close()
                except Exception:
                    pass
                picam2 = None
            time.sleep(1.0)

    if picam2 is None:
        return

    frame_count = 0
    try:
        while not stop_event.is_set():
            try:
                frame_data = picam2.capture_array("lores")
            except Exception:
                break
            if frame_data is None:
                break

            # libcamera/Pi often gives BGR; convert to RGB for pipeline (app.py expects RGB)
            import cv2
            if len(frame_data.shape) == 2:
                frame = cv2.cvtColor(frame_data, cv2.COLOR_GRAY2RGB)
            elif frame_data.shape[2] == 3:
                frame = cv2.cvtColor(frame_data, cv2.COLOR_BGR2RGB)
            else:
                frame = cv2.cvtColor(frame_data, cv2.COLOR_BGR2RGB)

            # Always push to stream queue for 30 fps view (non-blocking, drop if full)
            try:
                stream_queue.put_nowait(frame)
            except Exception:
                pass

            # When detection is on, push every Nth frame to detection queue
            if detection_enabled is not None and detection_queue is not None:
                if detection_enabled.value and frame_count % DETECTION_FRAME_INTERVAL == 0:
                    try:
                        detection_queue.put_nowait(frame)
                    except Exception:
                        pass

            frame_count += 1
    finally:
        try:
            picam2.stop()
            picam2.close()
        except Exception:
            pass
