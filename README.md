# Pocket AI

**Version 1** — *Project in active development; more features planned.*

A local-first AI assistant with voice, chat, and camera. Backend runs a small GGUF LLM (Qwen), Piper TTS, and optional Whisper/Vosk STT. The GUI is an Electron + React app that talks to the backend over HTTP and WebSockets.

---

## What’s in the repo

- **Backend (Python)**  
  - FastAPI app (`app.py`) with CORS, static files, and routers.  
  - **Chat** (`chat_ai.py`): conversation CRUD, WebSocket chat, voice pipeline (STT → LLM → TTS).  
  - **Camera** (`camera_stream.py`): Pi Camera 2 stream, MJPEG feed, capture, gallery, detection hooks.  
  - **TTS** (`tts_piper.py`): Piper-based speech output.  
  - **STT** (`stt_whisper.py`, `stt_vosk.py`): optional Whisper and Vosk engines.

- **Frontend (Electron + React)**  
  - `chat-gui/`: Vite + React 19, Tailwind, Framer Motion, React Router.  
  - Features: home screen, chat UI with sidebar, camera view, settings, WebSocket context for chat and voice.

- **Data**  
  - Conversations stored in `conversations.json`.  
  - Captures in `captures/`.  
  - GGUF model (e.g. Qwen3-0.6B) under `models/` (downloaded on first run if missing).

---

## Requirements

- **Python**: 3.10+ (tested with 3.13).  
- **Node**: for the Electron GUI (see `chat-gui/package.json`).  
- **Raspberry Pi** (optional): for `picamera2` and camera stream; on Pi you may use a venv with `--system-site-packages` or install `picamera2` via apt.

---

## Backend setup

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. **Raspberry Pi camera**: If you need the camera stream on a Pi, install `picamera2` via your system package manager (or use a venv with `--system-site-packages` and install it there), then uncomment the `picamera2` line in `requirements.txt` if you want it in the venv.

4. **Vosk**: Download a Vosk language model and point your STT code to it (see `stt_vosk.py`).

5. Run the backend:
   ```bash
   python app.py
   ```
   Server runs at `http://0.0.0.0:8000`.

---

## Frontend (chat GUI) setup

```bash
cd chat-gui
npm install
npm run dev
```

- Use **Build** when you want a packaged app:
  ```bash
  npm run build
  ```

The GUI expects the backend to be running (e.g. on port 8000); you can start it with `npm run backend` from `chat-gui` (runs `python ../app.py`) or run `app.py` from the repo root.

---

## Main endpoints (backend)

| Area        | Examples |
|------------|----------|
| Chat       | `GET/POST /conversations`, `GET /conversations/{id}`, `WS /ws/chat/{conv_id}` |
| Voice      | `WS /ws/voice` (commands: start_vosk, stop_vosk, toggle_voice, abort) |
| Camera     | `POST /camera/start`, `POST /camera/stop`, `GET /video_feed`, `POST /camera/capture` |
| Gallery    | `GET /gallery/images`, `DELETE /gallery/images/{filename}` |
| System     | `GET /system/stats` |
| Shutdown   | `POST /shutdown` |

---

## Project status

This is **v1** of the README. The project is **not finished**; features and structure may change as you add more. This file will be updated as the project evolves.
