from gql import gql, Client
from gql.transport.httpx import HTTPXTransport
from gql.transport.exceptions import TransportQueryError
import queries
import time
import json
import argparse
import os

def countdownTimer_s(seconds: int):
    while seconds > 0:
        print(seconds)
        time.sleep(1)
        seconds -= 1

# def oldFetchData(userName):
#     transport = AIOHTTPTransport(url="https://graphql.anilist.co", ssl=True)
#     client = Client(transport=transport, fetch_schema_from_transport=True)

#     query = gql(queries.userQuery(userName, "1", "manga"))
#     result = client.execute(query)
#     scores = result['Page']['users'][0]['statistics']['manga']['scores']

#     query = gql(queries.userQuery(userName, "1", "anime"))
#     result = client.execute(query)
#     scores += result['Page']['users'][0]['statistics']['anime']['scores']

#     userList = []

#     for scoreBucket in scores:
#         score = scoreBucket['score']
#         for mediaId in scoreBucket['mediaIds']:
#             query = gql(queries.animeQuery(mediaId))
#             result = None
#             while result == None:
#                 try:
#                     result = client.execute(query)
#                 except TransportQueryError as e:
#                     errorCode = e.errors[0]['status']
#                     if errorCode == 429:
#                         print(f"got http {errorCode}, server is rate limiting us. waiting to continue fetching data")
#                         countdownTimer_s(61)
#                     else:
#                         print(f"unhandled http error {errorCode}. trying again in 10 seconds")
#                         countdownTimer_s(10)

#             print(f"Found {result['Media']['title']['userPreferred']}")
#             userList.append(
#                 {
#                     'score': score,
#                     'mediaId': mediaId,
#                     'mediaMeta': result
#                 }
#             )

#     with open(f"{userName}.json", "w") as file:
#         json.dump(userList, file)

#     return userList

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

    #populate userlist. use the same schema as before

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

    finalRecList = [{'recScore': x['recScore'] / x['recCount'], 'recMedia': x['recMedia']} for x in list(recommendations.values()) if x['recCount'] > 1]

    return finalTagRatings, finalRecList


def calculateSecondPass(tagRatings, recs):
    finalRecs = []
    for rec in recs:
        tagTotal = 0
        tagCount = 0
        tags = rec['recMedia']['tags']
        tagRatings_d = {x['tag']['id']: x for x in tagRatings}
        for tag in tags:
            if tag['id'] not in tagRatings_d:
                continue
            tagTotal += tagRatings_d[tag['id']]['score'] * tag['rank']
            tagCount += 1
        tagScore = tagTotal / tagCount if tagCount > 0 else 0
        finalRecs.append({
            'recScore': rec['recScore'] * tagScore,
            'recMedia': rec['recMedia']
        })
    finalRecs.sort(key=lambda x: -x['recScore'])
    return finalRecs


parser = argparse.ArgumentParser()
parser.add_argument("userName", help="Anilist username of the user you wish to generate recommendations for")
parser.add_argument("-r", "--refresh", help = "Force refresh user data from anilist's servers. This may take a while due to rate limiting. Note if no cached data exists for the given user, this will happen anyway", action="store_true")
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

tags, recommendations = calculateFirstPass(userList, meanScore)

finalRecs = calculateSecondPass(tags, recommendations)

with open(f'{userName}-tags.txt', 'w', encoding="utf-8") as f:
    for tag in tags:
        print(f"{tag['tag']['name']}: {tag['score']}%", file=f)


with open(f'{userName}-recs.txt', 'w', encoding="utf-8") as f:
    for rec in finalRecs:
        media = rec['recMedia']
        title = media['title']['english'] if rec['recMedia']['title']['english'] else rec['recMedia']['title']['userPreferred']
        format = media['format']
        year = media['seasonYear']
        print(f"{title} ({format}, {year}): {int(rec['recScore'])}", file=f)
