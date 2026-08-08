# AniList Toolkit
A helpful desktop application with utilities to enhance your AniList and anime watching experience!
## What To Watch
Generates a list of recommendations based on one or more public AniList profiles. If you use multiple you'll get a joint list, sort of like a Spotify Blend but for anime! \
Currently uses Anilist's crowdsourced recommendations as the core source, also taking into account the user's own ratings and common tags. \
As of right now, anime and manga are grouped together. \
## AniHunter
Finds upcoming releases that contain one or more of your favorite tags. Remembers what it showed you and won't resurface the same media again unless it gains another relevant tag.
# Usage
## I cloned the repo
### Prerequisites
```bash
pip install -r requirements.txt
```
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
# FAQ
## It isn't working!
Create an issue here in GitHub so I can address it please!
## Why is it so slow?!
Anilist rate limits their API pretty strictly so fetching data from the server can take 5-10 minutes  
data is cached locally for 2 days, though, so subsequent runs are quicker within that time
## The AniList API is down!
Literally nothing I can do about that. I am not an AniList developer.
## I would like to integrate one of your tools into my own app!
You're free to use bits and pieces of my code including porting my logic to other languages. Please make sure to follow all terms of the GPLv3 license while doing so. Also, while you aren't required to credit me, it would be appreciated!
## Do you use generative AI?
I have used it in the past for setting up the github actions and for generating commit messages, but I have since sworn off it. The application itself is AI-free and any further work in this repo will be so as well. I believe in the irreplaceable power of human creation and I hope you all (as fellow anime fans) do as well. On your honor, please do not attempt to merge any genAI code into this repo.