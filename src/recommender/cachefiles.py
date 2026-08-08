import json
import os
from datetime import date
from glob import glob

import recommender.constants as constants
from recommender.utils import sanitize


def _get_cache_directory():
    path = os.path.expanduser("~/Documents/pyani/cache")
    os.makedirs(path, exist_ok=True)
    return path


def _get_today_date_stamp():
    return date.today().strftime("%Y%m%d")


def _compare_date_stamps(stamp1, stamp2=None, delta=constants.OLD_DATA_THRESHOLD):
    if not stamp2:
        stamp2 = _get_today_date_stamp()
    return abs(int(stamp1) - int(stamp2)) <= delta


def _generate_cache_file_name_for_item(item_name: str):
    return f"{_get_cache_directory()}{os.sep}{sanitize(item_name)}-{_get_today_date_stamp()}-list.json"


def save_cache_file(item_name: str, entries):
    with open(_generate_cache_file_name_for_item(item_name=item_name), "w") as file:
        json.dump(entries, file)


def remove_all_tag_file(tag: str):
    file_names = glob(f"{_get_cache_directory()}{os.sep}{tag}-*-list.json")
    for fileName in file_names:
        os.remove(fileName)


def latest_valid_cache_file_or_new(item_name: str, clean=True, expiration: bool = True):
    file_names = glob(
        f"{_get_cache_directory()}{os.sep}{sanitize(item_name)}-*-list.json"
    )
    latest_valid_file_name = None
    latest_valid_date_stamp = None
    for fileName in file_names:
        date_stamp = _extract_date_stamp_from_file_name(file_name=fileName)
        if not expiration or _compare_date_stamps(date_stamp):
            if latest_valid_date_stamp is None or date_stamp > latest_valid_date_stamp:
                if clean and latest_valid_file_name is not None:
                    os.remove(latest_valid_file_name)
                latest_valid_file_name = fileName
                latest_valid_date_stamp = date_stamp
            elif clean:
                os.remove(fileName)
        elif clean:
            os.remove(fileName)
    return latest_valid_file_name or _generate_cache_file_name_for_item(
        item_name=item_name
    )


def _extract_date_stamp_from_file_name(file_name):
    return int(file_name.split("-")[-2])


def load_data_from_file(user_file):
    if not os.path.exists(user_file):
        return None

    with open(user_file, "r") as file:
        user_list = json.load(file)

    return user_list


def _get_tags_file_name():
    return f"{_get_cache_directory()}{os.sep}tags.txt"


def load_tags_from_cache() -> list[str]:
    tags_file = _get_tags_file_name()
    if not os.path.exists(tags_file):
        return []
    else:
        with open(tags_file, "r") as file:
            tags_list = file.readlines()
        return tags_list


def save_tags_to_cache(tags_str: str):
    tags_file = _get_tags_file_name()
    with open(tags_file, "w") as file:
        file.write(tags_str)
