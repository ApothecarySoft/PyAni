# PyAni
Generates a list of recommendations based on a public AniList profile.  
Currently uses Anilist's crowdsourced recommendations as the core source, also taking into account the user's own ratings and common tags.  
As of right now, anime and manga are grouped together.
# Dependencies
running
```
pip install -r requirements.txt
```
from the project root will install all requirements automatically.
Read `requirements.txt` for a list of dependencies.\
This also works within venv if you prefer.
# Usage
run nextani.py in python3 along with one or more anilist usernames. Ff you use more than one username, it will generate a joint list for all users listed
```
python3 src/nextani.py [-rhtsfg] username1 [username2]...
```
supports optional flags
- -r to force refresh from the server
- -h to display help
- -t to take tags into account
- -s to take studios into account
- -f to take staff into account 
- -g to take genres into account 
# AniList is mean
they rate limit their API pretty strictly so fetching data from the server can take 5-10 minutes  
data is cached locally for 2 days, though, so subsequent runs are quicker unless you force refresh
