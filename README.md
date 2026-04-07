# NOVA AI

**Version 1** — *Project in active development; more features planned.*

A **Raspberry Pi 5**–focused, local-first AI assistant with voice and chat. fork of Pocket-AI. The backend runs a small GGUF LLM (Qwen), Piper TTS, and optional Whisper/Vosk STT. The GUI is an Electron + React app that talks to the backend over HTTP and WebSockets. This README is written for **Raspberry Pi 5** and **Raspberry Pi OS** (64-bit).

---

## What’s in the repo

- **Backend (Python)**  
  - FastAPI app (`app.py`) with CORS, static files, and routers.  
  - **Chat** (`chat_ai.py`): conversation CRUD, WebSocket chat, voice pipeline (STT → LLM → TTS).  
  - **TTS** (`tts_piper.py`): Piper-based speech output.  
  - **STT** (`stt_whisper.py`, `stt_vosk.py`): optional Whisper and Vosk engines.

- **Frontend (Electron + React)**  
  - `chat-gui/`: Vite + React 19, Tailwind, Framer Motion, React Router.  
  - Features: home screen, chat UI with sidebar, settings, WebSocket context for chat and voice.

- **Data**  
  - Conversations: `conversations.json`.  
  - Models: `models/` (LLM, Piper, and optionally Vosk — see [Models](#models-what-downloads-where) below).

---

## Quick start

From the **project root** (the folder that contains `app.py` and `requirements.txt`):

1. **Backend**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env       # optional: edit .env to change port or paths
   python app.py
   ```
2. **Frontend** (in a second terminal; start the backend first)
   ```bash
   cd chat-gui
   npm install
   npm run dev
   ```
3. The Electron window opens and connects to the backend. The **first run** may take several minutes while models download.

---

## Running the app

1. **Start the backend** — from the project root with your venv activated:
   ```bash
   python app.py
   ```
   The server listens on `http://0.0.0.0:8000` (or the port set in `.env`). Leave this terminal running.

2. **Start the GUI** — in a second terminal:
   ```bash
   cd chat-gui
   npm run dev
   ```
   The backend must be running first so the GUI can connect to the API and WebSockets.

3. **Optional:** Copy `.env.example` to `.env` to change `PORT`, paths, or model IDs without editing code.

### One-click desktop launcher (Raspberry Pi OS desktop)

To start the whole app (backend + GUI) from a desktop icon:

1. Copy the desktop entry to your Desktop and make it executable (use your actual project path if different):
   ```bash
   cp /home/pocket-ai/Documents/pocket-ai/scripts/pocket-ai.desktop ~/Desktop/
   chmod +x ~/Desktop/pocket-ai.desktop
   ```
2. If your project is not at `/home/pocket-ai/Documents/pocket-ai`, edit the copied file: set `Exec=` and `Path=` to your project’s path (e.g. `Exec=bash /home/pi/pocket-ai/scripts/start-pocket-ai.sh` and `Path=/home/pi/pocket-ai`).
3. Double-click **Pocket AI** on the Desktop. A terminal will open (with backend logs); the Electron window will open when the backend is ready. When you close the Electron window, the backend stops too.

To run Pocket AI automatically at login, copy the same `.desktop` file to `~/.config/autostart/` instead of `~/Desktop/`.

---

## Prerequisites (Raspberry Pi 5)

| Requirement | Notes |
|-------------|--------|
| **Raspberry Pi 5** | 4 GB or 8 GB RAM; 8 GB recommended for running the LLM plus GUI comfortably. |
| **Raspberry Pi OS (64-bit)** | Bookworm or later. Use the **desktop** image to run the Electron GUI on the Pi; **lite** is fine if you only run the backend and use the GUI from another machine. |
| **Storage** | SD card or (better) SSD. Plan for **at least 4–5 GB free** for models (Qwen GGUF ~500 MB, Piper, Whisper cache, Vosk). |
| **Python 3.10+** | Raspberry Pi OS Bookworm ships with Python 3.11; that’s fine. |
| **Node.js 18+** (and npm) | For building and running the Electron GUI. Install on the Pi (see below). |
| **Microphone** | USB microphone or the Pi’s 3.5 mm jack input (if configured). Needed for voice (STT). |
| **Speaker / USB audio** | For TTS. The code defaults to a USB audio device; see [TTS playback](#other-setup-notes-pi-5-gotchas) below. |


---

## Hailo-8 / Hailo-8L AI HAT setup

This section is for adding a **Hailo-8 or Hailo-8L** AI accelerator (e.g. for computer vision). Follow the official [Hailo Raspberry Pi 5 install guide](https://github.com/hailo-ai/hailo-rpi5-examples/blob/main/doc/install-raspberry-pi5.md); the steps below summarize it.

### What you need (Hailo)

- **Raspberry Pi 5** (8 GB recommended when using Hailo)
- **One of:**
  - **Raspberry Pi 5 AI Kit:** M.2 M-Key HAT + Hailo-8L M.2 module (Hailo-8 also supported). See [Raspberry Pi AI Kit Guide](https://www.raspberrypi.com/documentation/accessories/ai-kit.html#ai-kit).
  - **Raspberry Pi 5 AI HAT:** standalone HAT with Hailo-8L (26 or 13 TOPs). See [Raspberry Pi AI HAT Guide](https://www.raspberrypi.com/documentation/accessories/ai-hat-plus.html#ai-hat-plus).
- **Active cooler** for the Pi 5 (recommended); optional heat sink if the board is in a case.
- **Official 27 W (or adequate) USB-C power supply** so the board can power the HAT.
- Optional: Raspberry Pi camera (e.g. Camera Module 3) or USB camera.

### Install Raspberry Pi OS

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to flash the latest **Raspberry Pi OS (64-bit)** to your SD card or SSD.

### Install the AI Kit or AI HAT (hardware)

- **AI Kit (M.2 HAT):** [Raspberry Pi AI Kit Guide](https://www.raspberrypi.com/documentation/accessories/ai-kit.html#ai-kit) — use the thermal pad between the M.2 module and the HAT.
- **AI HAT:** [Raspberry Pi AI HAT Guide](https://www.raspberrypi.com/documentation/accessories/ai-hat-plus.html#ai-hat-plus).

### Update Raspberry Pi OS

Ensure the Raspberry Pi 5 is running **Raspberry Pi OS Trixie** with the latest software and the latest Raspberry Pi firmware:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo rpi-eeprom-update -a
sudo reboot
```

For more information, see [Update software](https://www.raspberrypi.com/documentation/computers/os.html#update-software) and [Update the bootloader configuration](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#updating-the-eeprom).

### Set PCIe to Gen3

For best performance with the Hailo device, set PCIe to Gen3. (The AI HAT is often auto-detected as Gen3; the M.2 HAT usually needs this set manually.)

```bash
sudo raspi-config
```

Go to **6 Advanced Options** → **A8 PCIe Speed** → choose **Yes** to enable PCIe Gen 3 → **Finish**, then reboot if prompted.

### Install required dependencies

The NPU needs the Hailo kernel device driver and firmware, Hailo RT middleware, and Hailo TAPPAS core post-processing libraries. Install them via apt. **Choose the package that matches your hardware** (these packages cannot co-exist):

- **AI Kit and AI HAT+:** use `hailo-all`
- **AI HAT+ 2:** use `hailo-h10-all`

In the Raspberry Pi Terminal:

```bash
sudo apt install dkms
sudo apt install hailo-all
```

For **AI HAT+ 2** only, use instead:

```bash
sudo apt install dkms
sudo apt install hailo-h10-all
```

### Reboot and verify

After installing the dependencies, reboot:

```bash
sudo reboot
```

When the Raspberry Pi 5 has finished booting, run:

```bash
hailortcli fw-control identify
```

If the NPU and software are installed correctly, you should see output similar to:

```
Executing on device: 0000:01:00.0
Identifying board
Control Protocol Version: 2
Firmware Version: 4.17.0 (release,app,extended context switch buffer)
Logger Version: 0
Board Name: Hailo-8
Device Architecture: HAILO8L
Serial Number: HLDDLBB234500054
Part Number: HM21LB1C2LAE
Product Name: HAILO-8L AI ACC M.2 B+M KEY MODULE EXT TMP
```

**AI HAT+ and AI HAT+ 2** may show `<N/A>` for Serial Number, Part Number, and Product Name. This is expected and does not affect functionality.

You can also check the kernel logs:

```bash
dmesg | grep -i hailo
```

Expected output is similar to:

```
[    3.049657] hailo: Init module. driver version 4.17.0
[    3.051983] hailo 0000:01:00.0: Probing on: 1e60:2864...
[    3.051989] hailo 0000:01:00.0: Probing: Allocate memory for device extension, 11600
[    3.052006] hailo 0000:01:00.0: enabling device (0000 -> 0002)
[    3.052011] hailo 0000:01:00.0: Probing: Device enabled
[    3.052028] hailo 0000:01:00.0: Probing: mapped bar 0 - 000000000d8baaf1 16384
[    3.052034] hailo 0000:01:00.0: Probing: mapped bar 2 - 000000009eeaa33c 4096
[    3.052039] hailo 0000:01:00.0: Probing: mapped bar 4 - 00000000b9b3d17d 16384
[    3.052044] hailo 0000:01:00.0: Probing: Force setting max_desc_page_size to 4096 (recommended value is 16384)
[    3.052052] hailo 0000:01:00.0: Probing: Enabled 64 bit dma
[    3.052055] hailo 0000:01:00.0: Probing: Using userspace allocated vdma buffers
[    3.052059] hailo 0000:01:00.0: Disabling ASPM L0s
[    3.052070] hailo 0000:01:00.0: Successfully disabled ASPM L0s
[    3.221043] hailo 0000:01:00.0: Firmware was loaded successfully
[    3.231845] hailo 0000:01:00.0: Probing: Added board 1e60-2864, /dev/hailo0
```

### Run vision AI models on Raspberry Pi 5

These steps let you run real-time vision AI (e.g. object detection) on camera input using the Hailo NPU. They apply to the AI Kit, AI HAT+, and AI HAT+ 2.

#### Step 1. Install camera dependencies

Install the Raspberry Pi camera stack. The `rpicam-apps` package includes the Hailo post-processing demo stages used for vision AI pipelines:

```bash
sudo apt update && sudo apt install rpicam-apps
```

Verify the camera works (a preview window should appear for a few seconds):

```bash
rpicam-hello
```

#### Step 2. Run real-time visual AI demos

After the camera and Hailo stack are working, you can run AI demos with `rpicam-apps`. The demos use pre-trained networks on the NPU; results can be shown in the live preview or as text in the terminal. Use `-n` to disable the viewfinder and `-v 2` for text-only output.

**Object detection** (YOLO models; bounding boxes around detected objects):

| Model   | Command | Description |
|--------|---------|-------------|
| YOLOv6 | `rpicam-hello -t 0 --post-process-file /usr/share/rpi-camera-assets/hailo_yolov6_inference.json` | Object detection. |
| YOLOv8 | `rpicam-hello -t 0 --post-process-file /usr/share/rpi-camera-assets/hailo_yolov8_inference.json` | Object detection. |
| YOLOX  | `rpicam-hello -t 0 --post-process-file /usr/share/rpi-camera-assets/hailo_yolox_inference.json` | Lightweight, fast object detection. |
| YOLOv5 | `rpicam-hello -t 0 --post-process-file /usr/share/rpi-camera-assets/hailo_yolov5_inference.json` | People and face detection. |

**Image segmentation** (detection + colour mask on the viewfinder):

```bash
rpicam-hello -t 0 --post-process-file /usr/share/rpi-camera-assets/hailo_yolov5_segmentation.json --framerate 20
```

**Pose estimation** (17-point human pose, lines connecting points):

```bash
rpicam-hello -t 0 --post-process-file /usr/share/rpi-camera-assets/hailo_yolov8_pose.json
```

You can use other `rpicam-apps` (e.g. `rpicam-vid`, `rpicam-still`) with the same `--post-process-file` option; some apps may need extra or modified command-line options.

### GStreamer plugins (optional check)

Check that GStreamer plugins are installed:

```bash
gst-inspect-1.0 hailotools
gst-inspect-1.0 hailo
```

If `hailo` or `hailotools` are not found, clear the GStreamer registry and try again:

```bash
rm ~/.cache/gstreamer-1.0/registry.aarch64.bin
gst-inspect-1.0 hailotools
gst-inspect-1.0 hailo
```

If you see a **“cannot allocate memory in static TLS block”** error (common on aarch64), add this and restart the terminal (or reboot):

```bash
echo 'export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libgomp.so.1' >> ~/.bashrc
```

Then:

```bash
export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libgomp.so.1
rm ~/.cache/gstreamer-1.0/registry.aarch64.bin
```

### PCIe / driver troubleshooting

- **PCIe not seen:** Run `lspci | grep Hailo`. If nothing appears, check connections, power, and that PCIe is enabled. New boards may need a [Raspberry Pi 5 firmware update](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#updating-the-eeprom).
- **Driver / kernel:** Hailo expects kernel **≥ 6.6.31**. Check with `uname -a`. If lower, run `sudo apt update` and `sudo apt full-upgrade`, then reboot.
- **PCIe descriptor page size error:** If you see `max_desc_page_size given 16384 is bigger than hw max desc page size 4096`, ensure `/etc/modprobe.d/hailo_pci.conf` exists with:
  ```bash
  options hailo_pci force_desc_page_size=4096
  ```

For more help, see the [Hailo Raspberry Pi 5 install doc](https://github.com/hailo-ai/hailo-rpi5-examples/blob/main/doc/install-raspberry-pi5.md) and the [Hailo Community Forum](https://community.hailo.ai/).

---

## Installing Node.js on Raspberry Pi OS

The Electron GUI needs Node.js and npm. On **Raspberry Pi OS (Debian-based)** use one of these.

**Option A — NodeSource (recommended, Node 20 LTS):**

```bash
sudo apt update
sudo apt install -y curl

curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

node -v   # e.g. v20.x.x
npm -v    # e.g. 10.x.x
```

**Option B — Raspberry Pi OS packages (may be older):**

```bash
sudo apt update
sudo apt install -y nodejs npm
node -v
npm -v
```

If you use a different OS on your Pi 5 (e.g. Ubuntu), the same NodeSource steps usually work.

---

## Backend setup (Raspberry Pi 5, step by step)

Do this on your **Pi 5** from the **project root** (the folder that contains `app.py` and `requirements.txt`).

### 1. System packages (Raspberry Pi OS)

Install dependencies for audio (PyAudio) and Python dev headers:

```bash
sudo apt update
sudo apt install -y portaudio19-dev python3-dev python3-pip python3-venv
```

- **Camera:** If you use a camera module, enable it:  
  `sudo raspi-config` → **Interface Options** → **Camera** → **Enable** → reboot if needed. Connect the camera to the Pi 5’s camera port (small ribbon connector).

### 2. Python virtual environment

```bash
python3 --version   # Should be 3.10+ (e.g. 3.11 on Bookworm)
python3 -m venv .venv
source .venv/bin/activate
```

Your prompt should show `(.venv)`.

**Using the system’s picamera2 from the venv:**  
If you want to use the `picamera2` you installed with apt (recommended on Pi 5), create the venv with system site-packages:

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
```

Then you can leave the `picamera2` line in `requirements.txt` commented out. If you prefer to install `picamera2` inside the venv instead, uncomment that line and run `pip install -r requirements.txt` (may take a while to build on Pi).

### 3. Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

If PyAudio fails to build, ensure you ran step 1 (`portaudio19-dev`). Use the project's `.venv` for all installs so dependency versions match; avoid mixing system and venv packages.

#### Optional: semantic routing

To route prompts to different LLMs (basic / thinking / tool-calling), install the semantic router:
`pip install "semantic-router[local]"`
Without it, the backend falls back to the basic chat model. The first time the router is used it downloads a small embedding model (~67 MB) from Hugging Face and caches it under your project `models/` folder so it only happens once.

### 4. Models: what downloads where

The app uses several models. Most are downloaded automatically; **only Vosk must be downloaded and placed by you.**

| Model | Used for | How you get it |
|-------|----------|-----------------|
| **Qwen3-0.6B (GGUF)** | Chat LLM | **Auto:** first run downloads from Hugging Face into `./models/`. ~400–500 MB. Fits in 4 GB RAM on Pi 5. |
| **Piper (en_US-lessac-medium)** | Text-to-speech | **Auto:** first TTS use downloads into the project’s `models/` folder. |
| **Whisper “tiny”** | Optional STT (push-to-talk) | **Auto:** `faster-whisper` downloads on first use (ARM-friendly). |
| **Vosk (small EN-US)** | Optional STT (live listening) | **Manual** — see below. |

#### Vosk model (manual download)

The code in `stt_vosk.py` expects the Vosk model at a specific path. By default:

`/home/pocket-ai/Documents/pocket-ai/models/vosk/vosk-model-small-en-us-0.15`

On your Pi 5, do this (adjust paths if your project or username differ):

1. **Download a Vosk model** (small model is a good fit for Pi 5):
   - [vosk-model-small-en-us-0.15](https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip) (~40 MB)
   - Or pick another from [Vosk models](https://alphacephei.com/vosk/models).

2. **Unzip and place it** in your project:
   ```bash
   mkdir -p models/vosk
   cd models/vosk
   wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
   unzip vosk-model-small-en-us-0.15.zip
   # You should have:  .../models/vosk/vosk-model-small-en-us-0.15/  with am/, conf/, graph/, etc.
   ```

3. **Set the path in code:**  
   Edit `stt_vosk.py` and set `MODEL_PATH` at the top to the **full path** to that folder on your Pi, e.g.:
   ```python
   MODEL_PATH = "/home/pi/pocket-ai/models/vosk/vosk-model-small-en-us-0.15"
   ```
   Replace `/home/pi/pocket-ai` with your actual project path. If the path is wrong, the backend will print an error on startup.

### 5. Run the backend

```bash
python app.py
```

The server listens on `http://0.0.0.0:8000`. The **first run** can take several minutes while the Qwen model (and optionally Piper/Whisper) download. On Pi 5 this is normal.

---

## Frontend (chat GUI) setup on Pi 5

Open a **second terminal** (or a second SSH session). Start the **backend first** (see above), then:

```bash
cd chat-gui
npm install
npm run dev
```

- **Packaged app:**  
  `npm run build`  
  then run the built app from the output folder (see `chat-gui/package.json`).

- **Start backend from the GUI folder (optional):**  
  From `chat-gui`, `npm run backend` runs `python ../app.py`.

The GUI expects the backend at **port 8000** on the same machine. To use the GUI from another computer, point it at your Pi 5’s IP and port 8000 (you may need to adjust the frontend’s API/WebSocket base URL).

---

## Order of operations (Pi 5 checklist)

1. **Raspberry Pi OS** up to date; **Node.js** and **system packages** installed (NodeSource, `portaudio19-dev`, etc.).  
4. **Backend:**  
   - Clone/open project, create venv.  
   - `pip install -r requirements.txt`.  
   - Download and place the **Vosk** model; set `MODEL_PATH` in `stt_vosk.py`.  
   - Run `python app.py` and wait for first-time model downloads.  
5. **Frontend:**  
   - `cd chat-gui`, `npm install`, `npm run dev`.  
6. Use the app; for voice, ensure a microphone is connected and (for Vosk) `MODEL_PATH` is correct.

---

## Other setup notes (Pi 5 gotchas)

- **Port 8000:** Nothing else should use it. If needed, set `PORT` in `.env` (see `.env.example`) and the frontend’s API config (or VITE_API_PORT in chat-gui).
- **First run is slow:** Qwen (~500 MB), Piper, and Whisper download on first use. Use a stable connection and enough free space (several GB).
- **Microphone on Pi:** Prefer a USB microphone. Ensure your user is in the `audio` group:  
  `groups` (check for `audio`); if missing:  
  `sudo usermod -aG audio $USER`  
  then log out and back in.
- **TTS playback:** `tts_piper.py` uses `aplay -D plughw:3,0`. On the Pi, the “card 3” device is often a **USB sound card**. If you use the Pi’s 3.5 mm jack or a different USB device, list devices with:
  ```bash
  aplay -l
  ```
  Then change the `-D plughw:X,Y` in `tts_piper.py` to match your card (e.g. `plughw:0,0` for the built-in jack, or the correct `hw:x,y` for your USB device).
- **Camera:** If the camera stream fails, check: camera enabled in `raspi-config`, cable seated, and `rpicam-hello` or `python3 -c "from picamera2 import Picamera2; print('ok')"` working.
- **Running headless:** You can run only the backend on the Pi and use the GUI from a laptop/desktop by pointing it at `http://<pi-ip>:8000` (and updating the frontend config if needed).
- **CORS:** The backend allows all origins (`*`); for production you’d restrict this.

---

## Development and performance

- **Dev server with auto-reload:**  
  `uvicorn app:app --reload --host 0.0.0.0 --port 8000`  
  (or set `PORT` in `.env`). Use this during development so the backend restarts when you change Python files.

- **Production:**  
  Run with a single process: `python app.py` or `uvicorn app:app --host 0.0.0.0 --port 8000`. Do not use multiple workers: the app keeps in-memory state (LLM, camera, scheduler). For more throughput you would need to refactor to a stateless design.

- **Startup time:**  
  The first run loads both the chat LLM (Qwen) and the tool-calling model (Function Gemma); this can take a minute. Later requests use the cached models.

---

## Main endpoints (backend)

| Area | Examples |
|------|----------|
| Chat | `GET/POST /conversations`, `GET /conversations/{id}`, `WS /ws/chat/{conv_id}` |
| Voice | `WS /ws/voice` (commands: start_vosk, stop_vosk, toggle_voice, abort) |
| Camera | `POST /camera/start`, `POST /camera/stop`, `GET /video_feed`, `POST /camera/capture` |
| Gallery | `GET /gallery/images`, `DELETE /gallery/images/{filename}` |
| System | `GET /system/stats` |
| Shutdown | `POST /shutdown` |

---

## Project status

This is **v1** of the README, written for **Raspberry Pi 5** and Raspberry Pi OS. The project is **not finished**; features and structure may change. This file will be updated as the project evolves.
