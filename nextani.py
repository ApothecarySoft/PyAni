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
                        countdownTimer_s(65)
                    print(f"unhandled http error {errorCode}. trying again in 10 seconds")
                    countdownTimer_s(10)
            print(result)
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

print(f"loaded user list of size {len(userList)}")