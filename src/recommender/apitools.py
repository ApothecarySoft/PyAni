import time
from gql import gql, Client
from gql.transport.httpx import HTTPXTransport
from gql.transport.exceptions import TransportQueryError, TransportServerError
import recommender.queries as queries
from recommender.cachefiles import save_user_data_file


def _fetch_data_for_chunk(client, media_type: str, chunk: int, user_name: str):
    print(f"fetching for chunk #{chunk}")
    query = gql(queries.user_list_query())
    result = None
    max_retries = 3
    retries = 0
    while result is None and retries <= max_retries:
        try:
            result = client.execute(
                query,
                variable_values={"name": user_name, "type": media_type, "chunk": chunk},
            )
        except TransportQueryError as e:
            error_code = e.errors[0]["status"]
            if error_code == 429:
                print(
                    f"got http {error_code}, server is rate limiting us. waiting to continue fetching data"
                )
                _countdown_timer_s(65)
            else:
                print(f"unhandled http error {error_code}. trying again in 10 seconds")
                _countdown_timer_s(10)
        except TransportServerError as e:
            print(e)
            _countdown_timer_s(10)
        finally:
            retries += 1
    if result is not None:
        lists = result["MediaListCollection"]["lists"]
        entries = [
            listEntries
            for currentList in lists
            for listEntries in currentList["entries"]
            if not currentList["isCustomList"]
        ]
        return entries, result["MediaListCollection"]["hasNextChunk"]
    else:
        raise ValueError()


def _countdown_timer_s(seconds: int):
    while seconds > 0:
        print(seconds)
        time.sleep(1)
        seconds -= 1


def _fetch_data_for_type(client, media_type: str, user_name: str):
    print(f"fetching data for type {media_type}")
    chunk_num = 0
    has_next_chunk = True
    entries = []
    while has_next_chunk:
        chunk_num += 1
        new_entries, has_next_chunk = _fetch_data_for_chunk(
            client=client, media_type=media_type, chunk=chunk_num, user_name=user_name
        )
        entries += new_entries

    return entries


def fetch_data_for_user(user_name: str):
    print(f"fetching data for user {user_name}")
    transport = HTTPXTransport(url="https://graphql.anilist.co", timeout=120)
    client = Client(transport=transport, fetch_schema_from_transport=False)
    entries = _fetch_data_for_type(
        client=client, media_type="ANIME", user_name=user_name
    )
    entries += _fetch_data_for_type(
        client=client, media_type="MANGA", user_name=user_name
    )

    save_user_data_file(user_name, entries)

    return entries
