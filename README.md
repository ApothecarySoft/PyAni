# AniList Toolkit
A helpful desktop application with utilities to enhance your AniList and anime watching experience!
## What To Watch
Generates a list of recommendations based on a public AniList profile.  
Currently uses Anilist's crowdsourced recommendations as the core source, also taking into account the user's own ratings and common tags.  
As of right now, anime and manga are grouped together.
## AniHunter
Finds upcoming releases that contain one or more of your favorite tags. Remembers what it showed you and won't resurface the same media again unless it gains another relevant tag.
# Prerequisites
```bash
pip install -r requirements.txt
```
# Usage
## I cloned the repo
run mainwindow.py in python3
### Linux/Mac
```bash
python3 src/mainwindow.py
```
### Windows
```pwsh
python src\mainwindow.py
```
## I downloaded a release
### Linux:
Double click mainwindow.bin or run `./mainwindow.bin` in the terminal \
You may need to `sudo chmod +x mainwindow.bin` first
### Windows:
Double click mainwindow.exe \
You may need to click past Windows Smart Screen
# It isn't working!
Create an issue here in GitHub so I can address it please!
# AniList is mean
they rate limit their API pretty strictly so fetching data from the server can take 5-10 minutes  
data is cached locally for 2 days, though, so subsequent runs are quicker within that time
