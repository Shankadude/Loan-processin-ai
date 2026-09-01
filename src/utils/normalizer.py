import re

def normalize_name(value) -> str:
    if value is None:
        return ""
    value = str(value).upper().strip()
    value = re.sub(r"[^A-Z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def normalize_text(value) -> str:
    if value is None:
        return ""
    value = str(value).lower().strip()
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def normalize_pan(value) -> str:
    if value is None:
        return ""
    return str(value).upper().replace(" ", "")

def normalize_dob(value) -> str:
    if value is None:
        return ""
    return str(value).strip()

def to_float(value) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0