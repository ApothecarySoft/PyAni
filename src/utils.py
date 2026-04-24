import re


def sanitizeUserName(userName: str):
    return re.sub(r"[^a-zA-Z0-9_-]", "", userName)
