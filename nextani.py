from gql import gql, Client
from gql.transport.httpx import HTTPXTransport
from gql.transport.exceptions import TransportQueryError
import queries
import time
import json
import argparse
import os
import math
from pprint import pprint


def countdownTimer_s(seconds: int):
    while seconds > 0:
        print(seconds)
        time.sleep(1)
        seconds -= 1


def fetchDataForChunk(client, mediaType: str, chunk: int, userName):
    print(f"fetching for chunk #{chunk}")
    query = gql(
        queries.userListQuery(userName=userName, mediaType=mediaType, chunk=chunk)
    )
    result = None
    while result == None:
        try:
            result = client.execute(query)
        except TransportQueryError as e:
            errorCode = e.errors[0]["status"]
            if errorCode == 429:
                print(
                    f"got http {errorCode}, server is rate limiting us. waiting to continue fetching data"
                )
                countdownTimer_s(65)
            else:
                print(f"unhandled http error {errorCode}. trying again in 10 seconds")
                countdownTimer_s(10)
    lists = result["MediaListCollection"]["lists"]
    # print(lists)
    entries = [
        listEntries
        for currentList in lists
        for listEntries in currentList["entries"]
        if not currentList["isCustomList"]
    ]
    return entries, result["MediaListCollection"]["hasNextChunk"]


def fetchDataForType(client, mediaType: str, userName):
    print(f"fetching data for type {mediaType}")
    chunkNum = 0
    hasNextChunk = True
    entries = []
    while hasNextChunk:
        chunkNum += 1
        newEntries, hasNextChunk = fetchDataForChunk(
            client=client, mediaType=mediaType, chunk=chunkNum, userName=userName
        )
        entries += newEntries

    return entries


def fetchDataForUser(userName):
    print(f"fetching data for user {userName}")
    transport = HTTPXTransport(url="https://graphql.anilist.co", timeout=120)
    client = Client(transport=transport, fetch_schema_from_transport=True)
    entries = fetchDataForType(client=client, mediaType="ANIME", userName=userName)
    entries += fetchDataForType(client=client, mediaType="MANGA", userName=userName)

    with open(f"{userName}-list.json", "w") as file:
        json.dump(entries, file)

    return entries


def loadDataFromFile(userFile):
    with open(userFile, "r") as file:
        userList = json.load(file)

    return userList


def calculateMeanScore(userList):
    scoresTotal = 0
    scoresCount = 0

    for ratedAni in userList:
        score = ratedAni["score"]
        if score <= 0:
            continue
        scoresTotal += score
        scoresCount += 1

    if scoresCount <= 0:
        return 50

    return scoresTotal / scoresCount


def calculateInitial(userList, meanScore):
    global angles
    angleKeys = list(angles.keys())
    tagRatings = {}
    studioRatings = {}
    staffRatings = {}
    recommendations = {}
    origins = {}

    for ratedAni in userList:
        score = ratedAni["score"]
        status = ratedAni["status"] if "status" in ratedAni.keys() else ""
        if score <= 0:
            if status == "DROPPED":
                score = 25
            else:
                score = meanScore
        media = ratedAni["media"]
        mediaMeanScore = media["meanScore"] or 1
        popularity = media["popularity"]

        for tag in media["tags"]:
            tagRank = tag["rank"]
            tagId = tag["id"]
            if tagId not in tagRatings:
                tagRatings[tagId] = {
                    "tag": tag,
                    "weightedScoreSum": score * tagRank,
                    "weightSum": tagRank,
                }
            else:
                oldTagRating = tagRatings[tagId]
                tagRatings[tagId] = {
                    "tag": oldTagRating["tag"],
                    "weightedScoreSum": oldTagRating["weightedScoreSum"]
                    + score * tagRank,
                    "weightSum": oldTagRating["weightSum"] + tagRank,
                }

        for studio in media["studios"]["nodes"]:
            studioId = studio["id"]
            if studioId not in studioRatings:
                studioRatings[studioId] = {
                    "studio": studio,
                    "scoreSum": score,
                    "studioOccurrence": 1,
                }
            else:
                oldStudioRating = studioRatings[studioId]
                studioRatings[studioId] = {
                    "studio": oldStudioRating["studio"],
                    "scoreSum": oldStudioRating["scoreSum"] + score,
                    "studioOccurrence": oldStudioRating["studioOccurrence"] + 1,
                }

        for staff in media["staff"]["nodes"]:
            staffId = staff["id"]
            if staffId not in staffRatings:
                staffRatings[staffId] = {
                    "staff": staff,
                    "scoreSum": score,
                    "staffOccurrence": 1,
                }
            else:
                oldStaffRating = staffRatings[staffId]
                staffRatings[staffId] = {
                    "staff": oldStaffRating["staff"],
                    "scoreSum": oldStaffRating["scoreSum"] + score,
                    "staffOccurrence": oldStaffRating["staffOccurrence"] + 1,
                }

        for rec in media["recommendations"]["nodes"]:
            rating = rec["rating"]

            # ensure we don't count an opinion held by only one person (and don't count negative values)
            if rating < 1:
                continue

            recMedia = rec["mediaRecommendation"]

            # ensure we do not try to process null values
            if not recMedia:
                continue

            recPopularity = recMedia["popularity"]
            recId = recMedia["id"]

            # ensure that we don't recommend things that the user already has on their list
            # if any(x['media']['id'] == recId for x in userList):
            #     continue

            userMatch = next((x for x in userList if x["media"]["id"] == recId), None)
            if userMatch:
                origins.setdefault(recMedia["id"], {}).setdefault(angleKeys[0], {})[
                    media["id"]
                ] = userMatch["score"]

            normalizedRating = (
                rating / (popularity + recPopularity) * score
            )  # normalize the rating to mitigate popularity bias and factor in user score
            if normalizedRating > 0.005:
                origins.setdefault(recMedia["id"], {}).setdefault(angleKeys[1], {})[
                    media["id"]
                ] = media
            scaledRating = (
                normalizedRating * mediaMeanScore
            )  # scale rating based on mean score

            # I feel like there's gotta be a more elegant way to do this
            if recId not in recommendations:
                recommendations[recId] = {
                    "recScore": scaledRating,
                    "recMedia": recMedia,
                    "recCount": 1,
                }
            else:
                oldRecommendation = recommendations[recId]
                recommendations[recId] = {
                    "recScore": oldRecommendation["recScore"] + scaledRating,
                    "recMedia": oldRecommendation["recMedia"],
                    "recCount": oldRecommendation["recCount"] + 1,
                }

    finalTagRatings = [
        {"tag": x["tag"], "score": x["weightedScoreSum"] / x["weightSum"]}
        for x in list(tagRatings.values())
        if x["weightSum"] > 200
    ]
    finalTagRatings.sort(key=lambda x: -x["score"])

    finalStudioRatings = [
        {"studio": x["studio"], "score": x["scoreSum"] / x["studioOccurrence"]}
        for x in list(studioRatings.values())
        if x["studioOccurrence"] > 2
    ]
    finalStudioRatings.sort(key=lambda x: -x["score"])

    finalStaffRatings = [
        {"staff": x["staff"], "score": x["scoreSum"] / x["staffOccurrence"]}
        for x in list(staffRatings.values())
        if x["staffOccurrence"] >= 4
    ]
    finalStaffRatings.sort(key=lambda x: -x["score"])

    finalRecList = [
        {"recScore": x["recScore"] / x["recCount"], "recMedia": x["recMedia"]}
        for x in list(recommendations.values())
        if x["recCount"] > 1
    ]

    return finalTagRatings, finalStudioRatings, finalRecList, finalStaffRatings, origins


def calculateBiases(
    tagRatings,
    studioRatings,
    recs,
    staffRatings,
    useTags,
    useStudios,
    useStaff,
    recOrigins,
    userMean,
):
    global angles
    angleKeys = list(angles.keys())
    finalRecs = []
    for rec in recs:
        tagTotal = 0
        tagCount = 0
        tags = rec["recMedia"]["tags"]
        tagRatings_d = {x["tag"]["id"]: x for x in tagRatings}
        if useTags:
            for tag in tags:
                tagId = tag["id"]
                if tagId not in tagRatings_d:
                    continue
                tagTotal += tagRatings_d[tagId]["score"] * tag["rank"]
                tagCount += 1
                if useTags and tagRatings_d[tagId]["score"] > userMean - 3:
                    recOrigins.setdefault(rec["recMedia"]["id"], {}).setdefault(
                        angleKeys[2], {}
                    )[tagId] = tag
        tagScore = tagTotal / tagCount if tagCount > 0 else 0

        studioTotal = 0
        studioCount = 0
        studios = rec["recMedia"]["studios"]["nodes"]
        studioRatings_d = {x["studio"]["id"]: x for x in studioRatings}
        if useStudios:
            for studio in studios:
                studioId = studio["id"]
                if studioId not in studioRatings_d:
                    continue
                studioTotal += studioRatings_d[studioId]["score"]
                studioCount += 1
                if useStudios and studioRatings_d[studioId]["score"] > userMean - 3:
                    recOrigins.setdefault(rec["recMedia"]["id"], {}).setdefault(
                        angleKeys[3], {}
                    )[studioId] = studio
        studioScore = studioTotal / studioCount if studioCount > 0 else 0

        staffTotal = 0
        staffCount = 0
        staffs = rec["recMedia"]["staff"]["nodes"]
        staffRatings_d = {x["staff"]["id"]: x for x in staffRatings}
        if useStaff:
            for staff in staffs:
                staffId = staff["id"]
                if staffId not in staffRatings_d:
                    continue
                staffTotal += staffRatings_d[staffId]["score"]
                staffCount += 1
                if useStaff and staffRatings_d[staffId]["score"] > userMean - 3:
                    recOrigins.setdefault(rec["recMedia"]["id"], {}).setdefault(
                        angleKeys[4], {}
                    )[staffId] = staff
        staffScore = staffTotal / staffCount if staffCount > 0 else 0

        finalRecs.append(
            {
                "recScore": rec["recScore"] * (tagScore + 1) * (studioScore + 1),
                "recMedia": rec["recMedia"],
            }
        )
    finalRecs.sort(key=lambda x: -x["recScore"])

    return finalRecs, recOrigins


def generateOriginStringForType(media, origins, userName=None):
    string = f"\t{userName}\n" if userName else ""
    global angles
    for angle, text in angles.items():
        if media["id"] not in origins:
            continue
        if angle not in origins[media["id"]]:
            continue

        if angle == "userRating":
            string += f"\tYou {text} {list(origins[media['id']][angle].values())[0]}%\n"
            continue

        string += f"\t{text} "
        for origin in origins[media["id"]][angle].values():
            name = ""
            if "title" in origin:
                name = getEnglishTitleOrUserPreferred(origin["title"])
            elif "name" in origin:
                name = (
                    origin["name"]
                    if isinstance(origin["name"], str)
                    else origin["name"]["userPreferred"]
                )
            elif type(origin) == str:
                name = origin
            string += f"{name}, "
        string = string[:-2] + "\n"
    return string


def getEnglishTitleOrUserPreferred(title):
    return title["english"] if title["english"] else title["userPreferred"]


def writeRecList(finalRecs, origins, userNames):
    fullName = ""
    if len(userNames) > 1:
        for userName in userNames:
            fullName += f"{userName}-"
    else:
        fullName = f"{userNames[0]}-"
    with open(f"{fullName}recs.txt", "w", encoding="utf-8") as f:
        for rec in finalRecs:

            media = rec["recMedia"]
            title = getEnglishTitleOrUserPreferred(media["title"])
            mediaFormat = media["format"]
            year = media["startDate"]["year"]
            score = rec["recScore"]
            print(f"{title} ({mediaFormat}, {year}): {score}%", file=f)
            for i in range(len(userNames)):
                print(
                    generateOriginStringForType(
                        media=media, origins=origins[i], userName=userNames[i]
                    ),
                    file=f,
                )


def getRecommendationList(userName, useTags, useStudios, useStaff, refresh):
    if not userName:
        return None, None

    userFile = f"{userName}-list.json"
    userList = []

    if refresh or not os.path.exists(userFile):
        userList = fetchDataForUser(userName)
    else:
        userList = loadDataFromFile(userFile)

    print(f"loaded {len(userList)} titles for {userName}")

    meanScore = calculateMeanScore(userList)

    print(f"{userName} gives a mean score of {meanScore}")

    tags, studios, recommendations, staffs, origins = calculateInitial(
        userList, meanScore
    )

    finalRecs, finalOrigins = calculateBiases(
        tags,
        studios,
        recommendations,
        staffs,
        useTags,
        useStudios,
        useStaff,
        origins,
        userMean=meanScore,
    )

    logBase = math.e
    topScore = math.log(finalRecs[0]["recScore"] + 1, logBase) ** 2

    for rec in finalRecs:
        rec["recScore"] = round(
            (math.log(rec["recScore"] + 1, logBase) ** 2) / topScore * 100, 2
        )

    with open(f"{userName}-tags.txt", "w", encoding="utf-8") as f:
        for tag in tags:
            print(f"{tag['tag']['name']}: {tag['score']}%", file=f)

    with open(f"{userName}-studios.txt", "w", encoding="utf-8") as f:
        for studio in studios:
            print(f"{studio['studio']['name']}: {studio['score']}%", file=f)

    with open(f"{userName}-staff.txt", "w", encoding="utf-8") as f:
        for staff in staffs:
            print(
                f"{staff['staff']['name']['userPreferred']}: {staff['score']}%", file=f
            )

    writeRecList(userNames=[userName], finalRecs=finalRecs, origins=[finalOrigins])

    return finalRecs, finalOrigins, userList


def generateJointList(userData, rewatch):
    userDicts = [{rec["recMedia"]["id"]: rec for rec in d["list"]} for d in userData]
    dictsUnion = {}
    for d in userDicts:
        dictsUnion = dictsUnion | d

    jointList = [value for (key, value) in dictsUnion.items()]
    origins = [d["origins"] for d in userData]
    for rec in jointList:
        score = 0
        for i, d in enumerate(userDicts):
            mediaId = rec["recMedia"]["id"]
            if "userRating" in origins[i].get(mediaId, {}):
                tempScore = list(origins[i][mediaId]["userRating"].values())[0]
                score += tempScore
            else:
                score += d.get(mediaId, {"recScore": 0})["recScore"]
        rec["recScore"] = score / len(userDicts)

    writeRecList(
        userNames=[d["userName"] for d in userData],
        finalRecs=[
            r
            for r in sorted(jointList, key=lambda x: -x["recScore"])
            if rewatch
            or not all(
                u.get(r["recMedia"]["id"], "") in {"COMPLETED", "REPEATING"}
                for u in [
                    {a["media"]["id"]: a["status"] for a in b}
                    for b in [d["userList"] for d in userData]
                ]
            )
        ],
        origins=origins,
    )


parser = argparse.ArgumentParser()
parser.add_argument(
    "userNames",
    help="Anilist username(s) of the user you wish to generate recommendations for",
    nargs="+",
)
parser.add_argument(
    "-r",
    "--refresh",
    help="Force refresh user data from anilist's servers. This may take a while. Note if no cached data exists for the given user, this will happen anyway",
    action="store_true",
)
parser.add_argument(
    "-s",
    "--studios",
    help="Use common animation studios in the recommendation algorithm. Note this will naturally push manga to the bottom of the list",
    action="store_true",
)
parser.add_argument(
    "-t",
    "--tags",
    help="Use common tags in the recommendation algorithm",
    action="store_true",
)
parser.add_argument(
    "-f",
    "--staff",
    help="Use common staff in the recommendation algorithm",
    action="store_true",
)
args = parser.parse_args()

angles = {
    "userRating": "rated it",
    "media": "if you liked:",
    "tags": "tags that may interest you:",
    "studios": "studios that may interest you:",
    "staff": "staff that may interest you:",
}

userData = [{"userName": n, "list": [], "origins": {}} for n in args.userNames]

for index, userName in enumerate(args.userNames):
    tempList, tempOrigins, tempUserList = getRecommendationList(
        userName=userName,
        useTags=args.tags,
        useStudios=args.studios,
        useStaff=args.staff,
        refresh=args.refresh,
    )
    userData[index]["list"] = tempList
    userData[index]["origins"] = tempOrigins
    userData[index]["userList"] = tempUserList

if len(args.userNames) > 1:
    generateJointList(userData=userData, rewatch=False)
