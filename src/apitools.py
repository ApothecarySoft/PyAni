import time
from gql import gql, Client
from gql.transport.httpx import HTTPXTransport
from gql.transport.exceptions import TransportQueryError
import queries
from cachefiles import saveUserDataFile


def _fetchDataForChunk(client, mediaType: str, chunk: int, userName: str):
    print(f"fetching for chunk #{chunk}")
    query = gql(
        queries.userListQuery()
    )
    result = None
    MAX_RETRIES = 3
    retries = 0
    while result == None and retries <= MAX_RETRIES:
        try:
            result = client.execute(query, variable_values = {"name": userName, "type": mediaType, "chunk": chunk})
        except TransportQueryError as e:
            errorCode = e.errors[0]["status"]
            retries += 1
            if errorCode == 429:
                print(
                    f"got http {errorCode}, server is rate limiting us. waiting to continue fetching data"
                )
                _countdownTimer_s(65)
            else:
                print(f"unhandled http error {errorCode}. trying again in 10 seconds")
                _countdownTimer_s(10)
    lists = result["MediaListCollection"]["lists"]
    entries = [
        listEntries
        for currentList in lists
        for listEntries in currentList["entries"]
        if not currentList["isCustomList"]
    ]
    return entries, result["MediaListCollection"]["hasNextChunk"]


def _countdownTimer_s(seconds: int):
    while seconds > 0:
        print(seconds)
        time.sleep(1)
        seconds -= 1


def _fetchDataForType(client, mediaType: str, userName: str):
    print(f"fetching data for type {mediaType}")
    chunkNum = 0
    hasNextChunk = True
    entries = []
    while hasNextChunk:
        chunkNum += 1
        newEntries, hasNextChunk = _fetchDataForChunk(
            client=client, mediaType=mediaType, chunk=chunkNum, userName=userName
        )
        entries += newEntries

    return entries


def fetchDataForUser(userName: str):
    print(f"fetching data for user {userName}")
    transport = HTTPXTransport(url="https://graphql.anilist.co", timeout=120)
    client = Client(transport=transport, fetch_schema_from_transport=False)
    entries = _fetchDataForType(client=client, mediaType="ANIME", userName=userName)
    entries += _fetchDataForType(client=client, mediaType="MANGA", userName=userName)

    saveUserDataFile(userName, entries)

    return entries
