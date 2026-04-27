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
PORT = int(os.getenv("PORT", "8000"))

# Paths (relative to project root)
CONVERSATIONS_FILE = os.getenv("CONVERSATIONS_FILE", "conversations.json")
TOOLS_PATH = os.getenv("TOOLS_PATH", "tools.json")
JOBS_FILE = os.getenv("JOBS_FILE", "task_jobs.json")
LOCAL_DIR = os.getenv("LOCAL_DIR", "./models")

# Chat LLM (Qwen)
CHAT_REPO_ID = os.getenv("CHAT_REPO_ID", "Qwen/Qwen3-0.6B-GGUF")
CHAT_FILENAME = os.getenv("CHAT_FILENAME", "Qwen3-0.6B-Q8_0.gguf")
CHAT_MODEL_PATH = os.path.join(LOCAL_DIR, CHAT_FILENAME)

# Tool LLM (Function Gemma)
TOOL_REPO_ID = os.getenv("TOOL_REPO_ID", "nlouis/functiongemma-pocket-q4_k_m")
TOOL_FILENAME = os.getenv("TOOL_FILENAME", "functiongemma-pocket-q4_k_m.gguf")
TOOL_MODEL_PATH = os.path.join(LOCAL_DIR, TOOL_FILENAME)

# Telegram bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_SUBSCRIPTIONS_FILE = os.getenv("TELEGRAM_SUBSCRIPTIONS_FILE", "telegram_subscriptions.json")
TELEGRAM_POLL_INTERVAL_SECONDS = int(os.getenv("TELEGRAM_POLL_INTERVAL_SECONDS", "60"))
TELEGRAM_REQUEST_TIMEOUT_SECONDS = int(os.getenv("TELEGRAM_REQUEST_TIMEOUT_SECONDS", "10"))
TELEGRAM_MAX_RETRIES = int(os.getenv("TELEGRAM_MAX_RETRIES", "3"))

# Logging (optional)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "")


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
