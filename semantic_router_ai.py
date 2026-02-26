"""
Semantic router for backend: route a user prompt to one of three models.
- qwen_basic: Qwen 0.6B (non-thinking) for basic conversation
- qwen_thinking: Qwen 0.6B (thinking) for complex/reasoning
- function_gemma: Function Gemma for tool/function calls

Import and call get_route(prompt) from chat_ai for voice and chat flows.
"""
import sys

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

    qwen_basic = Route(
        name="qwen_basic",
        utterances=[
            "hi", "hello", "hey there", "how are you", "what's up", "good morning",
            "good night", "thanks!", "thank you", "bye", "see you", "ok", "got it",
            "that's nice", "cool", "sure", "no problem", "how's it going", "nice to meet you",
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
            "turn on the security cameras", "activate security mode",
            "search the web for latest news", "search for AI news",
            "scan my local network", "scan the network",
            "what is the stock price of TSLA?", "current price of AAPL",
            "get weather for Boston", "enable PIR sensors", "web search for something",
        ],
    )
    encoder = FastEmbedEncoder()
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


# --- REPL for manual testing ---
def main():
    print("Loading router...")
    get_route("warmup")  # force init
    print("Semantic router ready. Type a prompt (empty to quit).\n")
    while True:
        try:
            prompt = input("Prompt> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not prompt:
            break
        r = get_route(prompt)
        print(f"  -> {r}\n")
    print("Bye.")


if __name__ == "__main__":
    main()
