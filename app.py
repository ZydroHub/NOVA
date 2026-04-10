import logging
import math
import os
import subprocess
from datetime import datetime
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

        temp = _read_temperature_celsius()
        now = datetime.now().strftime("%H:%M:%S")
        cpu_value = _finite_float(cpu_percent)
        ram_value = _finite_float(ram_percent)
        temp_value = _finite_float(temp)

        stats = {
            # Canonical keys used by the renderer.
            "time": now,
            "cpu_percent": round(cpu_value, 1),
            "memory_percent": round(ram_value, 1),
            "temperature": round(temp_value, 1),
            # Backward-compatible aliases.
            "cpu": round(cpu_value, 1),
            "ram": round(ram_value, 1),
            "temp": round(temp_value, 1)
        }
        logger.debug("System stats sampled: %s", stats)
        return stats
    except Exception as e:
        logger.warning("Error getting system stats: %s", e)
        return {
            "time": datetime.now().strftime("%H:%M:%S"),
            "cpu_percent": 0,
            "memory_percent": 0,
            "temperature": 0,
            "cpu": 0,
            "ram": 0,
            "temp": 0
        }


def _read_temperature_celsius() -> float:
    """Read CPU temperature with Linux/Raspberry Pi fallbacks."""
    # 1) psutil sensors API (works on many Linux systems, including some Pi setups).
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for entries in temps.values():
                if entries and entries[0].current is not None:
                    return float(entries[0].current)
    except (AttributeError, OSError):
        pass

    # 2) Direct sysfs read (common on Raspberry Pi).
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r", encoding="utf-8") as f:
            milli_c = f.read().strip()
        if milli_c:
            return float(milli_c) / 1000.0
    except (OSError, ValueError):
        pass

    # 3) vcgencmd fallback (Pi firmware utility).
    try:
        result = subprocess.run(
            ["vcgencmd", "measure_temp"],
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        )
        output = (result.stdout or "").strip()
        # Expected format: temp=52.8'C
        if output.startswith("temp=") and "'" in output:
            value = output.split("=", 1)[1].split("'", 1)[0]
            return float(value)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass

    logger.debug("Temperature sources unavailable; returning 0C.")
    return 0.0


def _finite_float(value: float, fallback: float = 0.0) -> float:
    """Convert numeric-like values to a finite float, with fallback on NaN/inf/errors."""
    try:
        number = float(value)
        return number if math.isfinite(number) else fallback
    except (TypeError, ValueError):
        return fallback


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
