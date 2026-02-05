import argparse

from algorithm import generateJointList, getRecommendationList
from output import writeRecList


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

userData = [{"userName": n, "list": [], "origins": {}} for n in args.userNames]

for index, userName in enumerate(args.userNames):
    tempList, tempOrigins, tempUserList = getRecommendationList(
        userName=userName,
        use={
            "tags": args.tags,
            "staff": args.staff,
            "studios": args.studios,
            "genres": args.genres,
            "decades": True,
        },
        refresh=args.refresh,
    )
    writeRecList(
        userNames=[userName],
        finalRecs=[
            rec
            for rec in sorted(tempList, key=lambda x: -x["recScore"])
            if not {a["media"]["id"]: a["status"] for a in tempUserList}.get(
                rec["recMedia"]["id"], ""
            )
            in {"COMPLETED", "REPEATING", "DROPPED", "CURRENT"}
        ],
        origins=[tempOrigins],
    )
    userData[index]["list"] = tempList
    userData[index]["origins"] = tempOrigins
    userData[index]["userList"] = tempUserList

if len(args.userNames) > 1:
    rewatch = False
    writeRecList(
        userNames=[d["userName"] for d in userData],
        finalRecs=[
            r
            for r in sorted(
                generateJointList(userData=userData), key=lambda x: -x["recScore"]
            )
            if rewatch
            or not all(
                u.get(r["recMedia"]["id"], "") in {"COMPLETED", "REPEATING", "DROPPED"}
                for u in [
                    {a["media"]["id"]: a["status"] for a in b}
                    for b in [d["userList"] for d in userData]
                ]
            )
        ],
        origins=[d["origins"] for d in userData],
    )
