import logging
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import PORT, CAPTURES_DIR, setup_logging
from camera_stream import router as camera_router
from chat_ai import router as chat_router, ai as ai_state

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Pocket AI Unified Backend")

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for gallery
os.makedirs(CAPTURES_DIR, exist_ok=True)
app.mount("/captures", StaticFiles(directory=CAPTURES_DIR), name="captures")

# Include the routers
app.include_router(camera_router)
app.include_router(chat_router)

@app.get("/health")
async def health():
    """Simple health check for monitoring and tests."""
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    logger.info("Unified Backend starting up...")
    if not os.environ.get("SKIP_MODEL_LOAD"):
        ai_state.load_model()
        # Tool model is loaded in a subprocess when needed (avoids thread/crash issues)
    try:
        from task_scheduler import init_scheduler
        init_scheduler(ai_state.conv_manager)
    except Exception as e:
        logger.warning("Task scheduler not started: %s", e)
    logger.info("Unified Backend ready.")

@app.post("/shutdown")
async def shutdown():
    import threading
    import time
    def delayed_exit():
        time.sleep(1)
        os._exit(0)
    threading.Thread(target=delayed_exit, daemon=True).start()
    return {"status": "shutting down..."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
