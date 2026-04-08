#!/usr/bin/env bash
# Start Pocket AI: backend (FastAPI) then Electron GUI.
# When you close the GUI, the backend is stopped too.

# When run from desktop, PATH may not include node/npm — load your shell profile
if [ -f "$HOME/.profile" ]; then
    source "$HOME/.profile"
fi
if [ -f "$HOME/.bashrc" ]; then
    source "$HOME/.bashrc"
fi

# Still no npm? Add common locations and try nvm
if ! command -v npm &>/dev/null; then
    export PATH="/usr/local/bin:/usr/bin:$HOME/.local/bin:$PATH"
    # NVM (Node Version Manager)
    if [ -s "$HOME/.nvm/nvm.sh" ]; then
        source "$HOME/.nvm/nvm.sh"
    fi
    # NVM puts node in versions/node/*/bin
    for nvm_dir in "$HOME/.nvm/versions/node"/*/bin; do
        [ -d "$nvm_dir" ] && PATH="$nvm_dir:$PATH"
    done
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Pocket AI launcher ==="
echo "Project: $PROJECT_ROOT"

# Create and activate venv if needed
if [ ! -f ".venv/bin/activate" ]; then
    echo "Creating Python venv (.venv)..."
    python3 -m venv .venv || {
        echo "ERROR: Could not create .venv. Ensure python3-venv is installed."
        exit 1
    }
fi

echo "Activating Python venv..."
source .venv/bin/activate

# If llama_cpp is missing, make sure local build tools exist before pip install.
# llama-cpp-python often requires compiling from source on Linux.
if ! python -c "import llama_cpp" >/dev/null 2>&1; then
    MISSING_TOOLS=()
    for tool in ninja cmake gcc g++; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            MISSING_TOOLS+=("$tool")
        fi
    done

    if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
        echo "ERROR: Missing system build tools: ${MISSING_TOOLS[*]}"
        echo "Install them, then rerun launcher:"
        echo "  sudo apt update && sudo apt install -y ninja-build cmake build-essential python3-dev"
        exit 1
    fi
fi

# Ensure required Python dependencies are installed
if ! python -c "import fastapi, psutil, uvicorn, llama_cpp" >/dev/null 2>&1; then
    echo "Installing Python dependencies..."
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt || {
        echo "ERROR: Failed to install Python dependencies from requirements.txt"
        exit 1
    }
fi

# Start backend in background
echo "Starting backend..."
python app.py &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend (up to 30s)..."
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do
    if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health 2>/dev/null | grep -q 200; then
        echo "Backend is ready."
        break
    fi
    sleep 1
done

# Start Electron GUI
cd "$PROJECT_ROOT/chat-gui"
if ! command -v npm &>/dev/null; then
    echo ""
    echo "ERROR: npm not found. Add Node/npm to your PATH or run this script from a terminal."
    echo "Backend is still running (PID $BACKEND_PID). Close this window to stop it, or run: kill $BACKEND_PID"
    echo "Press Enter to close..."
    read -r
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

echo "Starting Pocket AI window..."
if [ -f "out/main/index.js" ]; then
    npx electron . 2>/dev/null || npm run dev
else
    npm run dev
fi
GUI_EXIT=$?

# When GUI exits, stop the backend
echo "Stopping backend..."
kill $BACKEND_PID 2>/dev/null || true
exit $GUI_EXIT
