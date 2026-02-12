#!/usr/bin/env python3
"""
OpenClaw Python Client
──────────────────────
Interactive chat client for the OpenClaw gateway via WebSocket.

Usage:
    python3 openclaw_client.py              # interactive chat
    python3 openclaw_client.py --session mykey  # use a specific session key
    python3 openclaw_client.py --url ws://host:port --token TOKEN

Requires: pip install websockets
"""

import asyncio
import json
import os
import sys
import uuid
import signal
from pathlib import Path

try:
    import websockets
except ImportError:
    print("Error: 'websockets' package is required.")
    print("Install it with:  pip install websockets")
    sys.exit(1)


# ─── Configuration ───────────────────────────────────────────────────────────

PROTOCOL_VERSION = 3
DEFAULT_SESSION_KEY = "agent:main:main"
HISTORY_LIMIT = 50


def load_openclaw_config():
    """Load gateway URL and token from ~/.openclaw/openclaw.json."""
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        return {}, None, None

    with open(config_path) as f:
        config = json.load(f)

    gw = config.get("gateway", {})
    port = gw.get("port", 18789)
    url = f"ws://127.0.0.1:{port}"

    auth = gw.get("auth", {})
    token = auth.get("token")
    if not token:
        token = os.environ.get("OPENCLAW_GATEWAY_TOKEN")

    return config, url, token


# ─── Gateway Client ──────────────────────────────────────────────────────────

class OpenClawClient:
    """Async WebSocket client for the OpenClaw gateway."""

    def __init__(self, url: str, token: str = None, session_key: str = DEFAULT_SESSION_KEY):
        self.url = url
        self.token = token
        self.session_key = session_key
        self.ws = None
        self.connected = False
        self._pending = {}          # id -> Future
        self._event_handlers = {}   # event name -> callback
        self._recv_task = None
        self._req_counter = 0
        self._current_run_id = None

    # ── Connection ────────────────────────────────────────────────────────

    async def connect(self):
        """Connect to the gateway and complete the handshake."""
        self._challenge_received = asyncio.Event()

        self.ws = await websockets.connect(
            self.url,
            max_size=10 * 1024 * 1024,  # 10 MB
            ping_interval=20,
            ping_timeout=30,
        )

        # Start background receiver
        self._recv_task = asyncio.create_task(self._receive_loop())

        # Wait for the connect.challenge event (or timeout after 1s)
        try:
            await asyncio.wait_for(self._challenge_received.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pass  # proceed without challenge (some gateways skip it)

        # Now send the connect handshake
        await self._do_handshake()

    async def _do_handshake(self):
        """Send the connect request and wait for hello-ok."""
        connect_params = {
            "minProtocol": PROTOCOL_VERSION,
            "maxProtocol": PROTOCOL_VERSION,
            "client": {
                "id": "gateway-client",
                "displayName": "Python OpenClaw Client",
                "version": "1.0.0",
                "platform": sys.platform,
                "mode": "cli",
            },
            "role": "operator",
            "scopes": ["operator.read", "operator.write"],
            "caps": [],
            "auth": {"token": self.token} if self.token else {},
        }

        result = await self.request("connect", connect_params)
        if result and result.get("type") == "hello-ok":
            self.connected = True
        else:
            self.connected = True  # still usable even if shape differs

    async def disconnect(self):
        """Cleanly close the connection."""
        self.connected = False
        if self._recv_task:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass
        if self.ws:
            await self.ws.close()

    # ── Low-level messaging ───────────────────────────────────────────────

    def _next_id(self):
        self._req_counter += 1
        return f"py-{self._req_counter}"

    async def request(self, method: str, params=None, timeout: float = 30.0):
        """Send a request and wait for the response."""
        req_id = self._next_id()
        frame = {
            "type": "req",
            "id": req_id,
            "method": method,
        }
        if params is not None:
            frame["params"] = params

        future = asyncio.get_event_loop().create_future()
        self._pending[req_id] = future

        await self.ws.send(json.dumps(frame))

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise TimeoutError(f"Request '{method}' timed out after {timeout}s")

    async def _receive_loop(self):
        """Background loop that dispatches incoming messages."""
        try:
            async for raw in self.ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type")

                if msg_type == "res":
                    req_id = msg.get("id")
                    future = self._pending.pop(req_id, None)
                    if future and not future.done():
                        if msg.get("ok"):
                            future.set_result(msg.get("payload"))
                        else:
                            err = msg.get("error", {})
                            future.set_exception(
                                RuntimeError(err.get("message", "Request failed"))
                            )

                elif msg_type == "event":
                    event_name = msg.get("event", "")

                    # Signal the challenge so the handshake can proceed
                    if event_name == "connect.challenge":
                        self._challenge_received.set()
                        continue

                    handler = self._event_handlers.get(event_name)
                    if handler:
                        try:
                            handler(msg.get("payload", {}))
                        except Exception as e:
                            print(f"\n[event handler error: {e}]", file=sys.stderr)

        except websockets.ConnectionClosed:
            self.connected = False
        except asyncio.CancelledError:
            pass

    def on_event(self, event_name: str, handler):
        """Register an event handler."""
        self._event_handlers[event_name] = handler

    # ── Chat methods ──────────────────────────────────────────────────────

    async def chat_send(self, message: str, thinking: str = None) -> str:
        """
        Send a chat message. Returns the runId.
        The response streams back via 'chat' events.
        """
        run_id = str(uuid.uuid4())
        self._current_run_id = run_id

        params = {
            "sessionKey": self.session_key,
            "message": message,
            "idempotencyKey": run_id,
            "deliver": False,
        }
        if thinking:
            params["thinking"] = thinking

        await self.request("chat.send", params, timeout=600)
        return run_id

    async def chat_abort(self, run_id: str = None):
        """Abort the current chat run."""
        params = {"sessionKey": self.session_key}
        if run_id:
            params["runId"] = run_id
        try:
            await self.request("chat.abort", params, timeout=10)
        except Exception:
            pass  # best-effort

    async def chat_history(self, limit: int = HISTORY_LIMIT):
        """Load recent chat history."""
        result = await self.request("chat.history", {
            "sessionKey": self.session_key,
            "limit": limit,
        })
        return result

    async def session_reset(self):
        """Reset the current session."""
        await self.request("sessions.reset", {"key": self.session_key})


# ─── Interactive Chat ─────────────────────────────────────────────────────────

class ChatSession:
    """Interactive chat REPL using the OpenClaw gateway."""

    COLORS = {
        "reset":   "\033[0m",
        "bold":    "\033[1m",
        "dim":     "\033[2m",
        "red":     "\033[31m",
        "green":   "\033[32m",
        "yellow":  "\033[33m",
        "blue":    "\033[34m",
        "magenta": "\033[35m",
        "cyan":    "\033[36m",
    }

    def __init__(self, client: OpenClawClient):
        self.client = client
        self._stream_text = ""
        self._stream_done = asyncio.Event()
        self._streaming = False
        self._aborted = False

    def _c(self, color: str, text: str) -> str:
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"

    def _print_banner(self):
        print()
        print(self._c("cyan", "╔══════════════════════════════════════════╗"))
        print(self._c("cyan", "║") + self._c("bold", "    🦞 OpenClaw Python Client             ") + self._c("cyan", "║"))
        print(self._c("cyan", "╠══════════════════════════════════════════╣"))
        print(self._c("cyan", "║") + f"  Gateway: {self.client.url:<30}" + self._c("cyan", "║"))
        print(self._c("cyan", "║") + f"  Session: {self.client.session_key:<30}" + self._c("cyan", "║"))
        print(self._c("cyan", "╠══════════════════════════════════════════╣"))
        print(self._c("cyan", "║") + self._c("dim", "  /new    — reset session                 ") + self._c("cyan", "║"))
        print(self._c("cyan", "║") + self._c("dim", "  /quit   — exit                          ") + self._c("cyan", "║"))
        print(self._c("cyan", "║") + self._c("dim", "  Ctrl+C  — abort current response         ") + self._c("cyan", "║"))
        print(self._c("cyan", "╚══════════════════════════════════════════╝"))
        print()

    def _handle_chat_event(self, payload):
        """Handle incoming 'chat' events from the gateway."""
        session_key = payload.get("sessionKey")
        if session_key != self.client.session_key:
            return

        state = payload.get("state")
        run_id = payload.get("runId")

        # Only process events for our current run
        if run_id and self.client._current_run_id and run_id != self.client._current_run_id:
            return

        if state == "delta":
            message = payload.get("message", {})
            content = message.get("content", [])
            full_text = ""
            for block in content:
                if block.get("type") == "text":
                    full_text = block.get("text", "")

            # Print incremental delta
            if len(full_text) > len(self._stream_text):
                new_text = full_text[len(self._stream_text):]
                print(new_text, end="", flush=True)
                self._stream_text = full_text

        elif state == "final":
            # Finalize — load fresh from the final message if available
            message = payload.get("message", {})
            content = message.get("content", [])
            final_text = ""
            for block in content:
                if block.get("type") == "text":
                    final_text = block.get("text", "")

            if final_text and len(final_text) > len(self._stream_text):
                remaining = final_text[len(self._stream_text):]
                print(remaining, end="", flush=True)

            print()  # newline after response
            self._stream_done.set()

        elif state == "aborted":
            print(self._c("yellow", "\n[aborted]"))
            self._aborted = True
            self._stream_done.set()

        elif state == "error":
            error_msg = payload.get("errorMessage", "unknown error")
            print(self._c("red", f"\n[error: {error_msg}]"))
            self._stream_done.set()

    def _display_history(self, history_data):
        """Display chat history on connect."""
        messages = history_data.get("messages", [])
        if not messages:
            return

        print(self._c("dim", f"── Recent history ({len(messages)} messages) ──"))
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", [])

            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)

            text = "\n".join(text_parts).strip()
            if not text:
                continue

            # Truncate long history messages
            if len(text) > 200:
                text = text[:200] + "…"

            if role == "user":
                print(f"{self._c('green', 'You')}: {text}")
            elif role == "assistant":
                print(f"{self._c('magenta', 'AI')}: {text}")

        print(self._c("dim", "── End of history ──"))
        print()

    async def run(self):
        """Main interactive loop."""
        # Register event handler
        self.client.on_event("chat", self._handle_chat_event)

        self._print_banner()

        # Load and display history
        try:
            history = await self.client.chat_history()
            self._display_history(history)
        except Exception as e:
            print(self._c("dim", f"(could not load history: {e})"))

        print(self._c("green", "Ready. Type a message and press Enter.\n"))

        while True:
            try:
                # Get user input
                try:
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: input(self._c("green", "You: "))
                    )
                except EOFError:
                    print(self._c("dim", "\nGoodbye!"))
                    break

                user_input = user_input.strip()
                if not user_input:
                    continue

                # Handle slash commands
                lower = user_input.lower()
                if lower in ("/quit", "/exit", "exit", "quit"):
                    print(self._c("dim", "Goodbye!"))
                    break

                if lower in ("/new", "/reset"):
                    try:
                        await self.client.session_reset()
                        print(self._c("cyan", "Session reset. Starting fresh.\n"))
                    except Exception as e:
                        print(self._c("red", f"Failed to reset: {e}"))
                    continue

                if lower == "/help":
                    self._print_banner()
                    continue

                if lower.startswith("/session "):
                    new_key = user_input[9:].strip()
                    if new_key:
                        self.client.session_key = new_key
                        print(self._c("cyan", f"Switched to session: {new_key}\n"))
                    continue

                # Send message
                self._stream_text = ""
                self._stream_done.clear()
                self._streaming = True
                self._aborted = False

                print(self._c("magenta", "AI: "), end="", flush=True)

                run_id = await self.client.chat_send(user_input)

                # Wait for streaming to complete (with abort support)
                try:
                    await self._stream_done.wait()
                except asyncio.CancelledError:
                    pass

                self._streaming = False
                self.client._current_run_id = None
                print()  # extra blank line between exchanges

            except KeyboardInterrupt:
                if self._streaming and self.client._current_run_id:
                    print(self._c("yellow", "\n[aborting...]"), flush=True)
                    await self.client.chat_abort(self.client._current_run_id)
                    self._streaming = False
                    self.client._current_run_id = None
                    # Wait briefly for abort confirmation
                    try:
                        await asyncio.wait_for(self._stream_done.wait(), timeout=3)
                    except (asyncio.TimeoutError, asyncio.CancelledError):
                        print()
                    print()
                else:
                    print(self._c("dim", "\nPress Ctrl+D or type /quit to exit."))


# ─── CLI Entry Point ──────────────────────────────────────────────────────────

def parse_args():
    """Simple argument parser (no dependencies)."""
    args = {
        "url": None,
        "token": None,
        "session": DEFAULT_SESSION_KEY,
    }

    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--url", "-u") and i + 1 < len(argv):
            args["url"] = argv[i + 1]
            i += 2
        elif arg in ("--token", "-t") and i + 1 < len(argv):
            args["token"] = argv[i + 1]
            i += 2
        elif arg in ("--session", "-s") and i + 1 < len(argv):
            args["session"] = argv[i + 1]
            i += 2
        elif arg in ("--help", "-h"):
            print(__doc__)
            sys.exit(0)
        else:
            i += 1

    return args


async def main():
    args = parse_args()

    # Load config
    config, config_url, config_token = load_openclaw_config()

    url = args["url"] or config_url or "ws://127.0.0.1:18789"
    token = args["token"] or config_token
    session_key = args["session"]

    # Create client
    client = OpenClawClient(url=url, token=token, session_key=session_key)

    print(f"Connecting to {url}...", flush=True)

    try:
        await client.connect()
    except Exception as e:
        print(f"Failed to connect: {e}")
        print("Make sure the gateway is running: openclaw gateway")
        sys.exit(1)

    print("Connected!\n")

    # Run interactive session
    session = ChatSession(client)
    try:
        await session.run()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
