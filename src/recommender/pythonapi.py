from recommender.algorithm import get_recommendation_list, generate_joint_list
from recommender.utils import sanitize_user_name, sanitize_user_names_list
from PySide6.QtCore import QThread, Signal


class NotEnoughDataError(ValueError):
    pass


class FetchThread(QThread):
    ErrorSignal = Signal(str)
    StatusSignal = Signal(str)
    ProgressSignal = Signal(int)
    ResultSignal = Signal(object)
    FinishSignal = Signal()

    def __init__(self, user_names, use, force_refresh=False):
        super().__init__()
        self.user_names = user_names
        self.use = use
        self.force_refresh = force_refresh
        self.result = None

    def run(self):
        try:
            if len(self.user_names) > 1:
                self.result = _get_watch_party(
                    user_names=self.user_names,
                    use=self.use,
                    progress_callback=self.ProgressSignal.emit,
                    status_callback=self.StatusSignal.emit,
                    force_refresh=self.force_refresh,
                )
            elif len(self.user_names) == 1:
                self.result = _get_what_to_watch(
                    user_name=self.user_names[0],
                    use=self.use,
                    progress_callback=self.ProgressSignal.emit,
                    status_callback=self.StatusSignal.emit,
                    force_refresh=self.force_refresh,
                )
            else:
                raise NotEnoughDataError("At least one username is required")
            self.ResultSignal.emit(self.result)
        except Exception as e:
            self.ErrorSignal.emit(str(e))
        finally:
            self.FinishSignal.emit()


def _get_watch_party(user_names, use, progress_callback, status_callback, force_refresh=False):
    sanitized_user_names = sanitize_user_names_list(user_names)

    if len(sanitized_user_names) < 2:
        raise NotEnoughDataError("At least two usernames are required")

    user_data = [
        {"userName": n, "list": [], "origins": {}, "userList": []}
        for n in sanitized_user_names
    ]

    num_steps = len(sanitized_user_names) + 1

    for index, userName in enumerate(sanitized_user_names):
        progress_callback(int((index / num_steps) * 100))
        temp_list, temp_origins, temp_user_list = get_recommendation_list(
            user_name=userName,
            use=use,
            refresh=force_refresh,
            status_callback=status_callback,
        )
        user_data[index]["list"] = temp_list
        user_data[index]["origins"] = temp_origins
        user_data[index]["userList"] = temp_user_list

    progress_callback(len(sanitized_user_names) / num_steps * 100)

    final_list = generate_joint_list(user_data=user_data)

    progress_callback(100)

    return final_list, user_data


def _get_what_to_watch(user_name, use, progress_callback, status_callback, force_refresh=False):
    sanitized_user_name = sanitize_user_name(user_name)

    temp_list, final_origins, temp_user_list = get_recommendation_list(
        user_name=sanitized_user_name,
        use=use,
        refresh=force_refresh,
        status_callback=status_callback,
    )

    final_list = [
        rec
        for rec in sorted(temp_list, key=lambda x: -x["recScore"])
        if not {a["media"]["id"]: a["status"] for a in temp_user_list}.get(
            rec["recMedia"]["id"], ""
        )
        in {"COMPLETED", "REPEATING", "DROPPED"}
    ]

    return final_list, final_origins
