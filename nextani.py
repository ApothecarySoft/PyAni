from gql import gql, Client
from gql.transport.httpx import HTTPXTransport
from gql.transport.exceptions import TransportQueryError
import queries
import time
import json
import argparse
import os
import math

def countdownTimer_s(seconds: int):
    while seconds > 0:
        print(seconds)
        time.sleep(1)
        seconds -= 1

def fetchDataForType(client, type: str):
    query = gql(queries.userListQuery(userName, type))
    result = client.execute(query)
    lists = result['MediaListCollection']['lists']
    # TODO add support for extra chunks
    entries = [y for x in lists for y in x['entries']]
    return entries

def fetchDataForUser(userName):
    transport = HTTPXTransport(url="https://graphql.anilist.co", timeout=120)
    client = Client(transport=transport, fetch_schema_from_transport=True)
    entries = fetchDataForType(client, "ANIME")
    entries += fetchDataForType(client, "MANGA")

    with open(f"{userName}-list.json", "w") as file:
        json.dump(entries, file)

    return entries

def loadDataFromFile(userFile):
    with open(userFile, 'r') as file:
        userList = json.load(file)

    return userList

def calculateMeanScore(userList):
    scoresTotal = 0
    scoresCount = 0

    for ratedAni in userList:
        score = ratedAni['score']
        if score <= 0:
            continue
        scoresTotal += score
        scoresCount += 1

    if scoresCount <= 0:
        return 50

    return scoresTotal / scoresCount

def calculateFirstPass(userList, meanScore):
    tagRatings = {}
    studioRatings = {}
    recommendations = {}

    for ratedAni in userList:
        score = ratedAni['score']
        if score <= 0:
            score = meanScore
        media = ratedAni['media']
        popularity = media['popularity']

        for tag in media['tags']:
            tagRank = tag['rank']
            tagId = tag['id']
            if tagId not in tagRatings:
                tagRatings[tagId] = {
                    'tag': tag,
                    'weightedScoreSum': score * tagRank,
                    'weightSum': tagRank
                }
            else:
                oldTagRating = tagRatings[tagId]
                tagRatings[tagId] = {
                    'tag': oldTagRating['tag'],
                    'weightedScoreSum': oldTagRating['weightedScoreSum'] + score * tagRank,
                    'weightSum': oldTagRating['weightSum'] + tagRank
                }

        for studio in media['studios']['nodes']:
            studioId = studio['id']
            if studioId not in studioRatings:
                studioRatings[studioId] = {
                    'studio': studio,
                    'scoreSum': score,
                    'studioOccurrence': 1
                }
            else:
                oldStudioRating = studioRatings[studioId]
                studioRatings[studioId] = {
                    'studio': oldStudioRating['studio'],
                    'scoreSum': oldStudioRating['scoreSum'] + score,
                    'studioOccurrence': oldStudioRating['studioOccurrence'] + 1
                }

        for rec in media['recommendations']['nodes']:
            rating = rec['rating']

            # ensure we don't count an opinion held by only one person (and don't count negative values)
            if rating < 1:
                continue

            recMedia = rec['mediaRecommendation']

            # ensure we do not try to process null values
            if not recMedia:
                continue

            recPopularity = recMedia['popularity']
            recId = recMedia['id']

            # ensure that we don't recommend things that the user has already rated
            if any(x['media']['id'] == recId for x in userList):
                continue

            normalizedRating = rating / (popularity + recPopularity) # normalize the rating to mitigate popularity bias
            scaledRating = score * normalizedRating # scale rating based on user's score

            # I feel like there's gotta be a more elegant way to do this
            if recId not in recommendations:
                recommendations[recId] = {
                    'recScore': scaledRating,
                    'recMedia': recMedia,
                    'recCount': 1
                }
            else:
                oldRecommendation = recommendations[recId]
                recommendations[recId] = {
                    'recScore': oldRecommendation['recScore'] + scaledRating,
                    'recMedia': oldRecommendation['recMedia'],
                    'recCount': oldRecommendation['recCount'] + 1
                }

    finalTagRatings = [{'tag': x['tag'], 'score': x['weightedScoreSum'] / x['weightSum']} for x in list(tagRatings.values()) if x['weightSum'] > 200]
    finalTagRatings.sort(key= lambda x: -x['score'])

    finalStudioRatings = [{'studio': x['studio'], 'score': x['scoreSum'] / x['studioOccurrence']} for x in list(studioRatings.values()) if x['studioOccurrence'] > 2]
    finalStudioRatings.sort(key= lambda x: -x['score'])

    finalRecList = [{'recScore': x['recScore'] / x['recCount'], 'recMedia': x['recMedia']} for x in list(recommendations.values()) if x['recCount'] > 1]

    return finalTagRatings, finalStudioRatings, finalRecList


def calculateSecondPass(tagRatings, studioRatings, recs, useTags, useStudios):
    finalRecs = []
    for rec in recs:
        tagTotal = 0
        tagCount = 0
        tags = rec['recMedia']['tags']
        tagRatings_d = {x['tag']['id']: x for x in tagRatings}
        if useTags:
            for tag in tags:
                if tag['id'] not in tagRatings_d:
                    continue
                tagTotal += tagRatings_d[tag['id']]['score'] * tag['rank']
                tagCount += 1
        tagScore = tagTotal / tagCount if tagCount > 0 else 0

        studioTotal = 0
        studioCount = 0
        studios = rec['recMedia']['studios']['nodes']
        studioRatings_d = {x['studio']['id']: x for x in studioRatings}
        if useStudios:
            for studio in studios:
                if studio['id'] not in studioRatings_d:
                    continue
                studioTotal += studioRatings_d[studio['id']]['score']
                studioCount += 1
        studioScore = studioTotal / studioCount if studioCount > 0 else 0
        
        finalRecs.append({
            'recScore': rec['recScore'] * (tagScore + 1) * (studioScore + 1),
            'recMedia': rec['recMedia']
        })
    finalRecs.sort(key=lambda x: -x['recScore'])
    return finalRecs


parser = argparse.ArgumentParser()
parser.add_argument("userName", help="Anilist username of the user you wish to generate recommendations for")
parser.add_argument("-r", "--refresh", help = "Force refresh user data from anilist's servers. This may take a while. Note if no cached data exists for the given user, this will happen anyway", action="store_true")
parser.add_argument("-s", "--studios", help = "Use common animation studios in the recommendation algorithm", action="store_true")
parser.add_argument("-t", "--tags", help = "Use common tags in the recommendation algorithm", action="store_true")
args = parser.parse_args()

userName = args.userName
userFile = f"{userName}-list.json"
userList = []

if args.refresh or not os.path.exists(userFile):
    userList = fetchDataForUser(userName)
else:
    userList = loadDataFromFile(userFile)

print(f"loaded {len(userList)} titles for {userName}")

meanScore = calculateMeanScore(userList)

print(f"{userName} gives a mean score of {meanScore}")

tags, studios, recommendations = calculateFirstPass(userList, meanScore)

finalRecs = calculateSecondPass(tags, studios, recommendations, args.tags, args.studios)

with open(f'{userName}-tags.txt', 'w', encoding="utf-8") as f:
    for tag in tags:
        print(f"{tag['tag']['name']}: {tag['score']}%", file=f)

with open(f'{userName}-studios.txt', 'w', encoding="utf-8") as f:
    for studio in studios:
        print(f"{studio['studio']['name']}: {studio['score']}%", file=f)


with open(f'{userName}-recs.txt', 'w', encoding="utf-8") as f:
    logBase = 2
    topScore = math.log(finalRecs[0]['recScore'] + 1, logBase)
    for rec in finalRecs:
        media = rec['recMedia']
        title = media['title']['english'] if media['title']['english'] else media['title']['userPreferred']
        mediaFormat = media['format']
        year = media['startDate']['year']
        #score = int(rec['recScore']) if rec['recScore'] > 1 else rec['recScore']
        score = round(math.log(rec['recScore'] + 1, logBase) / topScore * 100, 2)
        print(f"{title} ({mediaFormat}, {year}): {score}%", file=f)
