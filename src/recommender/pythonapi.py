import os.path
import sys
import traceback

from PySide6.QtCore import QThread, Signal

from recommender.algorithm import get_recommendation_list, generate_joint_list
from recommender.apitools import fetch_data_for_tag
from recommender.cachefiles import (
    load_tags_from_cache,
    latest_valid_cache_file_or_new,
    load_data_from_file,
    save_cache_file,
)
from recommender.utils import sanitize, sanitize_list


class NotEnoughDataError(ValueError):
    pass


class BaseThread(QThread):
    ErrorSignal = Signal(str)
    StatusSignal = Signal(str)
    ProgressSignal = Signal(int)
    ResultSignal = Signal(object)
    FinishSignal = Signal()
    CooldownSignal = Signal(str)
    CooldownProgressSignal = Signal(int)

    def __init__(self):
        super().__init__()
        self.result = None

    def run_func(self):
        pass

    def run(self):
        try:
            self.run_func()
        except Exception as e:
            print(traceback.format_exc(), file=sys.stderr)
            self.ErrorSignal.emit(str(e))
        finally:
            self.FinishSignal.emit()


class RecThread(BaseThread):
    def __init__(self, user_names, use, force_refresh=False):
        super().__init__()
        self.user_names = sanitize_list(user_names)
        self.use = use
        self.force_refresh = force_refresh

    def run_func(self):
        if len(self.user_names) > 1:
            self.result = _get_watch_party(
                user_names=self.user_names,
                use=self.use,
                progress_callback=self.ProgressSignal.emit,
                status_callback=self.StatusSignal.emit,
                force_refresh=self.force_refresh,
                cd_progress_callback=self.CooldownProgressSignal.emit,
                cd_callback=self.CooldownSignal.emit,
            )
        elif len(self.user_names) == 1:
            if self.user_names[0] == "":
                raise NotEnoughDataError("At least one username is required")
            self.result = _get_what_to_watch(
                user_name=self.user_names[0],
                use=self.use,
                progress_callback=self.ProgressSignal.emit,
                status_callback=self.StatusSignal.emit,
                force_refresh=self.force_refresh,
                cd_progress_callback=self.CooldownProgressSignal.emit,
                cd_callback=self.CooldownSignal.emit,
            )
        else:
            raise NotEnoughDataError("At least one username is required")
        self.ResultSignal.emit(self.result)


def _get_watch_party(
    user_names,
    use,
    progress_callback,
    status_callback,
    cd_progress_callback,
    cd_callback,
    force_refresh=False,
):
    sanitized_user_names = sanitize_list(user_names)

    if len(sanitized_user_names) < 2:
        raise NotEnoughDataError("At least two usernames are required")

    user_data = [
        {"userName": n, "list": [], "origins": {}, "userList": []}
        for n in sanitized_user_names
    ]
    props: dict[str, list[dict]] = {}

    num_steps = len(sanitized_user_names) + 1

    for index, userName in enumerate(sanitized_user_names):
        progress_callback(int((index / num_steps) * 100))
        (temp_list, temp_origins, temp_user_list,) = get_recommendation_list(
            user_name=userName,
            use=use,
            refresh=force_refresh,
            status_callback=status_callback,
            cd_progress_callback=cd_progress_callback,
            cd_callback=cd_callback,
        )
        user_data[index]["list"] = temp_list
        user_data[index]["origins"] = temp_origins
        user_data[index]["userList"] = temp_user_list

    progress_callback(len(sanitized_user_names) / num_steps * 100)

    final_list = generate_joint_list(user_data=user_data)

    progress_callback(100)

    return final_list, [d["origins"] for d in user_data]


def _get_what_to_watch(
    user_name,
    use,
    progress_callback,
    status_callback,
    cd_progress_callback,
    cd_callback,
    force_refresh=False,
):
    sanitized_user_name = sanitize(user_name)

    temp_list, final_origins, temp_user_list = get_recommendation_list(
        user_name=sanitized_user_name,
        use=use,
        refresh=force_refresh,
        status_callback=status_callback,
        cd_progress_callback=cd_progress_callback,
        cd_callback=cd_callback,
    )

    final_list = [
        rec
        for rec in sorted(temp_list, key=lambda x: -x["recScore"])
        if not {a["media"]["id"]: a["status"] for a in temp_user_list}.get(
            rec["recMedia"]["id"], ""
        )
        in {"COMPLETED", "REPEATING", "DROPPED"}
    ]

    return final_list, [final_origins]


class HunterThread(BaseThread):
    def __init__(self):
        super().__init__()

    def run_func(self):
        tags = load_tags_from_cache()

        all_prev_stuff = load_data_from_file(
            latest_valid_cache_file_or_new(
                item_name="all_prev_stuff", clean=True, expiration=False
            )
        )
        all_new_stuff = {}
        all_current_stuff = {}

        for index, raw_tag in enumerate(tags):
            clean_tag = raw_tag.lower().strip()

            file_name = latest_valid_cache_file_or_new(
                item_name=clean_tag, clean=False, expiration=False
            )
            tag_prev_stuff = {}
            if os.path.exists(file_name):
                tag_prev_stuff = load_data_from_file(file_name)

            tag_current_stuff = fetch_data_for_tag(
                tag=clean_tag,
                status_callback=self.StatusSignal.emit,
                cd_progress_callback=self.CooldownProgressSignal.emit,
                cd_callback=self.CooldownSignal.emit,
            )

            all_current_stuff |= tag_current_stuff

            latest_valid_cache_file_or_new(
                item_name=clean_tag, clean=True, expiration=True
            )

            tag_new_keys = set(tag_current_stuff.keys()) - set(tag_prev_stuff.keys())

            tag_new_stuff = {k: tag_current_stuff[k] for k in tag_new_keys}

            for k in tag_new_keys:
                if k not in all_new_stuff:
                    all_new_stuff[k] = tag_new_stuff[k]
                if all_prev_stuff is None or k not in all_prev_stuff:
                    all_new_stuff[k]["new"] = True
                    all_new_stuff[k].setdefault("new_tags", []).append(clean_tag)
                else:
                    all_new_stuff[k]["new"] = False
                    media_prev_tags = [t["name"] for t in all_prev_stuff[k]["tags"]]
                    if clean_tag not in media_prev_tags:
                        all_new_stuff[k].setdefault("new_tags", []).append(clean_tag)

            self.ProgressSignal.emit(index / (len(tags)) * 100)

        save_cache_file("all_prev_stuff", all_current_stuff)

        self.ResultSignal.emit(list(all_new_stuff.values()))
