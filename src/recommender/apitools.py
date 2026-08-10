import time
from dataclasses import dataclass
from typing import Any, Callable

from gql import gql, Client
from gql.transport.httpx import HTTPXTransport
from gql.transport.exceptions import TransportQueryError, TransportServerError
import recommender.queries as queries
from database.db import LadybugManager
from recommender.cachefiles import save_cache_file


def _do_request(variable_values, query, callbacks) -> dict[str, Any] | None:
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
                        callbacks,
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
                        callbacks,
                        f"unhandled http error {error_code}. trying again in 10 seconds",
                    )
            else:
                raise RuntimeError(f"Unknown error: {e}")
        except TransportServerError as e:
            _countdown_timer_s(10, callbacks, str(e))
        finally:
            retries += 1
    return result


def refresh(username: str, force: bool, callbacks):
    db = LadybugManager()
    entries = None
    if not force and db.is_user_fresh(username):
        pass
        # entries = (get them from the database)
    if entries is None:
        entries = _fetch_user_list(username, callbacks)

    for entry in entries:
        if force or not db.is_media_fresh(entry['media']['id']):
            pass
            # fetch media

    # go through recommendations and relations (pull media from db based on ids in entries) and fetch any missing or outdated media
    # Media, Property nodes and MediaProperty relations can be stored on media fetch
    # Relation and Rec relations can be stored
    # User nodes should be stored here
    # then UserMedia, Follows relations can be stored here
    # UserProperty relations have to be stored when they're calculated in algorithm.py


def _fetch_tag_data_for_page(page: int, tag: str, callbacks):
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
        callbacks=callbacks,
    )
    if result is not None:
        data_page = result["Page"]
        return data_page["media"], data_page["pageInfo"]["hasNextPage"]
    else:
        raise RuntimeError(f"No result. Unknown reason.")


def _countdown_timer_s(seconds: int, callbacks, reason):
    callbacks.cd(reason)
    while seconds > 0:
        print(seconds)
        callbacks.cd_progress(seconds)
        time.sleep(1)
        seconds -= 1


def _fetch_user_list_for_type(media_type: str, user_name: str, callbacks):
    print(f"fetching data for type {media_type}")
    query = gql(queries.user_list_query())
    result = _do_request(
        variable_values={"name": user_name, "type": media_type},
        query=query,
        callbacks=callbacks,
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


def fetch_data_for_tag(tag: str, status_callback, callbacks):
    print(f"fetching data for tag {tag}")
    status_callback(f"Fetching data for tag: {tag}")
    page_num = 0
    has_next_page = True
    entries = []

    while has_next_page:
        page_num += 1
        new_entries, has_next_page = _fetch_tag_data_for_page(
            page=page_num, tag=tag, callbacks=callbacks
        )
        entries += new_entries
    entries = {str(x["id"]): x for x in entries}
    save_cache_file(tag, entries)

    return entries


class NestedProgressCallback:
    def __init__(self, callback_function: Callable[[int, int], None], layer: int, sub_job_size: int = 1):
        self.callback_function: Callable[[int, int], None] = callback_function
        self.layer: int = layer
        self.sub_job_size: int = sub_job_size
        self._progress: float = 0.0

    def set_progress(self, progress: int):
        self._progress = progress
        self.callback_function(progress, self.layer)

    def increment_progress(self):
        self._progress += 100.0 / self.sub_job_size
        self.callback_function(int(self._progress), self.layer)

    def make_sub_job(self, sub_job_size=1):
        return NestedProgressCallback(
            self.callback_function, self.layer + 1, sub_job_size
        )


class NestedStatusCallback:
    def __init__(self, callback_function: Callable[[str, int], None], layer: int):
        self.callback_function: Callable[[str, int], None] = callback_function
        self.layer: int = layer

    def __call__(self, status: str):
        self.callback_function(status, self.layer)

    def make_sub_job(self):
        return NestedStatusCallback(self.callback_function, self.layer + 1)


@dataclass
class CallbacksStruct:
    progress: NestedProgressCallback
    status: NestedStatusCallback
    cd: Callable
    cd_progress: Callable

    def make_sub_job(self, sub_job_size: int = 1):
        return CallbacksStruct(
            self.progress.make_sub_job(sub_job_size),
            self.status.make_sub_job(),
            self.cd,
            self.cd_progress,
        )


def _fetch_user_list(user_name: str, callbacks):
    print(f"fetching data for user {user_name}")
    entries = _fetch_user_list_for_type(
        media_type="ANIME", user_name=user_name, callbacks=callbacks
    )
    entries += _fetch_user_list_for_type(
        media_type="MANGA", user_name=user_name, callbacks=callbacks
    )

    # create or update user
    return entries
