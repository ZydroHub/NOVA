import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import routers and state from our modules
from camera_stream import router as camera_router
from chat_ai import router as chat_router, ai as ai_state

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
os.makedirs("captures", exist_ok=True)
app.mount("/captures", StaticFiles(directory="captures"), name="captures")

# Include the routers
app.include_router(camera_router)
app.include_router(chat_router)

@app.on_event("startup")
async def startup_event():
    # Initialize the AI models on startup
    print("Unified Backend starting up...")
    ai_state.load_model()
    print("Unified Backend ready.")

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
    # Run everything on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
