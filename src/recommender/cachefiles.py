from datetime import date
from glob import glob
import json
import os
import recommender.constants as constants


def _get_cache_directory():
    path = os.path.expanduser("~/Documents/pyani/cache")
    os.makedirs(path, exist_ok=True)
    return path


def _getTodayDateStamp():
    return str(date.today()).replace("-", "")


def _compareDateStamps(stamp1, stamp2=None, delta=constants.OLD_DATA_THRESHOLD):
    if not stamp2:
        stamp2 = _getTodayDateStamp()
    return abs(int(stamp1) - int(stamp2)) <= delta


def _generate_data_file_name_for_user(user_name: str):
    return (
        f"{_get_cache_directory()}{os.sep}{user_name}-{_getTodayDateStamp()}-list.json"
    )


def saveUserDataFile(userName: str, entries: list):
    with open(_generate_data_file_name_for_user(user_name=userName), "w") as file:
        json.dump(entries, file)


def latest_valid_user_file_or_new(user_name: str, clean=True):
    file_names = glob(f"{_get_cache_directory()}{os.sep}{user_name}-*-list.json")
    latest_valid_file_name = None
    latest_valid_date_stamp = None
    for fileName in file_names:
        date_stamp = _extractDateStampFromFileName(fileName=fileName)
        if _compareDateStamps(date_stamp):
            if latest_valid_date_stamp is None or date_stamp > latest_valid_date_stamp:
                if clean and latest_valid_file_name:
                    os.remove(latest_valid_file_name)
                latest_valid_file_name = fileName
                latest_valid_date_stamp = date_stamp
            elif clean:
                os.remove(fileName)
        elif clean:
            os.remove(fileName)
    return latest_valid_file_name or _generate_data_file_name_for_user(
        user_name=user_name
    )


def _extractDateStampFromFileName(fileName):
    return int(fileName.split("-")[-2])


def loadDataFromFile(userFile):
    if not os.path.exists(userFile):
        return None

    with open(userFile, "r") as file:
        userList = json.load(file)

    return userList
