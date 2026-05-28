import re


def sanitize(string: str):
    return re.sub(r"[^a-zA-Z0-9_-]", "", string)


def sanitize_list(string_list: list):
    return [s for s in string_list if (s := sanitize(s))]


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
