import re


def sanitize_user_name(user_name: str):
    return re.sub(r"[^a-zA-Z0-9_-]", "", user_name)


def sanitize_user_names_list(user_names_list: list):
    sanitized_user_names_list = []
    for n in user_names_list:
        s = sanitize_user_name(n)
        if s != "":
            sanitized_user_names_list.append(s)
    return sanitized_user_names_list


def get_english_title_or_user_preferred(title):
    return title["english"] if title["english"] else title["userPreferred"]


_words_to_all_caps = ["TV", "OVA", "ONA"]


def clean_format(raw_format):
    return " ".join(
        w.upper() if w in _words_to_all_caps else w.capitalize()
        for w in raw_format.replace("_", " ").upper().split(" ")
    )
