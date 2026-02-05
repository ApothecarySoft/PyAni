import os
from cachefiles import latestValidUserFileOrNew, loadDataFromFile
from apitools import fetchDataForUser
import constants


def generateJointList(userData):
    userDicts = [{rec["recMedia"]["id"]: rec for rec in d["list"]} for d in userData]
    userScores = [
        {entry["media"]["id"]: entry["score"] for entry in d["userList"]}
        for d in userData
    ]
    dictsUnion = {}
    for d in userDicts:
        dictsUnion = dictsUnion | d

    jointList = [value for (key, value) in dictsUnion.items()]
    for rec in jointList:
        score = 0
        for i, d in enumerate(userDicts):
            mediaId = rec["recMedia"]["id"]
            userRating = userScores[i].get(mediaId) or 0
            if userRating > 0:
                score += userRating
            else:
                score += d.get(mediaId, {"recScore": 0})["recScore"]
        rec["recScore"] = score / len(userDicts)

    return jointList


def getRecommendationList(userName, use, refresh):
    if not userName:
        return None, None

    userFile = latestValidUserFileOrNew(userName=userName, clean=True)
    userList = []

    if refresh or not os.path.exists(userFile):
        userList = fetchDataForUser(userName)
    else:
        userList = loadDataFromFile(userFile)

    print(f"loaded {len(userList)} titles for {userName}")

    meanScore = _calculateMeanScore(userList)

    print(f"{userName} gives a mean score of {meanScore}")

    propertyRatings, recommendations, origins = _calculateInitial(
        userList=userList, meanScore=meanScore
    )

    finalRecs, finalOrigins = _calculateBiases(
        propertyRatings=propertyRatings,
        recs=recommendations,
        use=use,
        recOrigins=origins,
        userMean=meanScore,
    )

    if not finalRecs:
        return [], {}, userList

    exponent = 0.25
    topScore = (finalRecs[0]["recScore"] + 1) ** exponent

    for rec in finalRecs:
        rec["recScore"] = round(((rec["recScore"] + 1) ** exponent) / topScore * 100, 2)

    with open(f"{userName}-tags.txt", "w", encoding="utf-8") as f:
        for tag in propertyRatings["tags"]:
            print(f"{tag['tag']['name']}: {tag['score']}%", file=f)

    with open(f"{userName}-studios.txt", "w", encoding="utf-8") as f:
        for studio in propertyRatings["studios"]:
            print(f"{studio['studio']['name']}: {studio['score']}%", file=f)

    with open(f"{userName}-genres.txt", "w", encoding="utf-8") as f:
        for genre in propertyRatings["genres"]:
            print(f"{genre['genre']}: {genre['score']}%", file=f)

    with open(f"{userName}-decades.txt", "w", encoding="utf-8") as f:
        for decade in propertyRatings["decades"]:
            print(f"{decade['decade']}: {decade['score']}%", file=f)

    with open(f"{userName}-staff.txt", "w", encoding="utf-8") as f:
        for staff in propertyRatings["staff"]:
            print(
                f"{staff['staff']['name']['userPreferred']}: {staff['score']}%", file=f
            )

    return finalRecs, finalOrigins, userList


def _calculateMeanScore(userList):
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


def _calculateAveragePropertyScorePhase1(
    propertyList, propRatings, propType: str, score, weightName=None
):
    for prop in propertyList:
        propId = prop["id"] if isinstance(prop, dict) and "id" in prop else prop
        propRating = propRatings.setdefault(
            propId, {propType: prop, "sum": 0, "count": 0}
        )
        if weightName:
            weight = prop[weightName]
            propRating["sum"] += score * weight
            propRating["count"] += weight
        else:
            propRating["sum"] += score
            propRating["count"] += 1

    return propRatings


def _calculateAveragePropertyScorePhase2(minThreshold: int, propType: str, propRatings):
    finalPropRatings = [
        {propType: x[propType], "score": x["sum"] / x["count"]}
        for x in list(propRatings.values())
        if x["count"] > minThreshold
    ]
    finalPropRatings.sort(key=lambda x: -x["score"])

    return finalPropRatings


def _getDecadeFromYear(year):
    return (int(year) // 10) * 10


def _calculateInitial(userList, meanScore):
    angleKeys = list(constants.ANGLES.keys())
    decadeRatings = {}
    genreRatings = {}
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
        mediaMeanScore = (media.get("meanScore") or 100) * 2
        popularity = media["popularity"]

        if media.get("startDate") and media["startDate"].get("year"):
            decadeRatings = _calculateAveragePropertyScorePhase1(
                propertyList=[_getDecadeFromYear(media["startDate"]["year"])],
                propRatings=decadeRatings,
                propType="decade",
                score=score,
            )

        genreRatings = _calculateAveragePropertyScorePhase1(
            propertyList=media["genres"],
            propRatings=genreRatings,
            propType="genre",
            score=score,
        )

        studioRatings = _calculateAveragePropertyScorePhase1(
            propertyList=media["studios"]["nodes"],
            propRatings=studioRatings,
            propType="studio",
            score=score,
        )

        tagRatings = _calculateAveragePropertyScorePhase1(
            propertyList=media["tags"],
            propRatings=tagRatings,
            propType="tag",
            score=score,
            weightName="rank",
        )

        staffRatings = _calculateAveragePropertyScorePhase1(
            propertyList=media["staff"]["nodes"],
            propRatings=staffRatings,
            propType="staff",
            score=score,
        )

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

            recommendationRating = recommendations.setdefault(
                recId, {"recScore": 0, "recMedia": recMedia, "recCount": 0}
            )
            recommendationRating["recScore"] += scaledRating
            recommendationRating["recCount"] += 1

    finalDecadeRatings = _calculateAveragePropertyScorePhase2(
        minThreshold=0, propType="decade", propRatings=decadeRatings
    )

    finalGenreRatings = _calculateAveragePropertyScorePhase2(
        minThreshold=2, propType="genre", propRatings=genreRatings
    )
    finalTagRatings = _calculateAveragePropertyScorePhase2(
        minThreshold=200, propType="tag", propRatings=tagRatings
    )
    finalStudioRatings = _calculateAveragePropertyScorePhase2(
        minThreshold=2, propType="studio", propRatings=studioRatings
    )
    finalStaffRatings = _calculateAveragePropertyScorePhase2(
        minThreshold=2, propType="staff", propRatings=staffRatings
    )

    finalRecList = [
        {"recScore": x["recScore"] / x["recCount"], "recMedia": x["recMedia"]}
        for x in list(recommendations.values())
        if x["recCount"] > 1
    ]

    return (
        {
            "genres": finalGenreRatings,
            "tags": finalTagRatings,
            "studios": finalStudioRatings,
            "staff": finalStaffRatings,
            "decades": finalDecadeRatings,
        },
        finalRecList,
        origins,
    )


def _calculateBiases(
    propertyRatings,
    recs,
    use,
    recOrigins,
    userMean,
):
    angleKeys = list(constants.ANGLES.keys())
    finalRecs = []
    originThreshold = -0.2 + 0.853 * userMean + (1.49e-3 * (userMean ** 2))
    for rec in recs:
        recMedia = rec["recMedia"]

        decadeTotal = 0
        decadeCount = 0
        if (
            use["decades"]
            and recMedia.get("startDate")
            and recMedia["startDate"].get("year")
        ):
            decades = [_getDecadeFromYear(recMedia["startDate"]["year"])]
            decadeRatings_d = {x["decade"]: x for x in propertyRatings["decades"]}
            for decade in decades:
                if decade not in decadeRatings_d:
                    continue
                decadeTotal += decadeRatings_d[decade]["score"]
                decadeCount += 1
                if decadeRatings_d[decade]["score"] > originThreshold:
                    recOrigins.setdefault(recMedia["id"], {}).setdefault(
                        angleKeys[6], {}
                    )[decade] = decade
        decadeScore = decadeTotal / decadeCount if decadeCount > 0 else userMean

        genreTotal = 0
        genreCount = 0
        if use["genres"]:
            genres = recMedia["genres"]
            genreRatings_d = {x["genre"]: x for x in propertyRatings["genres"]}
            for genre in genres:
                if genre not in genreRatings_d:
                    continue
                genreTotal += genreRatings_d[genre]["score"]
                genreCount += 1
                if genreRatings_d[genre]["score"] > originThreshold:
                    recOrigins.setdefault(recMedia["id"], {}).setdefault(
                        angleKeys[5], {}
                    )[genre] = genre
        genreScore = genreTotal / genreCount if genreCount > 0 else userMean

        tagTotal = 0
        tagCount = 0
        if use["tags"]:
            tags = recMedia["tags"]
            tagRatings_d = {x["tag"]["id"]: x for x in propertyRatings["tags"]}
            for tag in tags:
                tagId = tag["id"]
                if tagId not in tagRatings_d:
                    continue
                tagTotal += tagRatings_d[tagId]["score"] * tag["rank"]
                tagCount += tag["rank"]
                if tagRatings_d[tagId]["score"] > originThreshold:
                    recOrigins.setdefault(recMedia["id"], {}).setdefault(
                        angleKeys[2], {}
                    )[tagId] = tag
        tagScore = tagTotal / tagCount if tagCount > 0 else userMean

        studioTotal = 0
        studioCount = 0
        if use["studios"]:
            studios = recMedia["studios"]["nodes"]
            studioRatings_d = {x["studio"]["id"]: x for x in propertyRatings["studios"]}
            for studio in studios:
                studioId = studio["id"]
                if studioId not in studioRatings_d:
                    continue
                studioTotal += studioRatings_d[studioId]["score"]
                studioCount += 1
                if studioRatings_d[studioId]["score"] > originThreshold:
                    recOrigins.setdefault(recMedia["id"], {}).setdefault(
                        angleKeys[3], {}
                    )[studioId] = studio
        studioScore = studioTotal / studioCount if studioCount > 0 else userMean

        staffTotal = 0
        staffCount = 0
        if use["staff"]:
            staffs = recMedia["staff"]["nodes"]
            staffRatings_d = {x["staff"]["id"]: x for x in propertyRatings["staff"]}
            for staff in staffs:
                staffId = staff["id"]
                if staffId not in staffRatings_d:
                    continue
                staffTotal += staffRatings_d[staffId]["score"]
                staffCount += 1
                if staffRatings_d[staffId]["score"] > originThreshold:
                    recOrigins.setdefault(recMedia["id"], {}).setdefault(
                        angleKeys[4], {}
                    )[staffId] = staff
        staffScore = staffTotal / staffCount if staffCount > 0 else userMean

        finalRecs.append(
            {
                "recScore": rec["recScore"]
                * (tagScore)
                * (studioScore)
                * (genreScore)
                * (staffScore)
                * (decadeScore),
                "recMedia": recMedia,
            }
        )
    finalRecs.sort(key=lambda x: -x["recScore"])

    return finalRecs, recOrigins
