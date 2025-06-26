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
tagRatings = {}
recommendations = {}

for ratedAni in userList:
    score = ratedAni['score']
    media = ratedAni['mediaMeta']['Media']
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

tagRatingsList = list(tagRatings.values())
tagRatingsList = [x for x in tagRatingsList if x['weightSum'] > 100]
finalTagRatings = []

for tagRating in tagRatingsList:
    finalTagScore = tagRating['weightedScoreSum'] / tagRating['weightSum']
    finalTagRatings.append({
        'name': tagRating['tag']['name'],
        'score': finalTagScore
    })

finalTagRatings.sort(key= lambda x: -x['score'])

for finalRating in finalTagRatings:
    print(f"{finalRating['name']}: {finalRating['score']}%")

# keep a running list of recommendations and build a weighted score from each
# omit any that were in the original list
# normalize rank against popularity

# do a second pass and weight all scores against the media's tags

# sort by final scores and output to text file
