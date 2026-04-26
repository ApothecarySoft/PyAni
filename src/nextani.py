import argparse

from recommender.algorithm import generate_joint_list, get_recommendation_list
from recommender.output import write_rec_list
from recommender.utils import sanitize_user_name


def run(user_names, use):
    sanitized_user_names = [sanitize_user_name(n) for n in user_names]

    user_data = [
        {"userName": n, "list": [], "origins": {}} for n in sanitized_user_names
    ]

    for index, userName in enumerate(sanitized_user_names):
        temp_list, temp_origins, temp_user_list = get_recommendation_list(
            user_name=userName,
            use=use,
            refresh=args.refresh,
        )
        write_rec_list(
            user_names=[userName],
            final_recs=[
                rec
                for rec in sorted(temp_list, key=lambda x: -x["recScore"])
                if not {a["media"]["id"]: a["status"] for a in temp_user_list}.get(
                    rec["recMedia"]["id"], ""
                )
                in {"COMPLETED", "REPEATING", "DROPPED"}
            ],
            origins=[temp_origins],
        )
        user_data[index]["list"] = temp_list
        user_data[index]["origins"] = temp_origins
        user_data[index]["userList"] = temp_user_list

    if len(sanitized_user_names) > 1:
        write_rec_list(
            user_names=[d["userName"] for d in user_data],
            final_recs=generate_joint_list(user_data=user_data),
            origins=[d["origins"] for d in user_data],
        )


parser = argparse.ArgumentParser()
parser.add_argument(
    "userNames",
    help="Anilist username(s) of the user you wish to generate recommendations for",
    nargs="+",
)
parser.add_argument(
    "-r",
    "--refresh",
    help="Force refresh user data from anilist's servers. This may take a while. Note if no cached data exists for the given user, this will happen anyway",
    action="store_true",
)
parser.add_argument(
    "-s",
    "--studios",
    help="Use common animation studios in the recommendation algorithm. Note this will naturally push manga to the bottom of the list",
    action="store_true",
)
parser.add_argument(
    "-t",
    "--tags",
    help="Use common tags in the recommendation algorithm",
    action="store_true",
)
parser.add_argument(
    "-f",
    "--staff",
    help="Use common staff in the recommendation algorithm",
    action="store_true",
)
parser.add_argument(
    "-g",
    "--genres",
    help="Use common genres in the recommendation algorithm",
    action="store_true",
)
args = parser.parse_args()

run(
    args.userNames,
    use={
        "tags": args.tags,
        "staff": args.staff,
        "studios": args.studios,
        "genres": args.genres,
        "decades": True,
    },
)
