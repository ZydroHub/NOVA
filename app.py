from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import logging
import sys
import uuid
import pydantic
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

# Import OpenClawClient from the existing file
try:
    from openclaw_client import OpenClawClient, load_openclaw_config, DEFAULT_SESSION_KEY
    from scheduled_tasks_manager import ScheduledTasksManager
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
import multiprocessing
import queue
import threading

# Import camera_stream module
try:
    import camera_stream
except ImportError:
    print("Warning: Could not import camera_stream.py.")
    camera_stream = None

import psutil
import time

def get_cpu_temp():
    """Returns CPU temperature in Celsius."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return float(f.read()) / 1000.0
    except:
        return 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Shutdown: stop camera process so the server can exit cleanly
    perform_actual_shutdown()
    if gpio_manager:
        gpio_manager.close_all()
    logger.info("Backend shutdown complete.")


app = FastAPI(lifespan=lifespan)

# Initialize GPIO Manager
try:
    from gpio_manager import GPIOManager
    gpio_manager = GPIOManager()
except ImportError:
    dprint("Warning: Could not import GPIOManager.")
    gpio_manager = None
except Exception as e:
    print(f"Warning: Error initializing GPIOManager: {e}")
    gpio_manager = None

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/system/stats")
async def get_system_stats():
    """Returns current system statistics."""
    return {
        "time": time.strftime("%H:%M:%S"),
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory_percent": psutil.virtual_memory().percent,
        "temperature": get_cpu_temp()
    }


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
                    images = data.get("images", [])
                    
                    logger.info(f"[{self.connection_id}] Received send request (images={len(images)})")
                    
                    if (message or images) and self.oc_connected:
                        await self.safe_send({"type": "stream_start"})
                        
                        full_message = message
                        
                        # Append images if any
                        if images:
                            try:
                                base_dir = os.path.dirname(os.path.abspath(__file__))
                                img_dir_local = os.path.join(base_dir, "img")
                                
                                for img_name in images:
                                    # Basic security check
                                    if ".." in img_name or "/" in img_name or "\\" in img_name:
                                        logger.warning(f"[{self.connection_id}] Skipped unsafe image path: {img_name}")
                                        continue
                                        
                                    abs_path = os.path.join(img_dir_local, img_name)
                                    # Append text representation for the model
                                    full_message += f"\n\n[Image: {abs_path}]"
                            except Exception as e:
                                logger.error(f"Error processing images: {e}")

                        try:
                            await self.client.chat_send(full_message)
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

                # --- New Handlers for Scheduled Tasks ---
                elif msg_type == "cron.list":
                    try:
                        manager = ScheduledTasksManager(self.client)
                        jobs = await manager.list_cron_jobs()
                        await self.safe_send({
                            "type": "cron_list",
                            "jobs": jobs
                        })
                    except Exception as e:
                        logger.error(f"[{self.connection_id}] cron.list error: {e}")
                        await self.safe_send({"type": "stream_error", "error": f"cron.list error: {e}"})

                elif msg_type == "cron.add":
                    try:
                        manager = ScheduledTasksManager(self.client)
                        name = data.get("name")
                        schedule = data.get("schedule")
                        job_payload = data.get("payload", {})
                        description = data.get("description", "")
                        
                        if not name or not schedule:
                            raise ValueError("Missing name or schedule")
                            
                        # Use default session key if client session key not set, or pass explicitly
                        session_key = self.client.session_key if self.client else DEFAULT_SESSION_KEY
                        
                        # Pass description if supported by manager/API
                        # We need to update ScheduledTasksManager to accept it, 
                        # or just bypass it here if we want to be quick, but let's do it right.
                        # The manager.add_cron_job currently takes fixed args.
                        # Let's call client.request directly or update the manager signature in a separate step?
                        # Since `manager` is just a helper, let's just make the request here or update the manager.
                        # Updating app.py is the critical path since it has the code.
                        
                        params = {
                            "name": name,
                            "schedule": schedule,
                            "sessionTarget": session_key,
                            "payload": job_payload,
                            "description": description
                        }
                        
                        res = await self.client.request("cron.add", params)
                        await self.safe_send({"type": "cron_added", "result": res})
                    except Exception as e:
                        logger.error(f"[{self.connection_id}] cron.add error: {e}")
                        await self.safe_send({"type": "stream_error", "error": f"cron.add error: {e}"})

                elif msg_type == "cron.remove":
                    try:
                        manager = ScheduledTasksManager(self.client)
                        job_id = data.get("id")
                        if not job_id:
                            raise ValueError("Missing job id")
                        res = await manager.remove_cron_job(job_id)
                        await self.safe_send({"type": "cron_removed", "result": res})
                    except Exception as e:
                        logger.error(f"[{self.connection_id}] cron.remove error: {e}")
                        await self.safe_send({"type": "stream_error", "error": f"cron.remove error: {e}"})

                elif msg_type == "heartbeat.get":
                    try:
                        manager = ScheduledTasksManager(self.client)
                        status = await manager.get_heartbeat_status()
                        await self.safe_send({"type": "heartbeat_status", "status": status})
                    except Exception as e:
                        logger.error(f"[{self.connection_id}] heartbeat.get error: {e}")
                        await self.safe_send({"type": "stream_error", "error": f"heartbeat.get error: {e}"})

                elif msg_type == "heartbeat.set":
                    try:
                        manager = ScheduledTasksManager(self.client)
                        active = data.get("active", False)
                        interval = data.get("interval", 30)
                        
                        session_key = self.client.session_key if self.client else DEFAULT_SESSION_KEY
                        res = await manager.set_heartbeat(active, interval, session_key)
                        await self.safe_send({"type": "heartbeat_updated", "status": res})
                    except Exception as e:
                        logger.error(f"[{self.connection_id}] heartbeat.set error: {e}")
                        await self.safe_send({"type": "stream_error", "error": f"heartbeat.set error: {e}"})

                # --- GPIO Controls ---
                elif msg_type == "gpio.get_all":
                    try:
                        if gpio_manager:
                            # Refresh state map
                            states = gpio_manager.get_header_state()
                            await self.safe_send({"type": "gpio_state", "pins": states})
                        else:
                            await self.safe_send({"type": "stream_error", "error": "GPIO Manager not available"})
                    except Exception as e:
                        logger.error(f"[{self.connection_id}] gpio.get_all error: {e}")
                
                elif msg_type == "gpio.set_mode":
                    try:
                        if gpio_manager:
                            bcm = data.get("bcm")
                            mode = data.get("mode") # 'input' or 'output'
                            if bcm is not None and mode:
                                success = gpio_manager.setup_pin(bcm, mode)
                                if success:
                                    # Send updated state back
                                    states = gpio_manager.get_header_state()
                                    await self.safe_send({"type": "gpio_state", "pins": states})
                                else:
                                    await self.safe_send({"type": "stream_error", "error": f"Failed to set GPIO {bcm} to {mode}"})
                    except Exception as e:
                        logger.error(f"[{self.connection_id}] gpio.set_mode error: {e}")

                elif msg_type == "gpio.write":
                    try:
                        if gpio_manager:
                            bcm = data.get("bcm")
                            value = data.get("value") # 0 or 1
                            if bcm is not None and value is not None:
                                success = gpio_manager.set_pin_value(bcm, int(value))
                                if success:
                                    # Send updated state back
                                    states = gpio_manager.get_header_state()
                                    await self.safe_send({"type": "gpio_state", "pins": states})
                                else:
                                    await self.safe_send({"type": "stream_error", "error": f"Failed to write {value} to GPIO {bcm}"})
                    except Exception as e:
                        logger.error(f"[{self.connection_id}] gpio.write error: {e}")

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

# -----------------------------------------------------------------------------------------------
# Video Streaming & Camera Management
# -----------------------------------------------------------------------------------------------

class SharedState:
    def __init__(self):
        self.frame = None
        self.lock = threading.Lock()

    def update_frame(self, frame):
        with self.lock:
            self.frame = frame

    def get_latest(self):
        with self.lock:
            if self.frame is None:
                return None, None
            return self.frame.copy(), None # No detections

shared_state = SharedState()
stream_process = None
stream_queue = None
stream_stop_event = None
stream_consumer_thread = None

# Stream ref-count and shutdown (camera view open/close)
ref_count = 0
shutdown_timer = None
session_lock = threading.Lock()

def _stream_consumer_loop(q):
    """Consumes stream_queue in main process; updates shared_state.frame (30 fps)."""
    while True:
        try:
            frame = q.get(timeout=1.0)
            shared_state.update_frame(frame)
        except queue.Empty:
            if stream_process is None or not stream_process.is_alive():
                break
            continue
        except Exception as e:
            logger.debug("Stream consumer error: %s", e)
            break

def _spawn_stream_process():
    """Start stream process and stream consumer thread."""
    global stream_process, stream_queue, stream_stop_event, stream_consumer_thread
    
    stream_stop_event = multiprocessing.Event()
    stream_queue = multiprocessing.Queue(maxsize=2)
    
    # We don't use detection queue anymore
    detection_enabled = multiprocessing.Value("b", False)
    detection_queue = None

    stream_process = multiprocessing.Process(
        target=camera_stream.run_stream_process,
        args=(stream_queue, stream_stop_event, detection_enabled, detection_queue),
        # Default camera_stream width/height is 640x384 which fits our UI logic well enough
        daemon=False,
    )
    stream_process.start()

    stream_consumer_thread = threading.Thread(target=_stream_consumer_loop, args=(stream_queue,), daemon=True)
    stream_consumer_thread.start()

def start_camera_manager(session_id=None):
    """
    Starts the stream process if not already running.
    Increments ref count for camera view.
    """
    global stream_process, ref_count, shutdown_timer

    with session_lock:
        ref_count += 1
        logger.info(f"Start stream requested (session_id={session_id}). Ref count: {ref_count}")

        if shutdown_timer is not None:
            shutdown_timer.cancel()
            shutdown_timer = None

        if stream_process is not None and stream_process.is_alive():
            logger.info("Stream process already running.")
            return

        logger.info("Spawning stream process...")
        _spawn_stream_process()


def stop_camera_manager(session_id=None):
    """Decrements ref count. If 0, schedules stream shutdown."""
    global ref_count, shutdown_timer

    with session_lock:
        if ref_count > 0:
            ref_count -= 1
        logger.info(f"Stop stream requested (session_id={session_id}). Ref count: {ref_count}")

        if ref_count == 0:
            if shutdown_timer is not None:
                shutdown_timer.cancel()
            # 1.5s delay so React Strict Mode's second mount can send start and cancel this
            shutdown_timer = threading.Timer(1.5, perform_actual_shutdown)
            shutdown_timer.start()

    return True

def perform_actual_shutdown():
    """Stops the stream process."""
    global stream_process, stream_queue, stream_stop_event, ref_count, shutdown_timer

    with session_lock:
        if ref_count > 0:
            return
        proc = stream_process
        logger.info("Performing stream shutdown...")

    if stream_stop_event:
        stream_stop_event.set()
    
    if proc and proc.is_alive():
        proc.join(timeout=2.0)
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=1.0)
    
    with session_lock:
        stream_process = None
        stream_queue = None
        shutdown_timer = None

class CameraRequest(pydantic.BaseModel):
    session_id: str = "default"

@app.post("/camera/start")
async def start_camera(request: CameraRequest):
    """Start 30 fps stream."""
    try:
        start_camera_manager(request.session_id)
        return {"status": "started"}
    except Exception as e:
        logger.exception("Camera start failed")
        return {"status": "error", "message": str(e)}, 500

@app.post("/camera/stop")
async def stop_camera(request: CameraRequest):
    """Stop stream."""
    stop_camera_manager(request.session_id)
    return {"status": "stopped"}


@app.post("/camera/capture")
async def capture_camera_frame(request: CameraRequest):
    """Capture the current frame and save it to disk."""
    import datetime
    import os
    
    if not stream_process:
        return {"status": "error", "message": "Camera not running"}, 400
        
    frame, _ = shared_state.get_latest()
    if frame is None:
        return {"status": "error", "message": "No frame available"}, 503
        
    try:
        # Rotate 90 degrees clockwise to match UI
        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        
        # Convert RGB to BGR for OpenCV saving
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Ensure img directory exists
        # Use the directory where app.py is located, not the CWD (which might be hailo-apps)
        img_dir = "/home/pocket-ai/Pictures"        
        os.makedirs(img_dir, exist_ok=True)
        
        # Generate timestamped filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"capture_{timestamp}.jpg"
        filepath = os.path.join(img_dir, filename)
        
        # Save image
        cv2.imwrite(filepath, frame_bgr)
        logger.info(f"Image saved to {filepath}")
        
        return {"status": "success", "filename": filename, "filepath": filepath}
    except Exception as e:
        logger.exception("Failed to save image")
        return {"status": "error", "message": str(e)}, 500


def generate_frames():
    """Generates MJPEG frames from the shared state."""
    first_frame = True
    while True:
        frame, _ = shared_state.get_latest()
        if frame is not None:
            if first_frame:
                print("DEBUG: generate_frames received first frame!")
                first_frame = False
            # Rotate 90° clockwise for portrait display in the UI
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            # Encode frame to JPEG; frame is RGB, OpenCV expects BGR
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            ret, buffer = cv2.imencode('.jpg', frame_bgr)
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
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


# -----------------------------------------------------------------------------------------------
# Gallery & Static Files
# -----------------------------------------------------------------------------------------------

from fastapi.staticfiles import StaticFiles
import os

# Ensure img directory exists for StaticFiles to mount without error
# app.py is in /home/pocket-ai/Documents/pocket-ai/
# We want img to be in /home/pocket-ai/Documents/pocket-ai/img
# We want img to be in /home/pocket-ai/Pictures
img_dir = "/home/pocket-ai/Pictures"
os.makedirs(img_dir, exist_ok=True)

# Mount the img directory to serve images statically
app.mount("/img", StaticFiles(directory=img_dir), name="img")

# ----------------- Agentic Coding Workspace -----------------
WORKSPACE_DIR = "/home/pocket-ai/.openclaw/workspace/code projects"
# Ensure workspace directory exists
try:
    os.makedirs(WORKSPACE_DIR, exist_ok=True)
except Exception as e:
    logger.error(f"Failed to create workspace dir: {e}")

# Mount the workspace directory to serve the apps
app.mount("/apps", StaticFiles(directory=WORKSPACE_DIR, html=True), name="apps")

@app.get("/workspace/projects")
async def list_workspace_projects():
    """List all projects (subdirectories) in the workspace."""
    try:
        projects = []
        if os.path.exists(WORKSPACE_DIR):
            for item in os.listdir(WORKSPACE_DIR):
                item_path = os.path.join(WORKSPACE_DIR, item)
                if os.path.isdir(item_path):
                    projects.append(item)
        projects.sort()
        return {"status": "success", "projects": projects}
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/gallery/images")
async def get_gallery_images():
    """List all images in the img directory, sorted by newest first."""
    try:
        files = [f for f in os.listdir(img_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        # Sort by modification time, newest first
        files.sort(key=lambda x: os.path.getmtime(os.path.join(img_dir, x)), reverse=True)
        
        # Return list of URLs/filenames
        # Since we mounted /img, the URL is /img/filename
        image_list = [{"filename": f, "url": f"/img/{f}"} for f in files]
        return {"status": "success", "images": image_list}
    except Exception as e:
        logger.error(f"Error listing gallery images: {e}")
        return {"status": "error", "message": str(e)}

@app.delete("/gallery/images/{filename}")
async def delete_gallery_image(filename: str):
    """Delete an image from the gallery."""
    try:
        # Basic security check to prevent path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
             return {"status": "error", "message": "Invalid filename"}, 400
             
        filepath = os.path.join(img_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return {"status": "success", "message": f"Deleted {filename}"}
        else:
            return {"status": "error", "message": "File not found"}, 404
    except Exception as e:
        logger.error(f"Error deleting image: {e}")
        return {"status": "error", "message": str(e)}, 500

if __name__ == "__main__":
    import uvicorn
    # Need to run with setup_env.sh sourced if running directly
    uvicorn.run(app, host="0.0.0.0", port=8000)
