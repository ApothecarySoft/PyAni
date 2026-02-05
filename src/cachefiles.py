from datetime import date
from glob import glob
import json
import os
import constants
import re


def _getTodayDateStamp():
    return str(date.today()).replace("-", "")


def _compareDateStamps(stamp1, stamp2=None, delta=constants.OLD_DATA_THRESHOLD):
    if not stamp2:
        stamp2 = _getTodayDateStamp()
    return abs(int(stamp1) - int(stamp2)) <= delta


def _generateDataFileNameForUser(userName: str):
    return f"{_sanitizeUserName(userName=userName)}-{_getTodayDateStamp()}-list.json"


def saveUserDataFile(userName: str, entries: list):
    with open(_generateDataFileNameForUser(userName=userName), "w") as file:
        json.dump(entries, file)


def _sanitizeUserName(userName: str):
    return re.sub(r'[^a-zA-Z0-9_-]', '', userName)


def latestValidUserFileOrNew(userName: str, clean=True):
    fileNames = glob(f"{_sanitizeUserName(userName=userName)}-*-list.json")
    latestValidFileName = None
    latestValidDateStamp = None
    for fileName in fileNames:
        dateStamp = _extractDateStampFromFileName(fileName=fileName)
        if _compareDateStamps(dateStamp):
            if not latestValidDateStamp or dateStamp > latestValidDateStamp:
                if clean and latestValidFileName:
                    os.remove(latestValidFileName)
                latestValidFileName = fileName
                latestValidDateStamp = dateStamp
            elif clean:
                os.remove(fileName)
        elif clean:
            os.remove(fileName)
    return latestValidFileName or _generateDataFileNameForUser(userName=userName)


def _extractDateStampFromFileName(fileName):
    return int(fileName.split("-")[-2])


def loadDataFromFile(userFile):
    if not os.path.exists(userFile):
        return None

    with open(userFile, "r") as file:
        userList = json.load(file)

    return userList
