import json

import recommender.constants as constants
from recommender.utils import get_english_title_or_user_preferred


def _generate_origin_string_for_type(media, origins, user_name=None):
    string = f"\t{user_name}\n" if user_name else ""
    for angle, text in constants.ANGLES.items():
        if media["id"] not in origins:
            continue
        if angle not in origins[media["id"]]:
            continue

        if angle == "userRating":
            user_rating = list(origins[media["id"]][angle].values())[0]
            if user_rating > 0:
                string += f"\tYou {text} {user_rating}%\n"
            continue

        string += f"\t{text} "
        for origin in origins[media["id"]][angle].values():
            if angle == "decades":
                string += f"{origin}s"
                return string + "\n"
            name = ""
            if "title" in origin:
                name = get_english_title_or_user_preferred(origin["title"])
            elif "name" in origin:
                name = (
                    origin["name"]
                    if isinstance(origin["name"], str)
                    else origin["name"]["userPreferred"]
                )
            elif type(origin) == str:
                name = origin
            string += f"{name}, "
        string = string[:-2] + "\n"
    return string


def write_rec_list(final_recs, origins, user_names: list[str]):
    anime_recs = [rec for rec in final_recs if rec["recMedia"]["type"] == "ANIME"]
    manga_recs = [rec for rec in final_recs if rec["recMedia"]["type"] == "MANGA"]
    _write_rec_list_for_type(anime_recs, origins, user_names, "ANIME")
    _write_rec_list_for_type(manga_recs, origins, user_names, "MANGA")


def _write_rec_list_for_type(recs_for_type, origins, user_names, media_type):
    full_name = ""
    for userName in user_names:
        full_name += f"{userName}-"
    filename = f"{full_name}{media_type.lower()}-recs"
    with open(f"{filename}.json", "w") as f:
        json.dump(recs_for_type, f)
    with open(f"{filename}.txt", "w", encoding="utf-8") as f:
        for rec in recs_for_type:

            media = rec["recMedia"]
            title = get_english_title_or_user_preferred(media["title"])
            media_format = media["format"]
            year = media["startDate"]["year"]
            score = rec["recScore"]

            print(f"{title} ({media_format}, {year}): {score}%", file=f)
            print(f"\thttps://anilist.co/{media_type}/{media['id']}", file=f)

            if "meanScore" in media:
                mean_score = media["meanScore"]
                print(f"\tother users rated it {mean_score}%\n", file=f)

            for i in range(len(user_names)):
                print(
                    _generate_origin_string_for_type(
                        media=media, origins=origins[i], user_name=user_names[i]
                    ),
                    file=f,
                )
