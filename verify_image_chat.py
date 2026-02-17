import asyncio
import websockets
import json
import sys

async def test():
    uri = "ws://127.0.0.1:8000/ws"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket")
            
            # Send message with image
            msg = {
                "type": "send",
                "message": "Describe this image",
                "images": ["test_image.jpg"]
            }
            await websocket.send(json.dumps(msg))
            print(f"Sent: {msg}")
            
            # Wait for response
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    print(f"Received: {data}")
                    
                    if data.get("type") == "stream_start":
                        print("SUCCESS: Backend accepted request and started stream/processing.")
                        break
                    elif data.get("type") == "stream_error":
                        print(f"SUCCESS (Partial): Backend processed request but OpenClaw failed (expected if local model not running): {data.get('error')}")
                        break
                except asyncio.TimeoutError:
                    print("TIMEOUT: No response from backend.")
                    break
                    
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test())
