import re


def normalize_name(value):

    if value is None:
        return ""

    value = str(value).upper().strip()

    value = re.sub(
        r"[^A-Z0-9 ]+",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def normalize_text(value):

    if value is None:
        return ""

    value = str(value).lower().strip()

    value = re.sub(
        r"[^a-z0-9 ]+",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def normalize_pan(value):

    if value is None:
        return ""

    return str(value).upper().replace(" ", "")


def normalize_dob(value):

    if value is None:
        return ""

    return str(value).strip()


def to_float(value):

    if value is None or value == "":
        return 0.0

    try:
        return float(value)

    except:

        return 0.0