from services.intelligence_extractor import extract_entities


def calculate_scam_score(text: str, history: list[str] | None = None) -> float:
    combined = " ".join(history or []) + " " + text
    result = extract_entities(combined)
    raw = result["threat_level"]
    return min(1.0, raw / 100.0)
