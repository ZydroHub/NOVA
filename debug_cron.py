
import asyncio
import json
import uuid
from openclaw_client import OpenClawClient, load_openclaw_config

async def probe_cron_add():
    oc_config, oc_url, oc_token = load_openclaw_config()
    oc_url = oc_url or "ws://127.0.0.1:18789"
    
    # Needs operator.admin scope
    client = OpenClawClient(url=oc_url, token=oc_token, session_key="default")
    
    # We need to manually add the scope since the library default does not include it yet (unless I updated it?)
    # I did update it in Step 192. So standard connect should work.
    
    print(f"Connecting to {oc_url} with full scopes...")
    await client.connect()
    print("Connected.")
    
    # Base params
    base_params = {
        "name": f"Probe Job {uuid.uuid4().hex[:4]}",
        "schedule": "*/60 * * * *",
        "sessionTarget": "default",
        "description": "Probe test job"
    }

    payloads_to_test = [
        {"desc": "Simple Text", "payload": {"text": "hello"}},
        {"desc": "Simple Message", "payload": {"message": "hello"}},
        {"desc": "Simple Content", "payload": {"content": "hello"}},
        {"desc": "Type Text", "payload": {"type": "text", "text": "hello"}},
        {"desc": "Kind Agent Turn", "payload": {"kind": "agent-turn", "agentId": "default", "message": "hello"}},
        {"desc": "Kind Agent Turn (text)", "payload": {"kind": "agent-turn", "agentId": "default", "text": "hello"}},
        {"desc": "Kind Agent (no turn)", "payload": {"kind": "agent", "agentId": "default", "text": "hello"}},
        {"desc": "Kind Text", "payload": {"kind": "text", "text": "hello"}},
    ]

    for test in payloads_to_test:
        print(f"\n--- Testing: {test['desc']} ---")
        params = base_params.copy()
        params["payload"] = test["payload"]
        params["name"] = f"Probe {test['desc']}"
        
        try:
            res = await client.request("cron.add", params)
            print("SUCCESS:", json.dumps(res, indent=2))
            
            # Cleanup
            job_id = res.get("id")
            if job_id:
                await client.request("cron.remove", {"id": job_id})
                print("Cleaned up job.")
                
        except Exception as e:
            print("FAILED:", e)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(probe_cron_add())
