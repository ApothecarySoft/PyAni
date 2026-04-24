from recommender.algorithm import get_recommendation_list, generate_joint_list
from recommender.utils import sanitize_user_name, sanitize_user_names_list

class NotEnoughDataError(ValueError):
    pass


def get_watch_party(user_names, use, force_refresh=False):
    sanitized_user_names = sanitize_user_names_list(user_names)

    if len(sanitized_user_names) < 2:
        raise NotEnoughDataError()

    user_data = [
        {"userName": n, "list": [], "origins": {}, "userList": []}
        for n in sanitized_user_names
    ]

    for index, userName in enumerate(sanitized_user_names):
        temp_list, temp_origins, temp_user_list = get_recommendation_list(
            user_name=userName,
            use=use,
            refresh=force_refresh,
        )
        user_data[index]["list"] = temp_list
        user_data[index]["origins"] = temp_origins
        user_data[index]["userList"] = temp_user_list

    return generate_joint_list(user_data=user_data), user_data


def get_what_to_watch(user_name, use, force_refresh=False):
    sanitized_user_name = sanitize_user_name(user_name)

    temp_list, final_origins, temp_user_list = get_recommendation_list(
        user_name=sanitized_user_name,
        use=use,
        refresh=force_refresh,
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
