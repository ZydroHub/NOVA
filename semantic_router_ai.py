"""
Semantic router for backend: route a user prompt to one of three models.
- qwen_basic: Qwen 0.6B (non-thinking) for basic conversation
- qwen_thinking: Qwen 0.6B (thinking) for complex/reasoning
- function_gemma: Function Gemma for tool/function calls

Import and call get_route(prompt) from chat_ai for voice and chat flows.

The router uses FastEmbedEncoder, which downloads a small embedding model (~67MB) from
Hugging Face the first time. We cache it under the project models dir so it only downloads once.
"""
import os
import re
import sys
import time
from pathlib import Path

_llm = None

_router = None


def _get_router():
    """Build and cache the semantic router (lazy init)."""
    global _router
    if _router is not None:
        return _router
    try:
        from semantic_router import Route
        from semantic_router.encoders import FastEmbedEncoder
        from semantic_router.routers import SemanticRouter
    except ImportError as e:
        raise ImportError(
            "semantic_router not available. Install: pip install 'semantic-router[fastembed]'"
        ) from e

    # Cache embedding model under project models/ so it only downloads once (not HF default cache)
    try:
        from config import LOCAL_DIR
        embed_cache = os.path.join(LOCAL_DIR, "fastembed_cache")
    except ImportError:
        embed_cache = str(Path(__file__).resolve().parent / "models" / "fastembed_cache")
    os.makedirs(embed_cache, exist_ok=True)
    encoder = FastEmbedEncoder(cache_dir=embed_cache)

    qwen_basic = Route(
        name="qwen_basic",
        utterances=[
            # Greetings and chitchat
            "hi", "hello", "hey there", "how are you", "what's up", "good morning",
            "good night", "thanks!", "thank you", "bye", "see you", "ok", "got it",
            "that's nice", "cool", "sure", "no problem", "how's it going", "nice to meet you",
            # Simple factual / symbol facts — non-thinking
            "what is the largest continent?", "what is the capital of the United States?",
            "what is the capital of France?", "how many continents are there?",
            "what is two plus two?", "who wrote Romeo and Juliet?",
            "what is the speed of light?", "what year did World War II end?",
            "what is the largest ocean?", "name the planets in our solar system",
            "what is the capital of Japan?", "how many days in a week?",
            "what is the biggest country by area?", "simple facts", "give me a quick fact",
            "what's the population of China?", "who is the president of the US?",
        ],
    )
    qwen_thinking = Route(
        name="qwen_thinking",
        utterances=[
            "why does this happen?", "explain the reasoning behind it",
            "what are the steps to solve this?", "compare X and Y", "analyze this situation",
            "what are the pros and cons?", "how would you approach this problem?",
            "walk me through the logic", "what's the cause of this?",
            "give me a detailed explanation", "what are the implications?",
            "summarize the main points", "how do these relate?",
            "what's the difference between A and B?",
        ],
    )
    function_gemma = Route(
        name="function_gemma",
        utterances=[
            "what is the weather like in New York?", "weather in London",
            "search the web for latest news", "search for AI news",
            "scan my local network", "scan the network",
            "what is the stock price of TSLA?", "current price of AAPL",
            "get weather for Boston", "web search for something",
        ],
    )
    _router = SemanticRouter(encoder=encoder, routes=[qwen_basic, qwen_thinking, function_gemma], auto_sync="local")
    return _router


def get_route(prompt: str) -> str:
    """
    Route a user prompt to a model. Returns one of:
    "qwen_basic", "qwen_thinking", "function_gemma".
    Defaults to "qwen_basic" if no route matches or on error.
    """
    if not (prompt or "").strip():
        return "qwen_basic"
    try:
        router = _get_router()
        choice = router(prompt)
        name = choice.name if choice else None
        return name if name in ("qwen_basic", "qwen_thinking", "function_gemma") else "qwen_basic"
    except Exception as e:
        print(f"[semantic_router_ai] route failed: {e}")
        return "qwen_basic"


def _strip_think(text: str) -> str:
    """Remove <think>...</think> blocks for display."""
    if not text or not text.strip():
        return text
    out = re.sub(r'<\s*think\s*>.*?<\s*/\s*think\s*>', '', text, flags=re.DOTALL | re.IGNORECASE)
    out = re.sub(r'<\s*think\s*>[\s\S]*$', '', out, flags=re.IGNORECASE)
    out = out.replace('</think>', '').replace('<think>', '')
    return out.strip()


def _get_llm():
    """Load and cache the Qwen LLM (same config as chat_ai)."""
    global _llm
    if _llm is not None:
        return _llm
    try:
        from config import LOCAL_DIR, CHAT_REPO_ID as REPO_ID, CHAT_FILENAME as FILENAME, CHAT_MODEL_PATH as MODEL_PATH
        from huggingface_hub import hf_hub_download
        from llama_cpp import Llama
    except ImportError as e:
        raise ImportError("Need config, huggingface_hub, llama_cpp for REPL Qwen. Install: pip install llama-cpp-python huggingface-hub") from e
    if not os.path.exists(MODEL_PATH):
        print("Downloading Qwen model...")
        os.makedirs(LOCAL_DIR, exist_ok=True)
        hf_hub_download(repo_id=REPO_ID, filename=FILENAME, local_dir=LOCAL_DIR)
    print("Loading Qwen LLM...")
    _llm = Llama(model_path=MODEL_PATH, n_ctx=4096, n_threads=4, verbose=False)
    return _llm


def _generate_sync(prompt: str, thinking: bool) -> str:
    """Run Qwen on one user message; returns full raw response."""
    llm = _get_llm()
    user_content = prompt + (" /think" if thinking else " /no_think")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": user_content},
    ]
    temp = 0.6 if thinking else 0.7
    top_p = 0.95 if thinking else 0.8
    stream = llm.create_chat_completion(
        messages=messages,
        max_tokens=2048,
        temperature=temp,
        top_p=top_p,
        top_k=20,
        min_p=0.0,
        presence_penalty=1.5,
        stream=True,
    )
    full = ""
    for chunk in stream:
        if chunk.get("choices") and len(chunk["choices"]) > 0:
            delta = chunk["choices"][0].get("delta", {})
            if "content" in delta:
                content = delta["content"]
                full += content
                print(content, end="", flush=True)
    print()  # newline after stream
    return full


# --- REPL for manual testing ---
def main():
    print("Loading router...")
    get_route("warmup")  # force init
    print("Loading Qwen 3...")
    _get_llm()
    print("Semantic router ready. Type a prompt (empty to quit). Qwen thinking/non-thinking only; function_gemma skipped.\n")
    while True:
        try:
            prompt = input("Prompt> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not prompt:
            break
        t0 = time.perf_counter()
        r = get_route(prompt)
        route_ms = (time.perf_counter() - t0) * 1000
        print(f"  -> {r}  (routing: {route_ms:.1f} ms)")
        if r == "function_gemma":
            print("  (function_gemma skipped)\n")
            continue
        # Send to Qwen (thinking or non-thinking)
        gen_t0 = time.perf_counter()
        _generate_sync(prompt, thinking=(r == "qwen_thinking"))
        gen_ms = (time.perf_counter() - gen_t0) * 1000
        print(f"  (generation: {gen_ms:.0f} ms)\n")
    print("Bye.")


if __name__ == "__main__":
    main()
