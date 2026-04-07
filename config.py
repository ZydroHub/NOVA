"""
Central configuration for Pocket AI backend.
Reads from environment (and optional .env file) with sensible defaults.
"""
import logging
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Server
PORT = int(os.environ.get("PORT", "8000"))

# Paths (relative to project root)
CONVERSATIONS_FILE = os.environ.get("CONVERSATIONS_FILE", "conversations.json")
TOOLS_PATH = os.environ.get("TOOLS_PATH", "tools.json")
JOBS_FILE = os.environ.get("JOBS_FILE", "task_jobs.json")
LOCAL_DIR = os.environ.get("LOCAL_DIR", "./models")

# Chat LLM (Qwen)
CHAT_REPO_ID = os.environ.get("CHAT_REPO_ID", "Qwen/Qwen3-0.6B-GGUF")
CHAT_FILENAME = os.environ.get("CHAT_FILENAME", "Qwen3-0.6B-Q8_0.gguf")
CHAT_MODEL_PATH = os.path.join(LOCAL_DIR, CHAT_FILENAME)

# Tool LLM (Function Gemma)
TOOL_REPO_ID = os.environ.get("TOOL_REPO_ID", "nlouis/functiongemma-pocket-q4_k_m")
TOOL_FILENAME = os.environ.get("TOOL_FILENAME", "functiongemma-pocket-q4_k_m.gguf")
TOOL_MODEL_PATH = os.path.join(LOCAL_DIR, TOOL_FILENAME)

# Logging (optional)
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FILE = os.environ.get("LOG_FILE", "")


def setup_logging() -> None:
    """Configure root logger with LOG_LEVEL and optional LOG_FILE. Call once at app startup."""
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root = logging.getLogger()
    if LOG_FILE:
        try:
            fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
            fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
            root.addHandler(fh)
        except OSError:
            root.warning("Could not open log file %s", LOG_FILE)
