from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import logging
import sys
import uuid
import pydantic
from typing import Dict, List, Optional

# Import OpenClawClient from the existing file
try:
    from openclaw_client import OpenClawClient, load_openclaw_config, DEFAULT_SESSION_KEY
except ImportError as e:
    print(f"Error: Could not import openclaw_client. Details: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastapi_bridge")

# ─── Load Global Configuration ───────────────────────────────────────────────

OC_CONFIG, OC_URL, OC_TOKEN = load_openclaw_config()
OC_URL = OC_URL or "ws://127.0.0.1:18789"

import cv2
from starlette.background import BackgroundTask
from fastapi.responses import StreamingResponse

# Import detection module
# Ensure sys.path includes hailo-apps logic if needed, but detection.py handles it internally?
# Actually detection.py modifies sys.path if run as main, but as module it might not?
# Let's add the sys.path modification here regarding hailo-apps just in case,
# or rely on the environment being set correctly (which run_detection.sh does).
# Since app.py is likely run from the root, we might need to be careful.
# But detection.py uses relative imports from hailo_apps.
# Let's assume the environment is set up (via source setup_env.sh).

try:
    import detection
except ImportError:
    # Fallback if running from root without python path set?
    # Or maybe it's fine.
    print("Warning: Could not import detection.py. Make sure environment is set.")
    detection = None

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Connection Management ────────────────────────────────────────────────────

class OpenClawBridge:
    """Manages a single WebSocket bridge between a client and OpenClaw."""
    
    def __init__(self, websocket: WebSocket, connection_id: str):
        self.websocket = websocket
        self.connection_id = connection_id
        self.client: Optional[OpenClawClient] = None
        self.active = True
        self.oc_connected = False

    async def safe_send(self, data: dict):
        """Sends data through the frontend WebSocket safely."""
        if not self.active:
            return
        try:
            await self.websocket.send_json(data)
        except (WebSocketDisconnect, RuntimeError) as e:
            logger.warning(f"[{self.connection_id}] Frontend send failed: {e}")
            self.active = False
        except Exception as e:
            logger.error(f"[{self.connection_id}] Unexpected frontend send error: {e}")

    def on_chat_event(self, payload: dict):
        """Handles incoming 'chat' events from OpenClaw."""
        if not self.active or not self.client:
            return

        # Filter by session key and run ID
        if payload.get("sessionKey") != self.client.session_key:
            return
        
        run_id = payload.get("runId")
        if run_id and self.client._current_run_id and run_id != self.client._current_run_id:
            return

        state = payload.get("state")
        
        # Helper to send message in a separate task to avoid blocking the receiver
        def queue_msg(msg_data):
            if self.active:
                asyncio.create_task(self.safe_send(msg_data))

        if state == "delta":
            content = payload.get("message", {}).get("content", [])
            text = next((block.get("text", "") for block in content if block.get("type") == "text"), "")
            queue_msg({"type": "stream_delta", "text": text})

        elif state == "final":
            content = payload.get("message", {}).get("content", [])
            text = next((block.get("text", "") for block in content if block.get("type") == "text"), "")
            queue_msg({"type": "stream_final", "text": text})

        elif state == "aborted":
            queue_msg({"type": "stream_aborted"})

        elif state == "error":
            error_msg = payload.get("errorMessage", "unknown error")
            queue_msg({"type": "stream_error", "error": error_msg})

    async def connect_openclaw(self):
        """Initializes and connects the OpenClaw client."""
        try:
            self.client = OpenClawClient(url=OC_URL, token=OC_TOKEN, session_key=DEFAULT_SESSION_KEY)
            await self.client.connect()
            self.client.on_event("chat", self.on_chat_event)
            self.oc_connected = True
            logger.info(f"[{self.connection_id}] Connected to OpenClaw")
            return True
        except Exception as e:
            logger.error(f"[{self.connection_id}] OpenClaw connection failed: {e}")
            self.oc_connected = False
            return False

    async def broadcast_detections_loop(self):
        """Continuously checks and sends detections to the frontend."""
        last_detections = None
        while self.active:
            if shared_detection_state:
                _, detections = shared_detection_state.get_latest()
                if detections and detections != last_detections:
                    await self.safe_send({
                        "type": "detections",
                        "data": detections
                    })
                    last_detections = detections
            await asyncio.sleep(0.05) # 20 FPS updates

    async def send_history(self):
        """Fetches and sends chat history to the frontend."""
        if not self.oc_connected:
            return

        try:
            history = await self.client.chat_history()
            hist_messages = []
            for msg in history.get("messages", []):
                role = msg.get("role", "")
                content = msg.get("content", [])
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        text_parts.append(block)
                
                text = "\n".join(text_parts).strip()
                if text and role in ("user", "assistant"):
                    hist_messages.append({"role": role, "text": text})

            await self.safe_send({"type": "history", "messages": hist_messages})
        except Exception as e:
            logger.error(f"[{self.connection_id}] Error sending history: {e}")

    async def run(self):
        """Main loop for handling frontend messages."""
        try:
            # 1. Connect to OpenClaw
            if await self.connect_openclaw():
                # 2. Send history immediately
                await self.send_history()

            # Start detection broadcaster for this connection
            asyncio.create_task(self.broadcast_detections_loop())

            # 3. Handle messages
            while self.active:
                try:
                    data = await self.websocket.receive_json()
                except (WebSocketDisconnect, RuntimeError):
                    break

                msg_type = data.get("type")

                # Reconnect OpenClaw if it dropped
                if not self.oc_connected:
                    if await self.connect_openclaw():
                        logger.info(f"[{self.connection_id}] Reconnected to OpenClaw")

                if msg_type == "send":
                    message = data.get("message", "").strip()
                    logger.info(f"[{self.connection_id}] Received send request")
                    if message and self.oc_connected:
                        await self.safe_send({"type": "stream_start"})
                        try:
                            await self.client.chat_send(message)
                        except Exception as e:
                            logger.error(f"[{self.connection_id}] chat_send error: {e}")
                            await self.safe_send({"type": "stream_error", "error": str(e)})

                elif msg_type == "abort":
                    if self.oc_connected and self.client and self.client._current_run_id:
                        await self.client.chat_abort(self.client._current_run_id)

                elif msg_type == "reset":
                    if self.oc_connected:
                        try:
                            await self.client.session_reset()
                            await self.safe_send({"type": "session_reset"})
                        except Exception as e:
                            await self.safe_send({"type": "stream_error", "error": str(e)})

        except Exception as e:
            logger.error(f"[{self.connection_id}] Bridge loop error: {e}")
        finally:
            self.active = False
            if self.client:
                logger.info(f"[{self.connection_id}] Disconnecting OpenClaw client")
                await self.client.disconnect()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    connection_id = str(uuid.uuid4())[:8]
    logger.info(f"[{connection_id}] New connection request")
    
    await websocket.accept()
    logger.info(f"[{connection_id}] Connection accepted")

    bridge = OpenClawBridge(websocket, connection_id)
    await bridge.run()




# -----------------------------------------------------------------------------------------------
# Video Streaming & Detection Integration
# -----------------------------------------------------------------------------------------------

shared_detection_state = None

class CameraRequest(pydantic.BaseModel):
    session_id: str = "default"

@app.post("/camera/start")
async def start_camera(request: CameraRequest):
    """Start 30 fps stream only (no Hailo). Required before detection."""
    global shared_detection_state
    if not detection:
        return {"status": "error", "message": "Detection module not available"}, 503
    try:
        shared_detection_state = detection.start_detection(request.session_id)
        return {"status": "started"}
    except Exception as e:
        logger.exception("Camera start failed")
        return {"status": "error", "message": str(e)}, 500

@app.post("/camera/stop")
async def stop_camera(request: CameraRequest):
    """Stop stream (and detection if active)."""
    if detection:
        detection.stop_detection(request.session_id)
    return {"status": "stopped"}

@app.post("/camera/detection/start")
async def start_camera_detection(request: CameraRequest):
    """Start object detection at 5 fps (Hailo). Stream must be running."""
    if detection:
        ok = detection.start_detection_mode(request.session_id)
        return {"status": "started" if ok else "error", "message": "Detection started" if ok else "Start camera first"}
    return {"status": "error", "message": "Detection module not available"}

@app.post("/camera/detection/stop")
async def stop_camera_detection(request: CameraRequest):
    """Stop object detection."""
    if detection:
        detection.stop_detection_mode(request.session_id)
    return {"status": "stopped"}


def generate_frames():
    """Generates MJPEG frames from the shared state."""
    first_frame = True
    while True:
        if shared_detection_state:
            frame, _ = shared_detection_state.get_latest()
            if frame is not None:
                if first_frame:
                    print("DEBUG: generate_frames received first frame!")
                    first_frame = False
                # Encode frame to JPEG
                # Frame is RGB, OpenCV expects BGR
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                ret, buffer = cv2.imencode('.jpg', frame_bgr)
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                # Debugging potential stuck state
                # print("DEBUG: generate_frames waiting for frame...")
                pass
        
        # Avoid tight loop if no frame
        import time
        time.sleep(0.03)

@app.get("/video_feed")
async def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")


# -----------------------------------------------------------------------------------------------
# WebSocket Broadcasting
# -----------------------------------------------------------------------------------------------

# We can reuse the existing WebSocket bridge to send detection data, 
# or use a dedicated method. To keep it simple, we'll modify the loop 
# to check for detections and send them.
# However, the bridge loop blocks on receive.
# Better to have a background task or just rely on the client polling?
# Or we can push.

# Let's add a background broadcaster that pushes to all active bridges.

# Easier approach: Client requests detections or we piggyback on existing ws connection.
# Let's modify OpenClawBridge to include a detection broadcasting task.

if __name__ == "__main__":
    import uvicorn
    # Need to run with setup_env.sh sourced if running directly
    uvicorn.run(app, host="0.0.0.0", port=8000)
