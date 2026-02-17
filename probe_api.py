
import asyncio
import json
import uuid
import sys
# Import the client from the local file
from openclaw_client import OpenClawClient, load_openclaw_config, PROTOCOL_VERSION

class AdminClient(OpenClawClient):
    async def _do_handshake(self):
        """Send the connect request with ADMIN scopes."""
        connect_params = {
            "minProtocol": PROTOCOL_VERSION,
            "maxProtocol": PROTOCOL_VERSION,
            "client": {
                "id": "gateway-client",
                "displayName": "Python OpenClaw Probe",
                "version": "1.0.0",
                "platform": sys.platform,
                "mode": "cli",
            },
            "role": "operator",
            # ADDING operator.admin HERE
            "scopes": ["operator.read", "operator.write", "operator.admin"],
            "caps": [],
            "auth": {"token": self.token} if self.token else {},
        }

        result = await self.request("connect", connect_params)
        if result and result.get("type") == "hello-ok":
            self.connected = True
        else:
            self.connected = True

async def probe():
    config, url, token = load_openclaw_config()
    if not url: url = "ws://127.0.0.1:18789"
    
    print(f"Connecting to {url} with ADMIN scopes...")
    client = AdminClient(url=url, token=token)
    
    try:
        await client.connect()
        print("Connected.")
        
        # Test 1: Cron List
        print("\n--- Probing 'cron.list' ---")
        try:
            res = await client.request("cron.list", {})
            print("Response:", json.dumps(res, indent=2))
        except Exception as e:
            print("Error:", e)

        # Test 2: Cron Add (Probe schema)
        print("\n--- Probing 'cron.add' (expecting schema error) ---")
        try:
            # Sending empty body to see required fields
            res = await client.request("cron.add", {})
            print("Response:", json.dumps(res, indent=2))
        except Exception as e:
            print("Error:", e)

        # Test 4: Cron Remove (Probe schema)
        print("\n--- Probing 'cron.remove' ---")
        try:
            res = await client.request("cron.remove", {})
            print("Response:", json.dumps(res, indent=2))
        except Exception as e:
            print("Error:", e)
            
        # Test 5: System/Config
        print("\n--- Probing 'system.config' ---")
        try:
            res = await client.request("system.config", {})
            print("Response:", json.dumps(res, indent=2))
        except Exception as e:
            print("Error:", e)

    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(probe())
