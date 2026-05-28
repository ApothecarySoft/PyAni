import time
from gql import gql, Client
from gql.transport.httpx import HTTPXTransport
from gql.transport.exceptions import TransportQueryError, TransportServerError
import recommender.queries as queries
from recommender.cachefiles import save_cache_file


def _do_request(variable_values, query, status_callback):
    result = None
    max_retries = 3
    retries = 0
    client = Client(
        transport=HTTPXTransport(url="https://graphql.anilist.co", timeout=120),
        fetch_schema_from_transport=False,
    )
    while result is None and retries <= max_retries:
        try:
            result = client.execute(
                query,
                variable_values=variable_values,
            )
        except TransportQueryError as e:
            if e.errors is not None:
                error = e.errors[0]
                error_code = error["status"]
                error_message = error["message"]
                if error_code == 429:
                    print(
                        f"got http {error_code}, server is rate limiting us. waiting to continue fetching data"
                    )
                    _countdown_timer_s(
                        61, status_callback, "Server is busy. Please wait."
                    )
                elif error_code == 403:
                    raise RuntimeError(f"Query failed: {error_message}")
                elif error_code == 404:
                    raise RuntimeError(
                        f"Query failed. {variable_values.get('name', variable_values.get('tag'))}: {error_message}"
                    )
                else:
                    print(
                        f"unhandled http error {error_code}. trying again in 10 seconds"
                    )
                    _countdown_timer_s(
                        10,
                        status_callback,
                        f"Unhandled http error {error_code}. Trying again in 10 seconds.",
                    )
            else:
                raise RuntimeError(f"Unknown error: {e}")
        except TransportServerError as e:
            print(e)
            _countdown_timer_s(
                10,
                status_callback,
                f"Unhandled error: {e}. Trying again in 10 seconds.",
            )
        finally:
            retries += 1
    return result


def _fetch_tag_data_for_page(page: int, tag: str, status_callback):
    print(f"fetching for page #{page}")
    query = gql(queries.hunter_query)
    result = _do_request(
        variable_values={
            "tag": tag,
            "sort": "ID",
            "status": ["NOT_YET_RELEASED"],
            "page": page,
        },
        query=query,
        status_callback=status_callback,
    )
    if result is not None:
        data_page = result["Page"]
        return data_page["media"], data_page["pageInfo"]["hasNextPage"]
    else:
        raise RuntimeError(f"No result. Unknown reason.")


def _fetch_user_data_for_chunk(
    media_type: str, chunk: int, user_name: str, status_callback
):
    print(f"fetching for chunk #{chunk}")
    query = gql(queries.user_list_query())
    result = _do_request(
        variable_values={"name": user_name, "type": media_type, "chunk": chunk},
        query=query,
        status_callback=status_callback,
    )
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
        raise ValueError("No result. Unknown reason.")


def _countdown_timer_s(seconds: int, status_callback, reason: str = ""):
    while seconds > 0:
        print(seconds)
        status_callback(f"{reason} ({seconds} seconds remaining)")
        time.sleep(1)
        seconds -= 1


def _fetch_data_for_type(media_type: str, user_name: str, status_callback):
    print(f"fetching data for type {media_type}")
    chunk_num = 0
    has_next_chunk = True
    entries = []
    while has_next_chunk:
        chunk_num += 1
        status_callback(
            f"Fetching {media_type.lower()} data for {user_name} (chunk {chunk_num})"
        )
        new_entries, has_next_chunk = _fetch_user_data_for_chunk(
            media_type=media_type,
            chunk=chunk_num,
            user_name=user_name,
            status_callback=status_callback,
        )
        entries += new_entries

    return entries


def fetch_data_for_tag(tag: str, status_callback):
    print(f"fetching data for tag {tag}")
    status_callback(f"Fetching data for tag: {tag}")
    page_num = 0
    has_next_page = True
    entries = []

    while has_next_page:
        page_num += 1
        new_entries, has_next_page = _fetch_tag_data_for_page(
            page=page_num, tag=tag, status_callback=status_callback
        )
        entries += new_entries
    entries = {str(x["id"]): x for x in entries}
    save_cache_file(tag, entries)

    return entries


def fetch_data_for_user(user_name: str, status_callback):
    print(f"fetching data for user {user_name}")
    entries = _fetch_data_for_type(
        media_type="ANIME", user_name=user_name, status_callback=status_callback
    )
    entries += _fetch_data_for_type(
        media_type="MANGA", user_name=user_name, status_callback=status_callback
    )

    save_cache_file(user_name, entries)

    return entries
