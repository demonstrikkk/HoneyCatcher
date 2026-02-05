import re
import logging
from typing import Dict, List
import os
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from db.mongo import db
from db.models import Intelligence
from config import settings

logger = logging.getLogger("intelligence")

class IntelligenceExtractor:
    def __init__(self):
        self.groq_key = settings.GROQ_API_KEY
        if self.groq_key:
            self.llm = ChatGroq(temperature=0, model_name="llama-3.3-70b-versatile", api_key=self.groq_key)
        else:
            self.llm = None
    
    async def extract(self, session_id: str, message: str):
        """
        Extracts entities from the message and updates the session intelligence.
        """
        # 1. Regex Extraction
        extracted = self._regex_extract(message)
        
        # 2. LLM Extraction (if key exists)
        if self.llm:
            try:
                prompt = ChatPromptTemplate.from_template(
                    "Extract scam intelligence from this message: '{text}'\n"
                    "Return JSON with keys: bank_accounts, upi_ids, phone_numbers, urls, scam_keywords, behavioral_tactics. "
                    "Lists of strings. Empty list if none."
                )
                chain = prompt | self.llm | JsonOutputParser()
                llm_result = await chain.ainvoke({"text": message})
                
                # Merge LLM results
                for key in extracted:
                    if key in llm_result and isinstance(llm_result[key], list):
                        extracted[key].extend(llm_result[key])
            except Exception as e:
                logger.error(f"LLM Extraction failed: {e}")

        # 3. Save to DB (Atomic Update with Deduplication)
        # We fetch, merge, and update.
        session = await db.sessions.find_one({"session_id": session_id})
        if not session:
            return

        current_intel = session.get("extracted_intelligence", {})
        
        # Merge lists and deduplicate
        updates = {}
        for key in ["bank_accounts", "upi_ids", "phone_numbers", "urls", "scam_keywords", "behavioral_tactics"]:
            old_list = current_intel.get(key, [])
            new_items = extracted.get(key, [])
            combined = list(set(old_list + new_items))
            updates[f"extracted_intelligence.{key}"] = combined
            
        await db.sessions.update_one({"session_id": session_id}, {"$set": updates})
        logger.info(f"Updated intelligence for {session_id}")

    def _regex_extract(self, text: str) -> Dict[str, List[str]]:
        data = {
            "bank_accounts": [],
            "upi_ids": [],
            "phone_numbers": [],
            "urls": [],
            "scam_keywords": [],
            "behavioral_tactics": []
        }
        
        # Regex Patterns
        patterns = {
            "urls": r"https?://\S+",
            "upi_ids": r"[\w\.\-_]+@[\w]+",
            "phone_numbers": r"\b\d{10}\b",
            "bank_accounts": r"\b\d{9,18}\b"  # Generic account number
        }
        
        for key, pat in patterns.items():
            matches = re.findall(pat, text)
            data[key] = matches
            
        return data

extraction_service = IntelligenceExtractor()
