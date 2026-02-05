from datetime import datetime, timedelta
import logging
from db.mongo import db
from services.callback import callback_service

logger = logging.getLogger("lifecycle")

class LifecycleManager:
    MAX_MESSAGES = 50
    TIMEOUT_HOURS = 24

    async def check_termination(self, session_id: str):
        """
        Checks if the session should be terminated.
        """
        session = await db.sessions.find_one({"session_id": session_id})
        if not session:
            return

        terminated = False
        reason = ""

        # 1. Message Limit
        if session.get("message_count", 0) >= self.MAX_MESSAGES:
            terminated = True
            reason = "Max messages reached"

        # 2. Timeout (optional implementation)
        # last_update = session.get("last_updated")
        
        if terminated and session.get("status") != "terminated":
            await self._terminate(session, reason)

    async def _terminate(self, session: dict, reason: str):
        """Terminates session and triggers callback."""
        logger.info(f"Terminating session {session['session_id']}: {reason}")
        
        await db.sessions.update_one(
            {"session_id": session['session_id']},
            {"$set": {"status": "terminated", "termination_reason": reason}}
        )
        
        # Send Callback
        # Fetch fresh data
        final_session = await db.sessions.find_one({"session_id": session['session_id']})
        await callback_service.send_report(final_session)

lifecycle_manager = LifecycleManager()
