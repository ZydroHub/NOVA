import os
import time
import psutil
import multiprocessing
import cv2
import numpy as np
import asyncio
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from camera_stream import run_stream_process

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global camera state
camera_process = None
stop_event = multiprocessing.Event()
stream_queue = multiprocessing.Queue(maxsize=1) # Reduced maxsize to ensure fresh frames
detection_enabled = multiprocessing.Value('b', False)
detection_queue = multiprocessing.Queue(maxsize=1)

@app.get("/system/stats")
async def get_stats():
    return {
        "time": time.strftime("%H:%M:%S"),
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "temperature": 0 # Placeholder if no sensor access
    }

@app.post("/camera/start")
async def start_camera():
    global camera_process, stop_event
    if camera_process and camera_process.is_alive():
        return {"status": "already_running"}
    
    stop_event.clear()
    camera_process = multiprocessing.Process(
        target=run_stream_process,
        args=(stream_queue, stop_event, detection_enabled, detection_queue)
    )
    camera_process.start()
    return {"status": "started"}

@app.post("/camera/stop")
async def stop_camera():
    global camera_process, stop_event
    if camera_process:
        stop_event.set()
        camera_process.join(timeout=2)
        if camera_process.is_alive():
            camera_process.terminate()
        camera_process = None
    return {"status": "stopped"}

def generate_frames():
    while True:
        try:
            # We need to use timeout or check if process is alive to avoid hanging
            frame = stream_queue.get(timeout=1.0)
        except Exception:
            if camera_process and not camera_process.is_alive():
                break
            continue
            
        if frame is None:
            break
        
        # Rotate 90 degrees clockwise for portrait mode
        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        # Resize to fit window (Portrait aspect)
        frame = cv2.resize(frame, (480, 800), interpolation=cv2.INTER_LINEAR)
        
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        ret, buffer = cv2.imencode('.jpg', frame_bgr)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.post("/camera/capture")
async def capture_image():
    # Get the latest frame from the queue
    try:
        # Try to get a frame, non-blocking if possible or with small timeout
        frame = stream_queue.get(timeout=2.0)
        
        # Rotate 90 degrees clockwise for portrait mode
        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        # Resize to fit window (Portrait aspect)
        frame = cv2.resize(frame, (480, 800), interpolation=cv2.INTER_LINEAR)
        
        timestamp = int(time.time())
        filename = f"capture_{timestamp}.jpg"
        save_path = os.path.join("captures", filename)
        os.makedirs("captures", exist_ok=True)
        
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imwrite(save_path, frame_bgr)
        print(f"Captured: {save_path}")
        return {"status": "success", "filename": filename}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"Capture failed: {str(e)}"}

@app.post("/camera/detection/start")
async def start_detection():
    detection_enabled.value = True
    return {"status": "started"}

@app.post("/camera/detection/stop")
async def stop_detection():
    detection_enabled.value = False
    return {"status": "stopped"}

@app.websocket("/ws")
async def detection_websocket(websocket: WebSocket):
    await websocket.accept()
    print("Detection WebSocket connected")
    try:
        while True:
            # For now, just a keep-alive or empty detection feed
            # In the future, this would yield from detection_queue
            await asyncio.sleep(1)
            # await websocket.send_json({"type": "detections", "data": []})
    except WebSocketDisconnect:
        print("Detection WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
