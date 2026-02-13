# Detection Refactor Plan: 30 fps Stream + 5 fps Detection Modes

## Goal

- **Mode 1 – Live stream (30 fps)**: Camera-only view when the camera screen is open. No Hailo; stream frames to the frontend at ~30 fps for real-time view.
- **Mode 2 – Object detection (5 fps)**: When the user presses a “Detect” button, enable object detection. Run inference at 5 fps (send every Nth frame to the Hailo hat), return classes and bounding boxes to the frontend. The video stream stays at 30 fps; detections are overlaid at 5 fps.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Frontend (CameraView)                                                        │
│  - Video: <img src="/video_feed">  (always 30 fps)                           │
│  - Detections: WebSocket "detections" messages (only when Detect is on, 5 fps)│
│  - "Detect" button → POST /camera/detection/start                            │
│  - "Stop detect" or leave → POST /camera/detection/stop                       │
└─────────────────────────────────────────────────────────────────────────────┘
                    │                              │
                    ▼                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  app.py (FastAPI)                                                             │
│  - GET /video_feed     → MJPEG from shared_state.frame (30 fps)              │
│  - POST /camera/start  → start stream process only                            │
│  - POST /camera/stop   → stop stream process                                  │
│  - POST /camera/detection/start  → start detection process (5 fps, Hailo)    │
│  - POST /camera/detection/stop  → stop detection process                      │
│  - WebSocket → broadcast shared_state.detections when non-empty               │
└─────────────────────────────────────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌───────────────────┐   ┌───────────────────┐
│ Stream process    │   │ Detection process │  (only when Detect on)
│ (always when      │   │ - Reads every 6th │
│  camera open)     │   │   frame from      │
│ - Picamera2       │──▶│   detection_queue │
│   30 fps          │   │ - Pushes to       │
│ - Puts every      │   │   appsrc @ 5 fps  │
│   frame in        │   │ - GStreamer       │
│   stream_queue    │   │   Hailo pipeline  │
│ - When detect on:  │   │ - Puts (detections)│
│   every 6th frame │   │   in det_queue    │
│   in detection_   │   │                   │
│   queue           │   └───────────────────┘
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Main process      │
│ - Thread: consume │
│   stream_queue →  │
│   shared_state.   │
│   update_frame()  │
│ - When detect on: │
│   thread consumes │
│   det_queue →     │
│   shared_state.   │
│   update_detections()│
└───────────────────┘
```

---

## 1. Shared State Changes

**File: `detection.py`**

- Extend `SharedState` so frame and detections can be updated independently:
  - `update_frame(frame)` – used by the stream consumer (30 fps).
  - `update_detections(detections)` – used by the detection monitor (5 fps).
  - Keep `update(frame, detections)` for backward compatibility or remove if unused.
  - `get_latest()` still returns `(frame, detections)`; frame comes from stream, detections from detection process when enabled.
- When detection is off, `detections` is `[]` (cleared on detection stop).

---

## 2. Stream-Only Process (30 fps, No Hailo)

**File: `detection.py`**

- Add a **stream process** that:
  - Uses **only** Picamera2 (no GStreamer, no Hailo).
  - Captures at 30 fps in a loop.
  - Puts each frame into a **stream queue** (e.g. `multiprocessing.Queue(maxsize=2)`).
  - Optional: takes a `multiprocessing.Value("detection_enabled")` and a **detection queue**. When `detection_enabled` is true, also push **every 6th frame** into the detection queue (so ~5 fps).
  - Respects a stop event so the process can be shut down cleanly when the user leaves the camera view.
- Entry point: e.g. `run_stream_process(stream_queue, stop_event, detection_enabled=None, detection_queue=None)`.
- No Hailo imports or GStreamer in this process; keep it minimal so it can run without the Hailo hat.

**Main process**

- When camera view opens (`POST /camera/start`):
  - Start only the **stream process** (and the thread that consumes `stream_queue` and calls `shared_state.update_frame(...)`).
  - Do **not** start the detection process or load Hailo.
- Consumer thread in the main process:
  - Loop: get frame from `stream_queue` → `shared_state.update_frame(frame)`.
  - Optionally: when detection is disabled, call `shared_state.update_detections([])` so the UI clears boxes.

---

## 3. Detection Process (5 fps, Hailo)

**File: `detection.py`**

- Detection runs **only** when the user has pressed “Detect” (`POST /camera/detection/start`).
- **Input**: Frames from the **detection queue** (every 6th frame from the stream process, so ~5 fps).
- **Pipeline**: Keep the existing GStreamer + Hailo pipeline, but **feed appsrc from the queue** instead of from a camera thread:
  - Replace the “Picamera2 → appsrc” thread with a **frame-feeder thread** that:
    - Does `frame = detection_queue.get()` (blocking).
    - Pushes the frame into the pipeline’s appsrc at 5 fps (e.g. 0.2 s between frames).
  - Pipeline: `appsrc` → (existing Hailo inference) → callback.
- **Output**: In the callback, you only need **detections** (classes + bboxes). Either:
  - Put `(None, detections)` or `detections` into a **detections queue** that the main process consumes, or
  - Reuse the existing `frame_queue` but only send detections (main process updates only `shared_state.detections` from this queue).
- **Process lifecycle**:
  - Start: when `POST /camera/detection/start` is called (and stream process is already running). Create detection queue, set `detection_enabled = True`, spawn detection process, start thread that reads detections and calls `shared_state.update_detections(...)`.
  - Stop: when `POST /camera/detection/stop` or user leaves camera view. Set `detection_enabled = False`, signal detection process to exit, join it, then clear `shared_state.update_detections([])`.

---

## 4. Throttling: 30 fps → 5 fps for Hailo

- In the **stream process**, maintain a frame counter. When `detection_enabled` is true and `frame_count % 6 == 0`, push the current frame into `detection_queue`. So the detection process receives one frame every 6 frames (~5 fps for 30 fps input).
- Alternatively, use a time-based throttle (e.g. push at most one frame every 0.2 s). Prefer frame-based for predictable load.

---

## 5. API and App Changes

**File: `app.py`**

- **Keep**: `POST /camera/start` → start **stream process** only (and stream consumer thread). Set `shared_detection_state = ...` so `generate_frames()` and WebSocket can read from it.
- **Keep**: `POST /camera/stop` → stop stream process (and stream consumer); if detection was on, also stop detection process and clear detections.
- **Add**: `POST /camera/detection/start` → enable detection (set flag, create detection queue if needed, start detection process, start detection-monitor thread). Ensure stream process has been told to fill the detection queue (e.g. pass `detection_enabled` and `detection_queue` when starting stream process, or a separate “enable detection” mechanism that the stream process checks).
- **Add**: `POST /camera/detection/stop` → stop detection process, set `detection_enabled = False`, clear `shared_state.detections` (or call `update_detections([])`).
- **Video feed**: Unchanged; still reads `shared_detection_state.get_latest()` and uses the frame for MJPEG. Now the frame is always from the stream process (30 fps).
- **WebSocket**: Keep sending `detections` in the bridge when `shared_detection_state.get_latest()[1]` is non-empty (or always send; frontend can hide overlays when empty).

**Request models**

- Reuse or extend `CameraRequest` (e.g. optional `session_id`) for the new endpoints if needed.

---

## 6. Frontend Changes

**File: `chat-gui/src/renderer/src/components/CameraView.jsx`**

- Add a **“Detect”** button (e.g. in the header or footer).
  - On click: `POST /camera/detection/start` (and optionally set local state like `detectionActive: true`).
  - When detection is on, show a “Stop detection” or toggle the same button to call `POST /camera/detection/stop` and set `detectionActive: false`.
- **Bounding boxes**: Render only when `detectionActive` (or when `detections.length > 0`). When the user stops detection, clear boxes (backend will send empty list).
- Keep existing behavior: video feed and WebSocket for detections; only the source of detections (5 fps, on-demand) and the new button/toggle change.

---

## 7. File Layout (detection.py)

Suggested structure:

1. **Imports and shared state** – keep at top; add `update_frame` / `update_detections` to `SharedState`.
2. **Stream-only process** – `run_stream_process(stream_queue, stop_event, detection_enabled, detection_queue)` (Picamera2 loop, no GStreamer/Hailo).
3. **Detection process** – `run_detection_process(detection_queue, detections_output_queue, stop_event)` (or keep current signature and pass queues). Uses GStreamer + Hailo; frame-feeder thread reads from `detection_queue` and pushes to appsrc at 5 fps.
4. **Main-process helpers**:
   - `start_stream()` – start stream process + stream consumer thread; create and pass `detection_enabled` and `detection_queue` (can be created at start and left empty until detection is enabled).
   - `stop_stream()` – stop stream process and consumer.
   - `start_detection()` – set `detection_enabled = True`, start detection process, start detection-monitor thread.
   - `stop_detection()` – set `detection_enabled = False`, stop detection process, clear detections.
5. **Ref-count / lifecycle**: Keep ref-count for “camera view open” so that one user opening the camera doesn’t stop the stream when another is still viewing. Detection can be a separate ref-count or a simple boolean (only one viewer can enable detection at a time, or share the same detection state).

---

## 8. Implementation Order

1. **SharedState** – add `update_frame` and `update_detections`; ensure `get_latest()` still returns `(frame, detections)`.
2. **Stream process** – implement `run_stream_process` with 30 fps capture and `stream_queue` only (no detection queue yet). Main process: start/stop stream process and consumer thread; wire `generate_frames()` to this (so camera view works without Hailo).
3. **App routes** – change `POST /camera/start` to start only the stream process; ensure `POST /camera/stop` stops it. Verify 30 fps view works without detection.
4. **Detection queue and throttle** – add `detection_enabled` and `detection_queue` to the stream process; when enabled, push every 6th frame to `detection_queue`.
5. **Detection process** – modify to accept frames from `detection_queue` (frame-feeder thread → appsrc) and run at 5 fps; output only detections (or frame + detections) to main process; main process updates only `shared_state.detections`.
6. **App routes** – add `POST /camera/detection/start` and `POST /camera/detection/stop`; start/stop detection process and detection-monitor thread; clear detections when stopping.
7. **Frontend** – add Detect button and call the new endpoints; show/hide bounding boxes based on detection state.

---

## 9. Edge Cases

- **User opens camera, then enables detection, then disables detection, then leaves**: Stream stops when they leave; detection stops when they disable or leave. Clear detections on disable and on leave.
- **User leaves camera view while detection is on**: On `POST /camera/stop`, stop both stream and detection processes and clear state.
- **Detection process slow**: If Hailo can’t keep 5 fps, the detection queue may grow; use a small maxsize (e.g. 1–2) and drop oldest so the stream stays responsive.
- **Stream process must not block on detection queue**: Use `put_nowait` or a short timeout when pushing to `detection_queue` so a slow detection consumer doesn’t slow the 30 fps stream.

---

## 10. Summary Table

| Component            | 30 fps stream mode      | 5 fps detection mode (on Detect)   |
|----------------------|-------------------------|------------------------------------|
| Stream process       | Picamera2 → stream_queue | Same + every 6th frame → detection_queue |
| Main process         | Consume stream_queue → update_frame | Consume det_queue → update_detections    |
| Detection process    | Not running             | Consume detection_queue → appsrc @ 5 fps → Hailo → detections queue |
| Hailo                | Not used                | Used at 5 fps                       |
| Frontend             | Video + optional boxes  | Video + bounding boxes from WS      |

This plan keeps the 30 fps path free of Hailo and adds an on-demand 5 fps detection path fed by the same camera stream, with clear API and lifecycle for both modes.
