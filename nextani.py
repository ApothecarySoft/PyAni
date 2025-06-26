from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
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
        seconds = seconds - 1

def fetchData(userName):
    transport = AIOHTTPTransport(url="https://graphql.anilist.co", ssl=True)
    client = Client(transport=transport, fetch_schema_from_transport=True)

    query = gql(queries.userQuery(userName, "1"))

    result = client.execute(query)
    scores = result['Page']['users'][0]['statistics']['anime']['scores']

    userList = []

    for scoreBucket in scores:
        score = scoreBucket['score']
        for mediaId in scoreBucket['mediaIds']:
            query = gql(queries.animeQuery(mediaId))
            result = None
            while result == None:
                try:
                    result = client.execute(query)
                except TransportQueryError as e:
                    errorCode = e.errors[0]['status']
                    if errorCode == 429:
                        print(f"got http {errorCode}, server is rate limiting us. waiting to continue fetching data")
                        countdownTimer_s(61)
                    else:
                        print(f"unhandled http error {errorCode}. trying again in 10 seconds")
                        countdownTimer_s(10)

            print(f"Found {result['Media']['title']['userPreferred']}")
            userList.append(
                {
                    'score': score,
                    'mediaId': mediaId,
                    'mediaMeta': result
                }
            )

    with open(f"{userName}.json", "w") as file:
        json.dump(userList, file)

    return userList


def loadDataFromFile(userFile):
    with open(userFile, 'r') as file:
        userList = json.load(file)

    return userList


def calculateFirstPass(userList):
    tagRatings = {}
    recommendations = {}

    for ratedAni in userList:
        score = ratedAni['score']
        media = ratedAni['mediaMeta']['Media']
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
            if rating < 1:
                continue
            recMedia = rec['mediaRecommendation']
            if not recMedia:
                continue
            recPopularity = recMedia['popularity']
            recId = recMedia['id']

            # ensure that we don't recommend things that the user has already rated
            if any(x['mediaId'] == recId for x in userList):
                continue

            normalizedRating = rating / (popularity + recPopularity)
            scaledRating = score * normalizedRating
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

    tagRatingsList = list(tagRatings.values())
    tagRatingsList = [x for x in tagRatingsList if x['weightSum'] > 200]
    finalTagRatings = []

    for tagRating in tagRatingsList:
        finalTagScore = tagRating['weightedScoreSum'] / tagRating['weightSum']
        finalTagRatings.append({
            'tag': tagRating['tag'],
            'score': finalTagScore
        })

    finalTagRatings.sort(key= lambda x: -x['score'])

    recList = list(recommendations.values())
    tagRatingsList = [x for x in recList if x['recCount'] > 1]
    finalRecList = []
    for rec in tagRatingsList:
        finalRecList.append({
            'recScore': rec['recScore'] / rec['recCount'],
            'recMedia': rec['recMedia']
        })
    # finalRecList.sort(key= lambda x: -x['recScore'])

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
userFile = f"{userName}.json"
userList = []

if args.refresh or not os.path.exists(userFile):
    userList = fetchData(userName)
else:
    userList = loadDataFromFile(userFile)

print(f"loaded {len(userList)} rated titles for {userName}")

# keep a running list of tags and build a weighted % rating for each
tags, recommendations = calculateFirstPass(userList)

finalRecs = calculateSecondPass(tags, recommendations)

with open(f'{userName}-tags.txt', 'w', encoding="utf-8") as f:
    for tag in tags:
        print(f"{tag['tag']['name']}: {tag['score']}%", file=f)

# with open(f'{userName}.txt', 'w', encoding="utf-8") as f:
#     for rec in recommendations:
#         title = rec['recMedia']['title']['english'] if rec['recMedia']['title']['english'] else rec['recMedia']['title']['userPreferred']
#         print(f"{title}: {int(rec['recScore'])}", file=f)

with open(f'{userName}-recs.txt', 'w', encoding="utf-8") as f:
    for rec in finalRecs:
        title = rec['recMedia']['title']['english'] if rec['recMedia']['title']['english'] else rec['recMedia']['title']['userPreferred']
        print(f"{title}: {int(rec['recScore'])}", file=f)

# keep a running list of recommendations and build a weighted score from each
# omit any that were in the original list
# normalize rank against popularity

# do a second pass and weight all scores against the media's tags

# sort by final scores and output to text file
