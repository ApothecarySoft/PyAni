from datetime import date
from glob import glob
import json
import os

oldDataThreshold = 1


def getTodayDateStamp():
    return str(date.today()).replace("-", "")


def compareDateStamps(stamp1, stamp2=getTodayDateStamp(), delta=oldDataThreshold):
    return abs(int(stamp1) - int(stamp2)) <= delta


def generateDataFileNameForUser(userName: str):
    return f"{userName}-{getTodayDateStamp()}-list.json"


def saveUserDataFile(userName: str, entries: list):
    with open(generateDataFileNameForUser(userName=userName), "w") as file:
        json.dump(entries, file)


def latestValidUserFileOrNew(userName: str, clean=True):
    fileNames = glob(f"{userName}-*-list.json")
    latestValidFileName = None
    latestValidDateStamp = None
    for fileName in fileNames:
        dateStamp = extractDateStampFromFileName(fileName=fileName)
        if compareDateStamps(dateStamp):
            if not latestValidDateStamp or dateStamp > latestValidDateStamp:
                if clean and latestValidFileName:
                    os.remove(latestValidFileName)
                latestValidFileName = fileName
                latestValidDateStamp = dateStamp
            elif clean:
                os.remove(fileName)
        elif clean:
            os.remove(fileName)
    return latestValidFileName or generateDataFileNameForUser(userName=userName)


def extractDateStampFromFileName(fileName):
    return int(fileName.split("-")[-2])


def loadDataFromFile(userFile):
    with open(userFile, "r") as file:
        userList = json.load(file)

    return userList
