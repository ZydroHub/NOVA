"""
Task / tool-running agent: prompt Gemma, parse tool call, run tools (stub prints),
then create a chat (conversation) with the tool call response.
Uses the same response flow as test_gemma.py (streaming, first_function_call_only).
"""
import argparse
import json
import os
import re
import time

from huggingface_hub import hf_hub_download
from llama_cpp import Llama

# 1. Model configuration
REPO_ID = "nlouis/functiongemma-pocket-q4_k_m"
FILENAME = "functiongemma-pocket-q4_k_m.gguf"
LOCAL_DIR = "./models"
MODEL_PATH = os.path.join(LOCAL_DIR, FILENAME)
TOOLS_PATH = "tools.json"

# 2. Auto-download if not already in models/
if not os.path.exists(MODEL_PATH):
    print(f"Model not found at {MODEL_PATH}. Downloading from Hugging Face...")
    os.makedirs(LOCAL_DIR, exist_ok=True)
    MODEL_PATH = hf_hub_download(
        repo_id=REPO_ID,
        filename=FILENAME,
        local_dir=LOCAL_DIR,
    )
    print("Download complete!")

# 3. Performance settings (aligned with test_gemma.py)
PERF = {
    "n_ctx": 2048,
    "n_threads": 4,
    "n_threads_batch": 4,
    "n_batch": 512,
    "n_gpu_layers": -1,
    "use_mmap": True,
    "use_mlock": False,
    "verbose": False,
}
GEN_PERF = {
    "max_tokens": 128,
    "temperature": 0.1,
}


def first_function_call_only(text: str) -> str:
    """Keep only the first function call; normalize so it always ends with <end_function_call>."""
    end_marker = "<end_function_call>"
    idx = text.find(end_marker)
    if idx != -1:
        return text[: idx + len(end_marker)]
    if "<start_function_call>" in text and text.strip().endswith("}"):
        return text.rstrip() + "<end_function_call>"
    return text


def parse_function_call(raw_call: str):
    """
    Extract tool name and arguments from model output between <start_function_call> and <end_function_call>.
    Returns (name, arguments dict) or (None, None) if parsing fails.
    """
    start_marker = "<start_function_call>"
    end_marker = "<end_function_call>"
    i = raw_call.find(start_marker)
    j = raw_call.find(end_marker)
    if i == -1 or j == -1 or j <= i:
        return None, None
    payload = raw_call[i + len(start_marker) : j].strip()
    try:
        data = json.loads(payload)
        name = data.get("name")
        args = data.get("arguments")
        if isinstance(args, str):
            args = json.loads(args) if args.strip() else {}
        if not name:
            return None, None
        return name, args or {}
    except (json.JSONDecodeError, TypeError):
        return None, None


# --- Boilerplate tool implementations (print only) ---
def run_get_weather(arguments: dict) -> str:
    location = arguments.get("location", "unknown")
    print(f"[tool] get_weather(location={location})")
    return f"Weather for {location}: (stub — no data)"


def run_activate_security_mode(arguments: dict) -> str:
    print("[tool] activate_security_mode()")
    return "Security mode activated (stub)"


def run_web_search(arguments: dict) -> str:
    query = arguments.get("query", "")
    print(f"[tool] web_search(query={query})")
    return f"Search results for '{query}' (stub)"


def run_network_scan(arguments: dict) -> str:
    print("[tool] network_scan()")
    return "Network scan complete (stub)"


def run_get_stock_price(arguments: dict) -> str:
    symbol = arguments.get("symbol", "")
    print(f"[tool] get_stock_price(symbol={symbol})")
    return f"Stock price for {symbol}: (stub)"


TOOL_RUNNERS = {
    "get_weather": run_get_weather,
    "activate_security_mode": run_activate_security_mode,
    "web_search": run_web_search,
    "network_scan": run_network_scan,
    "get_stock_price": run_get_stock_price,
}


def run_tool(name: str, arguments: dict) -> str:
    runner = TOOL_RUNNERS.get(name)
    if not runner:
        print(f"[tool] unknown tool: {name}({arguments})")
        return f"Unknown tool: {name}"
    return runner(arguments)


# Cached model and tools for run_task_for_backend (lazy load)
_llm_cache = None
_chat_tools_cache = None


def _get_llm_and_tools():
    """Load Gemma and tools once; cache for run_task_for_backend."""
    global _llm_cache, _chat_tools_cache
    if _llm_cache is not None and _chat_tools_cache is not None:
        return _llm_cache, _chat_tools_cache
    if not os.path.exists(TOOLS_PATH):
        raise FileNotFoundError(f"Tools file not found: {TOOLS_PATH}")
    with open(TOOLS_PATH, "r") as f:
        tools = json.load(f)
    _chat_tools_cache = [{"type": "function", "function": t} for t in tools]
    model_path = MODEL_PATH
    if not os.path.exists(model_path):
        print(f"Model not found at {model_path}. Downloading...")
        os.makedirs(LOCAL_DIR, exist_ok=True)
        model_path = hf_hub_download(repo_id=REPO_ID, filename=FILENAME, local_dir=LOCAL_DIR)
    print(f"[tool_ai] Loading FunctionGemma: {model_path}")
    _llm_cache = Llama(
        model_path=model_path,
        n_ctx=PERF["n_ctx"],
        n_threads=PERF["n_threads"],
        n_threads_batch=PERF["n_threads_batch"],
        n_batch=PERF["n_batch"],
        n_gpu_layers=PERF["n_gpu_layers"],
        use_mmap=PERF["use_mmap"],
        use_mlock=PERF["use_mlock"],
        verbose=PERF["verbose"],
    )
    return _llm_cache, _chat_tools_cache


def run_task_for_backend(prompt: str) -> tuple:
    """
    Run tool_ai for a single user prompt from chat_ai (voice or chat).
    Loads model/tools on first call. Tools print to terminal.
    Returns (tool_call_raw_or_none, tool_result_or_none).
    If no tool call, returns (None, None).
    """
    llm, chat_tools = _get_llm_and_tools()
    return run_task(llm, chat_tools, prompt)


def run_task(llm, chat_tools, user_prompt: str):
    """
    Run one turn: user prompt -> Gemma (with tools) -> first tool call -> execute tool.
    Returns (tool_call_raw, tool_result) for building the chat. If no tool call, returns (None, None).
    """
    messages = [
        {"role": "developer", "content": "You are a model that can do function calling with the provided functions."},
        {"role": "user", "content": user_prompt},
    ]

    stream = llm.create_chat_completion(
        messages=messages,
        tools=chat_tools,
        max_tokens=GEN_PERF["max_tokens"],
        temperature=GEN_PERF["temperature"],
        stop=["<end_function_call>", "<eos>"],
        stream=True,
    )
    content_parts = []
    for chunk in stream:
        choice = chunk.get("choices", [{}])[0]
        delta = choice.get("delta", {})
        text = delta.get("content") or ""
        if text:
            content_parts.append(text)

    raw = "".join(content_parts)
    tool_call_raw = first_function_call_only(raw)
    if "<start_function_call>" not in tool_call_raw:
        print("Model did not produce a tool call.")
        return None, None

    name, arguments = parse_function_call(tool_call_raw)
    if not name:
        print("Could not parse tool call from model output.")
        return tool_call_raw, None

    print(f"Tool call: {name}({arguments})")
    result = run_tool(name, arguments)
    return tool_call_raw, result


def create_chat_via_api(title: str, messages: list, api_base: str = "http://127.0.0.1:8000"):
    """Create a conversation with the given messages via the backend API."""
    try:
        import urllib.request
        payload = json.dumps({"title": title, "messages": messages}).encode("utf-8")
        req = urllib.request.Request(
            f"{api_base}/conversations",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data
    except Exception as e:
        print(f"Failed to create conversation via API: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Run Gemma with tools; create a chat with the tool call response.")
    parser.add_argument("prompt", nargs="?", help="User prompt (e.g. task message)")
    parser.add_argument("--no-create-chat", action="store_true", help="Do not POST to create a conversation")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000", help="Backend API base URL")
    args = parser.parse_args()

    prompt = args.prompt
    if not prompt:
        prompt = input("Prompt (task message): ").strip()
    if not prompt:
        print("No prompt provided.")
        return 1

    # Load tools (same as test_gemma.py)
    if not os.path.exists(TOOLS_PATH):
        print(f"Error: Tools file not found at {TOOLS_PATH}")
        return 1
    with open(TOOLS_PATH, "r") as f:
        tools = json.load(f)
    chat_tools = [{"type": "function", "function": t} for t in tools]

    # Load model
    print(f"Loading FunctionGemma model: {MODEL_PATH}...")
    llm = Llama(
        model_path=MODEL_PATH,
        n_ctx=PERF["n_ctx"],
        n_threads=PERF["n_threads"],
        n_threads_batch=PERF["n_threads_batch"],
        n_batch=PERF["n_batch"],
        n_gpu_layers=PERF["n_gpu_layers"],
        use_mmap=PERF["use_mmap"],
        use_mlock=PERF["use_mlock"],
        verbose=PERF["verbose"],
    )

    # Run task: prompt -> model -> tool call -> run tool
    tool_call_raw, tool_result = run_task(llm, chat_tools, prompt)

    # Build chat messages (role + content only; backend can add timestamp if needed)
    chat_messages = [
        {"role": "user", "content": prompt},
    ]
    if tool_call_raw:
        chat_messages.append({"role": "assistant", "content": tool_call_raw})
    if tool_result is not None:
        chat_messages.append({"role": "assistant", "content": f"[Tool result] {tool_result}"})

    if not args.no_create_chat and chat_messages:
        title = (prompt[:30] + "…") if len(prompt) > 30 else prompt
        conv = create_chat_via_api(title, chat_messages, api_base=args.api_base)
        if conv:
            print(f"Created conversation: {conv.get('id')} — {conv.get('title', '')}")
        else:
            print("Chat messages (API create skipped or failed):")
            for m in chat_messages:
                print(f"  {m['role']}: {m['content'][:80]}…" if len(m["content"]) > 80 else f"  {m['role']}: {m['content']}")
    else:
        print("Chat messages:")
        for m in chat_messages:
            print(f"  {m['role']}: {m['content'][:80]}…" if len(m["content"]) > 80 else f"  {m['role']}: {m['content']}")

    return 0


if __name__ == "__main__":
    exit(main())
