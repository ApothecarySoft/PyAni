import re
from datetime import date

sanitize_pattern = re.compile(r"[^a-zA-Z0-9_-]")


def sanitize(string: str):
    return re.sub(sanitize_pattern, "", string)


def sanitize_list(string_list: list):
    sanitized_user_names_list = []
    for n in string_list:
        s = sanitize(n)
        if s != "":
            sanitized_user_names_list.append(s)
    return sanitized_user_names_list


def get_english_title_or_user_preferred(title):
    return title["english"] if title["english"] else title["userPreferred"]


_words_to_all_caps = ["TV", "OVA", "ONA"]


def clean_format(raw_format):
    if raw_format is None:
        return "Unknown"
    return " ".join(
        w.upper() if w in _words_to_all_caps else w.capitalize()
        for w in raw_format.replace("_", " ").upper().split(" ")
    )

def get_today_date_stamp():
    return date.today().strftime("%Y%m%d")
