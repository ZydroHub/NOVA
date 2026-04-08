import logging
import os
import uvicorn
import psutil
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import PORT, setup_logging
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

# Include the routers
app.include_router(chat_router)

@app.get("/health")
async def health():
    """Simple health check for monitoring and tests."""
    return {"status": "ok"}


@app.get("/system/stats")
async def system_stats():
    """Get current system stats (CPU, RAM, Temperature)."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        ram_percent = ram.percent
        
        # Try to get temperature (may not work in VM or without sensors)
        temp = 0
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                # Get the first available temperature sensor
                for name, entries in temps.items():
                    if entries:
                        temp = entries[0].current
                        break
            else:
                logger.debug("No temperature sensors available in this environment.")
        except (AttributeError, OSError):
            # Temperature sensors not available (common in VMs)
            temp = 0
            logger.debug("Temperature sensors are not supported in this environment.")
        
        stats = {
            "cpu": round(cpu_percent, 1),
            "ram": round(ram_percent, 1),
            "temp": round(temp, 1)
        }
        logger.debug("System stats sampled: %s", stats)
        return stats
    except Exception as e:
        logger.warning("Error getting system stats: %s", e)
        return {
            "cpu": 0,
            "ram": 0,
            "temp": 0
        }


@app.on_event("startup")
async def startup_event():
    logger.info("Unified Backend starting up on port %s", PORT)
    logger.debug("SKIP_MODEL_LOAD=%s", os.environ.get("SKIP_MODEL_LOAD", ""))
    if not os.environ.get("SKIP_MODEL_LOAD"):
        logger.info("Loading chat model...")
        ai_state.load_model()
        logger.info("Chat model loaded.")
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
