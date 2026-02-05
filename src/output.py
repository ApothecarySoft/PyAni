import constants


def generateOriginStringForType(media, origins, userName=None):
    string = f"\t{userName}\n" if userName else ""
    for angle, text in constants.ANGLES.items():
        if media["id"] not in origins:
            continue
        if angle not in origins[media["id"]]:
            continue

        if angle == "userRating":
            userRating = list(origins[media["id"]][angle].values())[0]
            if userRating > 0:
                string += f"\tYou {text} {userRating}%\n"
            continue

        string += f"\t{text} "
        for origin in origins[media["id"]][angle].values():
            if angle == "decades":
                string += f"{origin}s"
                return string + "\n"
            name = ""
            if "title" in origin:
                name = getEnglishTitleOrUserPreferred(origin["title"])
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


def getEnglishTitleOrUserPreferred(title):
    return title["english"] if title["english"] else title["userPreferred"]


def writeRecList(finalRecs, origins, userNames):
    fullName = ""
    for userName in userNames:
        fullName += f"{userName}-"
    with open(f"{fullName}recs.txt", "w", encoding="utf-8") as f:
        for rec in finalRecs:

            media = rec["recMedia"]
            title = getEnglishTitleOrUserPreferred(media["title"])
            mediaFormat = media["format"]
            year = media["startDate"]["year"]
            score = rec["recScore"]
            print(f"{title} ({mediaFormat}, {year}): {score}%", file=f)

            if "meanScore" in media:
                meanScore = media["meanScore"]
                print(f"\tother users rated it {meanScore}%\n", file=f)

            for i in range(len(userNames)):
                print(
                    generateOriginStringForType(
                        media=media, origins=origins[i], userName=userNames[i]
                    ),
                    file=f,
                )
