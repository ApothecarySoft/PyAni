import time
from typing import Any

from gql import gql, Client
from gql.transport.httpx import HTTPXTransport
from gql.transport.exceptions import TransportQueryError, TransportServerError
import recommender.queries as queries
from database.db import LadybugManager
from recommender.cachefiles import save_cache_file


def _do_request(
    variable_values, query, cd_progress_callback, cd_callback
) -> dict[str, Any] | None:
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
                    _countdown_timer_s(
                        61,
                        cd_progress_callback,
                        cd_callback,
                        f"got http {error_code}, server is rate limiting us. waiting to continue fetching data",
                    )
                elif error_code == 403:
                    raise RuntimeError(f"Query failed: {error_message}")
                elif error_code == 404:
                    raise RuntimeError(
                        f"Query failed. {variable_values.get('name', variable_values.get('tag'))}: {error_message}"
                    )
                else:
                    _countdown_timer_s(
                        10,
                        cd_progress_callback,
                        cd_callback,
                        f"unhandled http error {error_code}. trying again in 10 seconds",
                    )
            else:
                raise RuntimeError(f"Unknown error: {e}")
        except TransportServerError as e:
            _countdown_timer_s(10, cd_progress_callback, cd_callback, str(e))
        finally:
            retries += 1
    return result


def _fetch_tag_data_for_page(page: int, tag: str, cd_progress_callback, cd_callback):
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
        cd_progress_callback=cd_progress_callback,
        cd_callback=cd_callback,
    )
    if result is not None:
        data_page = result["Page"]
        return data_page["media"], data_page["pageInfo"]["hasNextPage"]
    else:
        raise RuntimeError(f"No result. Unknown reason.")


def _countdown_timer_s(seconds: int, cd_progress_callback, cd_callback, reason):
    cd_callback(reason)
    while seconds > 0:
        print(seconds)
        cd_progress_callback(seconds)
        time.sleep(1)
        seconds -= 1


def _fetch_user_list_for_type(
    media_type: str, user_name: str, status_callback, cd_progress_callback, cd_callback
):
    print(f"fetching data for type {media_type}")
    db = LadybugManager()
    query = gql(queries.user_list_query())
    result = _do_request(
        variable_values={"name": user_name, "type": media_type},
        query=query,
        cd_progress_callback=cd_progress_callback,
        cd_callback=cd_callback,
    )
    if result is not None:
        lists = result["MediaListCollection"]["lists"]
        entries = [
            list_entry
            for current_list in lists
            for list_entry in current_list["entries"]
            if not current_list["isCustomList"]
        ]
        return entries
    else:
        raise ValueError("No result. Unknown reason.")


def fetch_data_for_tag(tag: str, status_callback, cd_progress_callback, cd_callback):
    print(f"fetching data for tag {tag}")
    status_callback(f"Fetching data for tag: {tag}")
    page_num = 0
    has_next_page = True
    entries = []

    while has_next_page:
        page_num += 1
        new_entries, has_next_page = _fetch_tag_data_for_page(
            page=page_num,
            tag=tag,
            cd_progress_callback=cd_progress_callback,
            cd_callback=cd_callback,
        )
        entries += new_entries
    entries = {str(x["id"]): x for x in entries}
    save_cache_file(tag, entries)

    return entries


class RecursiveProgressCallback:
    def __init__(self, callback_object, sub_job_size: int = 1):
        self._callback_function = callback_object
        self.sub_job_size = sub_job_size
        self._progress = 0

    def __call__(self, progress):
        self._callback_function(progress / self.sub_job_size)


def _update_media_info_for_list(
    user_name: str,
    entries,
    status_callback,
):
    for entry in entries:
        media_id = entry["media"]["id"]
        fetch_data_for_media



def _store_user_media_relations(user_name, entries):
    pass


def fetch_user_list(
    user_name: str, status_callback, cd_progress_callback, cd_callback
):
    print(f"fetching data for user {user_name}")
    entries = _fetch_user_list_for_type(
        media_type="ANIME",
        user_name=user_name,
        status_callback=status_callback,
        cd_progress_callback=cd_progress_callback,
        cd_callback=cd_callback,
    )
    entries += _fetch_user_list_for_type(
        media_type="MANGA",
        user_name=user_name,
        status_callback=status_callback,
        cd_progress_callback=cd_progress_callback,
        cd_callback=cd_callback,
    )

    _update_media_info_for_list(user_name, entries, RecursiveProgressCallback(status_callback))
    _store_user_media_relations(user_name, entries)

    save_cache_file(user_name, entries)

    return entries
