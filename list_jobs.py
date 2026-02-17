
import asyncio
import json
from openclaw_client import OpenClawClient, load_openclaw_config

async def list_cron_jobs():
    oc_config, oc_url, oc_token = load_openclaw_config()
    oc_url = oc_url or "ws://127.0.0.1:18789"
    
    client = OpenClawClient(url=oc_url, token=oc_token, session_key="default")
    await client.connect()
    
    try:
        res = await client.request("cron.list", {})
        print("JOBS:", json.dumps(res, indent=2))
    except Exception as e:
        print("ERROR:", e)
        
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(list_cron_jobs())
