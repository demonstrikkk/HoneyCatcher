import re
import logging
from typing import Dict, Any
from config import settings

logger = logging.getLogger(__name__)

_PHONE_RE   = re.compile(r"(\+?\d[\d\s\-]{8,14}\d)")
_UPI_RE     = re.compile(r"[\w.\-]+@[\w.\-]+")
_BANK_RE    = re.compile(r"\b\d{9,18}\b")
_URL_RE     = re.compile(r"https?://[^\s]+")
_IFSC_RE    = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")

_TACTICS: Dict[str, list] = {
    "urgency":    ["urgent", "immediately", "right now", "expire", "24 hours", "last chance"],
    "authority":  ["rbi", "bank of india", "police", "cbi", "income tax", "government", "officer"],
    "fear":       ["arrest", "blocked", "legal action", "penalty", "lawsuit", "cancelled"],
    "greed":      ["prize", "lottery", "winner", "refund", "cashback", "reward"],
    "tech_support": ["virus", "hack", "remote access", "teamviewer", "anydesk", "error"],
    "romance":    ["love", "relationship", "lonely", "missed you"],
}


def extract_entities(text: str) -> Dict[str, Any]:
    lower = text.lower()
    entities = []

    for m in _PHONE_RE.finditer(text):
        entities.append({"type": "phone", "value": m.group().strip(), "confidence": 0.85})

    for m in _UPI_RE.finditer(text):
        entities.append({"type": "upi", "value": m.group(), "confidence": 0.80})

    for m in _URL_RE.finditer(text):
        entities.append({"type": "url", "value": m.group(), "confidence": 1.0})

    for m in _BANK_RE.finditer(text):
        entities.append({"type": "bank_account", "value": m.group(), "confidence": 0.70})

    for m in _IFSC_RE.finditer(text):
        entities.append({"type": "ifsc", "value": m.group(), "confidence": 0.95})

    tactics = [
        name for name, kws in _TACTICS.items() if any(kw in lower for kw in kws)
    ]

    threat = min(100, len(entities) * 10 + len(tactics) * 15)

    return {"entities": entities, "tactics": tactics, "threat_level": threat}
