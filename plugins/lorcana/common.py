import re


def remove_nonalphanumeric(s: str) -> str:
    return re.sub(r"[^\w]", "", s)
