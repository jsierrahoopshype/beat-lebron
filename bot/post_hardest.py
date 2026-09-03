#!/usr/bin/env python3
"""
Beat LeBron reveal bot: posts yesterday's most-missed question to Bluesky (and X if configured).

Reads GET /hardest from the leaderboard Worker, resolves the metric label and LeBron's mark
from the game's data file, composes one post, and publishes it. DRY_RUN=1 (the default) only
prints the post. Nothing is sent until DRY_RUN=0 is set explicitly.

Env vars:
  DRY_RUN            "1" (default) prints only; "0" posts
  BSKY_HANDLE        e.g. hoopshypeofficial.bsky.social
  BSKY_APP_PASSWORD  an app password from Bluesky settings (never the account password)
  X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET   optional; X is skipped if any is missing
  DAY                optional YYYY-MM-DD (ET) to post about a specific day instead of yesterday
  MIN_PLAYS          minimum plays that day before posting (default 25)

    pip install -r requirements.txt
    python post_hardest.py
"""
import json, os, sys, re, urllib.request

LB_API = os.environ.get("LB_API", "https://beat-lebron-leaderboard.thejorgesierra.workers.dev")
DATA_URL = os.environ.get("DATA_URL", "https://jsierrahoopshype.github.io/beat-lebron/lebron-duo-data.js")
GAME_URL = "https://hoopsmatic.com/beat-lebron"


def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read().decode("utf-8")


def fmt(n):
    return f"{int(n):,}"


def compose():
    day = os.environ.get("DAY", "").strip()
    h = json.loads(get(LB_API + "/hardest" + (f"?day={day}" if day else "")))
    if h.get("plays", 0) < int(os.environ.get("MIN_PLAYS", "25")):
        print(f"only {h.get('plays', 0)} plays on {h.get('day')}, skipping")
        return None
    if not h.get("questions"):
        print("no question with enough answers, skipping")
        return None
    data = json.loads(get(DATA_URL).split("=", 1)[1].strip().rstrip(";"))
    keys = [m["k"] for m in data["metrics"]]
    q = h["questions"][0]
    mi = keys.index(q["m"]) if q["m"] in keys else -1
    label = data["metrics"][mi]["label"] if mi >= 0 else q["m"]
    L = data["lebron"]["v"][mi] if mi >= 0 else None
    pick = q.get("topWrongPick") or ""
    pick_line = ""
    if pick and pick != "timeout":
        pick_line = f" Most common wrong pick: {pick.replace(' + ', ' and ')}."
    text = (f"Yesterday's most-missed Beat LeBron question: two All-Stars with more {label} than LeBron"
            f"{' (' + fmt(L) + ')' if L is not None else ''}. {q['missPct']}% got it wrong. "
            f"The answer: {q['a']} and {q['b']}.{pick_line} Today's game is up: {GAME_URL}")
    if len(text) > 296:   # Bluesky limit is 300 graphemes; X is 280 but shortens the URL
        text = (f"Most-missed Beat LeBron question yesterday: more {label} than LeBron. {q['missPct']}% got it wrong. "
                f"Answer: {q['a']} and {q['b']}. {GAME_URL}")
    return text


def post_bluesky(text):
    from atproto import Client, client_utils
    handle, pw = os.environ.get("BSKY_HANDLE"), os.environ.get("BSKY_APP_PASSWORD")
    if not (handle and pw):
        print("Bluesky: credentials missing, skipped"); return
    c = Client(); c.login(handle, pw)
    tb = client_utils.TextBuilder()
    before, url = text.rsplit(GAME_URL, 1)[0], GAME_URL
    tb.text(before); tb.link(url, url)
    c.send_post(tb)
    print("Bluesky: posted")


def post_x(text):
    keys = [os.environ.get(k) for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")]
    if not all(keys):
        print("X: credentials missing, skipped"); return
    import tweepy
    api = tweepy.Client(consumer_key=keys[0], consumer_secret=keys[1], access_token=keys[2], access_token_secret=keys[3])
    api.create_tweet(text=text)
    print("X: posted")


if __name__ == "__main__":
    text = compose()
    if not text:
        sys.exit(0)
    print("POST:\n" + text + "\n")
    if os.environ.get("DRY_RUN", "1") != "0":
        print("DRY_RUN=1, nothing sent. Set DRY_RUN=0 to post.")
        sys.exit(0)
    post_bluesky(text)
    post_x(text)
