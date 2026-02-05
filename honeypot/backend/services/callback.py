import httpx
import logging
from db.models import Session
from config import settings

logger = logging.getLogger("callback")

class CallbackService:
    def __init__(self):
        self.url = settings.GUVI_CALLBACK_URL
        self.max_retries = 3

    async def send_report(self, session: dict):
        """
        Sends the final report to GUVI endpoint.
        """
        raw_intel = session.get("extracted_intelligence", {})
        
        # Map to GUVI expected keys (camelCase)
        extracted_intelligence = {
            "bankAccounts": raw_intel.get("bank_accounts", []),
            "upiIds": raw_intel.get("upi_ids", []),
            "phishingLinks": raw_intel.get("urls", []),
            "phoneNumbers": raw_intel.get("phone_numbers", []),
            "suspiciousKeywords": raw_intel.get("scam_keywords", [])
        }

        payload = {
            "sessionId": session["session_id"],
            "scamDetected": session.get("is_confirmed_scam", False),
            "totalMessagesExchanged": session.get("message_count", 0),
            "extractedIntelligence": extracted_intelligence,
            "agentNotes": session.get("agent_state", {}).get("notes", "Scam detected and intelligence gathered.")
        }
        
        logger.info(f"Sending callback for {session['session_id']}...")
        
        async with httpx.AsyncClient() as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.post(self.url, json=payload, timeout=10.0)
                    response.raise_for_status()
                    logger.info(f"✅ Callback Success: {response.status_code}")
                    return True
                except Exception as e:
                    logger.warning(f"Callback attempt {attempt+1} failed: {e}")
            
            logger.error("🚨 Callback failed after max retries.")
            return False

callback_service = CallbackService()
