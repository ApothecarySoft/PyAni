import os
from recommender.cachefiles import latest_valid_user_file_or_new, load_data_from_file
from recommender.apitools import fetch_data_for_user
import recommender.constants as constants


def generate_joint_list(user_data):
    user_dicts = [{rec["recMedia"]["id"]: rec for rec in d["list"]} for d in user_data]
    user_scores = [
        {entry["media"]["id"]: entry["score"] for entry in d["userList"]}
        for d in user_data
    ]
    dicts_union = {}
    for d in user_dicts:
        dicts_union = dicts_union | d

    joint_list = [value for (key, value) in dicts_union.items()]
    for rec in joint_list:
        score = 0
        for i, d in enumerate(user_dicts):
            media_id = rec["recMedia"]["id"]
            user_rating = user_scores[i].get(media_id) or 0
            if user_rating > 0:
                score += user_rating
            else:
                score += d.get(media_id, {"recScore": 0})["recScore"]
        rec["recScore"] = score / len(user_dicts)

    return [
        r
        for r in sorted(joint_list, key=lambda x: -x["recScore"])
        if not all(
            u.get(r["recMedia"]["id"], "") in {"COMPLETED", "REPEATING", "DROPPED"}
            for u in [
                {a["media"]["id"]: a["status"] for a in b}
                for b in [d["userList"] for d in user_data]
            ]
        )
    ]


def get_recommendation_list(user_name, use, refresh, status_callback):
    if not user_name:
        return None, None

    user_file = latest_valid_user_file_or_new(user_name=user_name, clean=True)

    if refresh or not os.path.exists(user_file):
        user_list = fetch_data_for_user(user_name, status_callback=status_callback)
    else:
        user_list = load_data_from_file(user_file)

    print(f"loaded {len(user_list)} titles for {user_name}")
    status_callback(f"Loaded {len(user_list)} titles for {user_name}")
    mean_score = _calculate_mean_score(user_list)

    print(f"{user_name} gives a mean score of {mean_score}")

    property_ratings, recommendations, origins = _calculate_initial(
        user_list=user_list, mean_score=mean_score
    )

    final_recs, final_origins = _calculate_biases(
        property_ratings=property_ratings,
        recs=recommendations,
        use=use,
        rec_origins=origins,
        user_mean=mean_score,
    )

    if not final_recs:
        return [], {}, user_list

    exponent = 0.16
    top_score = (final_recs[0]["recScore"] + 1) ** exponent

    for rec in final_recs:
        rec["recScore"] = round(
            ((rec["recScore"] + 1) ** exponent) / top_score * 100, 2
        )

    with open(f"{user_name}-tags.txt", "w", encoding="utf-8") as f:
        for tag in property_ratings["tags"]:
            print(f"{tag['tag']['name']}: {tag['score']}%", file=f)

    with open(f"{user_name}-studios.txt", "w", encoding="utf-8") as f:
        for studio in property_ratings["studios"]:
            print(f"{studio['studio']['name']}: {studio['score']}%", file=f)

    with open(f"{user_name}-genres.txt", "w", encoding="utf-8") as f:
        for genre in property_ratings["genres"]:
            print(f"{genre['genre']}: {genre['score']}%", file=f)

    with open(f"{user_name}-decades.txt", "w", encoding="utf-8") as f:
        for decade in property_ratings["decades"]:
            print(f"{decade['decade']}: {decade['score']}%", file=f)

    with open(f"{user_name}-staff.txt", "w", encoding="utf-8") as f:
        for staff in property_ratings["staff"]:
            print(
                f"{staff['staff']['name']['userPreferred']}: {staff['score']}%", file=f
            )

    return final_recs, final_origins, user_list


def _calculate_mean_score(user_list):
    scores_total = 0
    scores_count = 0

    for ratedAni in user_list:
        score = ratedAni["score"]
        if score <= 0:
            continue
        scores_total += score
        scores_count += 1

    if scores_count <= 0:
        return 50

    return scores_total / scores_count


def _calculate_average_property_score_phase_1(
    prop_list, prop_ratings, prop_type: str, score, weight_name=None
):
    for prop in prop_list:
        prop_id = prop["id"] if isinstance(prop, dict) and "id" in prop else prop
        prop_rating = prop_ratings.setdefault(
            prop_id, {prop_type: prop, "sum": 0, "count": 0}
        )
        if weight_name:
            weight = prop[weight_name]
            prop_rating["sum"] += score * weight
            prop_rating["count"] += weight
        else:
            prop_rating["sum"] += score
            prop_rating["count"] += 1

    return prop_ratings


def _calculate_average_property_score_phase_2(
    min_threshold: int, prop_type: str, prop_ratings
):
    final_prop_ratings = [
        {prop_type: x[prop_type], "score": x["sum"] / x["count"]}
        for x in list(prop_ratings.values())
        if x["count"] > min_threshold
    ]
    final_prop_ratings.sort(key=lambda x: -x["score"])

    return final_prop_ratings


def _get_decade_from_year(year):
    return (int(year) // 10) * 10


def _calculate_initial(user_list, mean_score):
    angle_keys = list(constants.ANGLES.keys())
    decade_ratings = {}
    genre_ratings = {}
    tag_ratings = {}
    studio_ratings = {}
    staff_ratings = {}
    recommendations = {}
    origins = {}

    for ratedAni in user_list:
        score = ratedAni["score"]
        status = ratedAni["status"] if "status" in ratedAni.keys() else ""
        if score <= 0:
            if status == "DROPPED":
                score = 25
            else:
                score = mean_score
        media = ratedAni["media"]
        media_mean_score = media.get("meanScore") or 100
        popularity = media["popularity"]

        if media.get("startDate") and media["startDate"].get("year"):
            decade_ratings = _calculate_average_property_score_phase_1(
                prop_list=[_get_decade_from_year(media["startDate"]["year"])],
                prop_ratings=decade_ratings,
                prop_type="decade",
                score=score,
            )

        genre_ratings = _calculate_average_property_score_phase_1(
            prop_list=media["genres"],
            prop_ratings=genre_ratings,
            prop_type="genre",
            score=score,
        )

        studio_ratings = _calculate_average_property_score_phase_1(
            prop_list=media["studios"]["nodes"],
            prop_ratings=studio_ratings,
            prop_type="studio",
            score=score,
        )

        tag_ratings = _calculate_average_property_score_phase_1(
            prop_list=media["tags"],
            prop_ratings=tag_ratings,
            prop_type="tag",
            score=score,
            weight_name="rank",
        )

        staff_ratings = _calculate_average_property_score_phase_1(
            prop_list=media["staff"]["nodes"],
            prop_ratings=staff_ratings,
            prop_type="staff",
            score=score,
        )

        for rec in media["recommendations"]["nodes"]:
            rating = rec["rating"]

            # ensure we don't count an opinion held by only one person (and don't count negative values)
            if rating < 1:
                continue

            rec_media = rec["mediaRecommendation"]

            # ensure we do not try to process null values
            if not rec_media:
                continue

            rec_popularity = rec_media["popularity"]
            rec_id = rec_media["id"]

            # ensure that we don't recommend things that the user already has on their list
            # if any(x['media']['id'] == recId for x in userList):
            #     continue

            user_match = next(
                (x for x in user_list if x["media"]["id"] == rec_id), None
            )
            if user_match:
                origins.setdefault(rec_media["id"], {}).setdefault(angle_keys[0], {})[
                    media["id"]
                ] = user_match["score"]

            normalized_rating = (
                rating / (popularity + rec_popularity) * score
            )  # normalize the rating to mitigate popularity bias and factor in user score
            if normalized_rating > 0.005:
                origins.setdefault(rec_media["id"], {}).setdefault(angle_keys[1], {})[
                    media["id"]
                ] = media
            scaled_rating = (
                normalized_rating * media_mean_score
            )  # scale rating based on mean score

            recommendation_rating = recommendations.setdefault(
                rec_id, {"recScore": 0, "recMedia": rec_media, "recCount": 0}
            )
            recommendation_rating["recScore"] += scaled_rating
            recommendation_rating["recCount"] += 1

    final_decade_ratings = _calculate_average_property_score_phase_2(
        min_threshold=0, prop_type="decade", prop_ratings=decade_ratings
    )

    final_genre_ratings = _calculate_average_property_score_phase_2(
        min_threshold=2, prop_type="genre", prop_ratings=genre_ratings
    )
    final_tag_ratings = _calculate_average_property_score_phase_2(
        min_threshold=200, prop_type="tag", prop_ratings=tag_ratings
    )
    final_studio_ratings = _calculate_average_property_score_phase_2(
        min_threshold=2, prop_type="studio", prop_ratings=studio_ratings
    )
    final_staff_ratings = _calculate_average_property_score_phase_2(
        min_threshold=2, prop_type="staff", prop_ratings=staff_ratings
    )

    final_rec_list = [
        {"recScore": x["recScore"] / x["recCount"], "recMedia": x["recMedia"]}
        for x in list(recommendations.values())
        if x["recCount"] > 1
    ]

    return (
        {
            "genres": final_genre_ratings,
            "tags": final_tag_ratings,
            "studios": final_studio_ratings,
            "staff": final_staff_ratings,
            "decades": final_decade_ratings,
        },
        final_rec_list,
        origins,
    )


def _calculate_biases(
    property_ratings,
    recs,
    use,
    rec_origins,
    user_mean,
):
    angle_keys = list(constants.ANGLES.keys())
    final_recs = []
    origin_threshold = -0.2 + 0.853 * user_mean + (1.49e-3 * (user_mean**2))
    for rec in recs:
        rec_media = rec["recMedia"]

        decade_total = 0
        decade_count = 0
        if (
            use["decades"]
            and rec_media.get("startDate")
            and rec_media["startDate"].get("year")
        ):
            decades = [_get_decade_from_year(rec_media["startDate"]["year"])]
            decade_ratings_d = {x["decade"]: x for x in property_ratings["decades"]}
            for decade in decades:
                if decade not in decade_ratings_d:
                    continue
                decade_total += decade_ratings_d[decade]["score"]
                decade_count += 1
                if decade_ratings_d[decade]["score"] > origin_threshold:
                    rec_origins.setdefault(rec_media["id"], {}).setdefault(
                        angle_keys[6], {}
                    )[decade] = decade
        decade_score = decade_total / decade_count if decade_count > 0 else user_mean

        genre_total = 0
        genre_count = 0
        if use["genres"]:
            genres = rec_media["genres"]
            genre_ratings_d = {x["genre"]: x for x in property_ratings["genres"]}
            for genre in genres:
                if genre not in genre_ratings_d:
                    continue
                genre_total += genre_ratings_d[genre]["score"]
                genre_count += 1
                if genre_ratings_d[genre]["score"] >= origin_threshold:
                    rec_origins.setdefault(rec_media["id"], {}).setdefault(
                        angle_keys[5], {}
                    )[genre] = genre
        genre_score = genre_total / genre_count if genre_count > 0 else user_mean

        tag_total = 0
        tag_count = 0
        if use["tags"]:
            tags = rec_media["tags"]
            tag_ratings_d = {x["tag"]["id"]: x for x in property_ratings["tags"]}
            for tag in tags:
                tag_id = tag["id"]
                if tag_id not in tag_ratings_d:
                    continue
                tag_total += tag_ratings_d[tag_id]["score"] * tag["rank"]
                tag_count += tag["rank"]
                if tag_ratings_d[tag_id]["score"] >= origin_threshold:
                    rec_origins.setdefault(rec_media["id"], {}).setdefault(
                        angle_keys[2], {}
                    )[tag_id] = tag
        tag_score = tag_total / tag_count if tag_count > 0 else user_mean

        studio_total = 0
        studio_count = 0
        if use["studios"]:
            studios = rec_media["studios"]["nodes"]
            studio_ratings_d = {
                x["studio"]["id"]: x for x in property_ratings["studios"]
            }
            for studio in studios:
                studio_id = studio["id"]
                if studio_id not in studio_ratings_d:
                    continue
                studio_total += studio_ratings_d[studio_id]["score"]
                studio_count += 1
                if studio_ratings_d[studio_id]["score"] >= origin_threshold:
                    rec_origins.setdefault(rec_media["id"], {}).setdefault(
                        angle_keys[3], {}
                    )[studio_id] = studio
        studio_score = studio_total / studio_count if studio_count > 0 else user_mean

        staff_total = 0
        staff_count = 0
        if use["staff"]:
            staffs = rec_media["staff"]["nodes"]
            staff_ratings_d = {x["staff"]["id"]: x for x in property_ratings["staff"]}
            for staff in staffs:
                staff_id = staff["id"]
                if staff_id not in staff_ratings_d:
                    continue
                staff_total += staff_ratings_d[staff_id]["score"]
                staff_count += 1
                if staff_ratings_d[staff_id]["score"] >= origin_threshold:
                    rec_origins.setdefault(rec_media["id"], {}).setdefault(
                        angle_keys[4], {}
                    )[staff_id] = staff
        staff_score = staff_total / staff_count if staff_count > 0 else user_mean

        final_recs.append(
            {
                "recScore": rec["recScore"]
                * tag_score
                * studio_score
                * genre_score
                * staff_score
                * decade_score,
                "recMedia": rec_media,
            }
        )
    final_recs.sort(key=lambda x: -x["recScore"])

    return final_recs, rec_origins
