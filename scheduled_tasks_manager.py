import json
import uuid

class ScheduledTasksManager:
    """Helper to manage Cron Jobs and Heartbeat via OpenClawClient."""
    
    def __init__(self, client):
        self.client = client

    async def list_cron_jobs(self):
        """List all active cron jobs."""
        try:
            res = await self.client.request("cron.list", {})
            return res.get("jobs", [])
        except Exception as e:
            print(f"[ScheduledTasksManager] Error listing cron jobs: {e}")
            return []

    async def add_cron_job(self, name, schedule, payload, session_target_key):
        """Add a new cron job."""
        
        # Openclaw cron jobs require valid JSON payload
        # And a target session key to execute in context of
        if isinstance(payload, str):
            # If user provides string, wrap in simple chat message structure if needed
            # But the gateway might expect raw object.
            # Let's assume payload is a dict or string message
            pass

        params = {
            "name": name,
            "schedule": schedule,
            "sessionTarget": session_target_key,
            "payload": payload
        }
        
        try:
            res = await self.client.request("cron.add", params)
            return res
        except Exception as e:
            print(f"[ScheduledTasksManager] Error adding cron job: {e}")
            raise e

    async def remove_cron_job(self, job_id):
        """Remove a cron job by ID."""
        try:
            res = await self.client.request("cron.remove", {"id": job_id})
            return res
        except Exception as e:
            # Try with jobId if id fails (based on probe error message)
            try:
                res = await self.client.request("cron.remove", {"jobId": job_id})
                return res
            except Exception as e2:
                print(f"[ScheduledTasksManager] Error removing cron job: {e2}")
                raise e2

    # Heartbeat is essentially a specific Cron job in some versions,
    # or a specific system config.
    # The probe showed heartbeat.get/config are NOT valid methods.
    # So we will implement Heartbeat as a "standard" Cron Job with a specific name/tag.
    
    HEARTBEAT_JOB_NAME = "System Heartbeat"
    
    async def get_heartbeat_status(self):
        """Check if the Heartbeat cron job exists and get its schedule."""
        jobs = await self.list_cron_jobs()
        for job in jobs:
            if job.get("name") == self.HEARTBEAT_JOB_NAME:
                return {
                    "active": True,
                    "schedule": job.get("schedule"),
                    "id": job.get("id")
                }
        return {"active": False, "schedule": None, "id": None}

    async def set_heartbeat(self, active: bool, interval_minutes: int, session_target_key: str):
        """Create or Remove the Heartbeat job."""
        current = await self.get_heartbeat_status()
        
        if not active:
            if current["active"]:
                await self.remove_cron_job(current["id"])
            return {"active": False}
        
        # If active, we need to create or update
        # If it exists, remove it first to "update" (simplest approach)
        if current["active"]:
            await self.remove_cron_job(current["id"])
            
        schedule = f"*/{interval_minutes} * * * *"
        # Simple payload to trigger a check
        payload = {
            "type": "event",
            "name": "heartbeat.check"
        }
        
        await self.add_cron_job(self.HEARTBEAT_JOB_NAME, schedule, payload, session_target_key)
        return {"active": True, "schedule": schedule}
