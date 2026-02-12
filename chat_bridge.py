#!/usr/bin/env python3
"""
WebSocket bridge between the React chat GUI and the OpenClaw gateway.

Usage:
    python3 chat_bridge.py                    # default settings
    python3 chat_bridge.py --port 8765        # custom bridge port
    python3 chat_bridge.py --session mykey    # custom session key

Requires: pip install websockets
"""

import asyncio
import json
import sys
import traceback

try:
    import websockets
except ImportError:
    print("Error: 'websockets' package is required.")
    print("Install it with:  pip install websockets")
    sys.exit(1)

# Import the OpenClaw client from the same directory
from openclaw_client import OpenClawClient, load_openclaw_config, DEFAULT_SESSION_KEY


BRIDGE_PORT = 8765


class ChatBridge:
    """Bridges a single React WebSocket client to the OpenClaw gateway."""

    def __init__(self, openclaw_url: str, token: str, session_key: str):
        self.openclaw_url = openclaw_url
        self.token = token
        self.session_key = session_key

    async def handle_client(self, ws):
        """Handle a single React frontend connection."""
        print(f"[bridge] Client connected from {ws.remote_address}", flush=True)

        client = None
        oc_connected = False
        stream_text = ""

        async def safe_send(data):
            """Send JSON to the React frontend, ignoring errors."""
            try:
                await ws.send(json.dumps(data))
            except Exception:
                pass

        def on_chat_event(payload):
            nonlocal stream_text
            session_key = payload.get("sessionKey")
            if session_key != client.session_key:
                return

            run_id = payload.get("runId")
            if run_id and client._current_run_id and run_id != client._current_run_id:
                return

            state = payload.get("state")

            if state == "delta":
                message = payload.get("message", {})
                content = message.get("content", [])
                full_text = ""
                for block in content:
                    if block.get("type") == "text":
                        full_text = block.get("text", "")
                stream_text = full_text
                asyncio.ensure_future(safe_send({
                    "type": "stream_delta",
                    "text": full_text,
                }))

            elif state == "final":
                message = payload.get("message", {})
                content = message.get("content", [])
                final_text = ""
                for block in content:
                    if block.get("type") == "text":
                        final_text = block.get("text", "")
                stream_text = ""
                asyncio.ensure_future(safe_send({
                    "type": "stream_final",
                    "text": final_text,
                }))

            elif state == "aborted":
                asyncio.ensure_future(safe_send({
                    "type": "stream_aborted",
                }))
                stream_text = ""

            elif state == "error":
                error_msg = payload.get("errorMessage", "unknown error")
                asyncio.ensure_future(safe_send({
                    "type": "stream_error",
                    "error": error_msg,
                }))
                stream_text = ""

        # Try to connect to OpenClaw
        try:
            client = OpenClawClient(
                url=self.openclaw_url,
                token=self.token,
                session_key=self.session_key,
            )
            await client.connect()
            client.on_event("chat", on_chat_event)
            oc_connected = True
            print(f"[bridge] Connected to OpenClaw gateway at {self.openclaw_url}", flush=True)
        except Exception as e:
            print(f"[bridge] WARNING: Could not connect to OpenClaw: {e}", flush=True)
            traceback.print_exc()
            await safe_send({
                "type": "stream_error",
                "error": f"Could not connect to OpenClaw gateway: {e}",
            })
            # DON'T return — keep the WS alive so the frontend stays connected
            # and can retry when the gateway comes up.

        # Send history to the frontend
        if oc_connected:
            try:
                history = await client.chat_history()
                hist_messages = []
                for msg in history.get("messages", []):
                    role = msg.get("role", "")
                    content = msg.get("content", [])
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif isinstance(block, str):
                            text_parts.append(block)
                    text = "\n".join(text_parts).strip()
                    if text and role in ("user", "assistant"):
                        hist_messages.append({"role": role, "text": text})

                await safe_send({
                    "type": "history",
                    "messages": hist_messages,
                })
            except Exception as e:
                print(f"[bridge] Could not load history: {e}", flush=True)

        # Main message loop — keep alive even if OpenClaw isn't connected
        try:
            async for raw in ws:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_type = data.get("type")
                print(f"[bridge] Received: {msg_type}", flush=True)

                if not oc_connected:
                    # Try to reconnect to OpenClaw on each message attempt
                    try:
                        client = OpenClawClient(
                            url=self.openclaw_url,
                            token=self.token,
                            session_key=self.session_key,
                        )
                        await client.connect()
                        client.on_event("chat", on_chat_event)
                        oc_connected = True
                        print(f"[bridge] Reconnected to OpenClaw!", flush=True)
                    except Exception as e:
                        await safe_send({
                            "type": "stream_error",
                            "error": f"OpenClaw gateway not available: {e}",
                        })
                        continue

                if msg_type == "send":
                    message = data.get("message", "").strip()
                    if not message:
                        continue

                    stream_text = ""
                    await safe_send({"type": "stream_start"})

                    try:
                        await client.chat_send(message)
                    except Exception as e:
                        print(f"[bridge] Send error: {e}", flush=True)
                        await safe_send({
                            "type": "stream_error",
                            "error": str(e),
                        })

                elif msg_type == "abort":
                    if client and client._current_run_id:
                        try:
                            await client.chat_abort(client._current_run_id)
                        except Exception as e:
                            print(f"[bridge] Abort error: {e}", flush=True)

                elif msg_type == "reset":
                    try:
                        await client.session_reset()
                        await safe_send({"type": "session_reset"})
                    except Exception as e:
                        await safe_send({
                            "type": "stream_error",
                            "error": f"Reset failed: {e}",
                        })

        except websockets.ConnectionClosed:
            print(f"[bridge] Client disconnected", flush=True)
        except Exception as e:
            print(f"[bridge] Unexpected error: {e}", flush=True)
            traceback.print_exc()
        finally:
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass


async def main():
    # Parse simple args
    port = BRIDGE_PORT
    session_key = DEFAULT_SESSION_KEY

    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        if argv[i] == "--port" and i + 1 < len(argv):
            port = int(argv[i + 1])
            i += 2
        elif argv[i] in ("--session", "-s") and i + 1 < len(argv):
            session_key = argv[i + 1]
            i += 2
        else:
            i += 1

    # Load OpenClaw config
    config, url, token = load_openclaw_config()
    url = url or "ws://127.0.0.1:18789"

    bridge = ChatBridge(openclaw_url=url, token=token, session_key=session_key)

    print(f"🦞 Chat Bridge starting on ws://0.0.0.0:{port}", flush=True)
    print(f"   OpenClaw gateway: {url}", flush=True)
    print(f"   Session key: {session_key}", flush=True)
    print(flush=True)

    async with websockets.serve(bridge.handle_client, "0.0.0.0", port):
        print(f"[bridge] Server listening on port {port}", flush=True)
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBridge stopped.")
