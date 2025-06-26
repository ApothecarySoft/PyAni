# PyAni
Generates a list of recommendations based on a public AniList profile.  
Currently uses Anilist's crowdsourced recommendations as the core source, also taking into account the user's own ratings and common tags.  
As of right now, anime and manga are grouped together.
# Prerequisites
    pip install "gql[all]"
if you don't have it already
# Usage
run nextani.py in python3 along with the username of a public Anilist profile  
```
python3 nextani.py [-r][-h] username
```
supports optional flags
- -r to force refresh from the server
- -h to display help
# AniList is mean
they rate limit their API pretty strictly so fetching data from the server can take 5-10 minutes  
data is cached locally after that, though, so subsequent runs are quicker unless you force refresh
