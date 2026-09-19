"""Emotion labeling study: each participant labels 5 random tweets."""
import csv
import io
import json
import os
import pathlib
import random
import sqlite3
from datetime import datetime, timezone

from flask import Flask, abort, redirect, render_template, request, session, url_for

EMOTIONS = ["anger", "fear", "joy", "love", "sadness", "surprise"]

# Worked examples for the instructions page. Written by hand rather than taken from the
# dataset, so a participant can never be shown an example as one of their real tweets.
EXAMPLES = [
    ("anger", "i feel like screaming every time they send me the same useless reply",
     "Frustration pointed outward at someone. Anger covers the whole range from mild "
     "irritation to outrage — it does not have to be shouting."),
    ("fear", "i keep checking my phone because i feel like something bad is about to happen",
     "Dread about what might happen next. Fear looks forward to a threat; sadness looks back "
     "at a loss."),
    ("joy", "i feel so light today like everything finally clicked into place",
     "Positive and energised, and about the situation rather than about a person — that is "
     "what separates joy from love."),
    ("love", "i feel so lucky to have someone who still waits up for me",
     "Warmth aimed at a specific person. The tweet is positive, but the affection has a "
     "target, so it is love rather than plain joy."),
    ("sadness", "i feel completely empty since she stopped calling",
     "Loss and low energy, turned inward. No threat ahead and nobody being blamed, which "
     "rules out fear and anger."),
    ("surprise", "i cannot believe they actually showed up i feel totally thrown",
     "Being caught off guard. Surprise can be pleasant or unpleasant — it is about the jolt, "
     "not about whether the news was good."),
]
N_TWEETS = 5

# Everything is resolved against this file, never the working directory: a WSGI server
# (PythonAnywhere, gunicorn under a supervisor) runs the app from somewhere else entirely.
HERE = pathlib.Path(__file__).resolve().parent
TWEETS = {t["id"]: t for t in json.loads((HERE / "tweets.json").read_text())}

# In production point DB_PATH outside the checkout, so a git pull can never touch collected
# data. ponytail: one SQLite file assumes one worker process -- fine here, and the free
# PythonAnywhere tier gives exactly one. Move to Postgres before adding workers.
DB_PATH = os.environ.get("DB_PATH", str(HERE / "labels.db"))
EXPORT_TOKEN = os.environ.get("EXPORT_TOKEN", "dev-token")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    # the cookie carries the participant's assigned tweet ids; HTTPS_ONLY=1 in production
    SESSION_COOKIE_SECURE=os.environ.get("HTTPS_ONLY") == "1",
)


def db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS labels (
        participant_id TEXT, tweet_id INTEGER, tweet_text TEXT,
        label TEXT, gold_label TEXT, ambiguous INTEGER, comment TEXT, created_at TEXT)""")
    return con


@app.route("/")
def index():
    session.clear()
    return render_template("index.html", emotions=EMOTIONS, n=N_TWEETS, examples=EXAMPLES)


@app.route("/join")
def join():
    return render_template("join.html", n=N_TWEETS)


@app.route("/start", methods=["POST"])
def start():
    pid = request.form.get("participant_id", "").strip()
    if not pid:
        return render_template("join.html", n=N_TWEETS,
                               error="Please enter a participant ID."), 400
    session["pid"] = pid
    session["tweet_ids"] = random.sample(list(TWEETS), N_TWEETS)
    return redirect(url_for("label"))


@app.route("/label")
def label():
    if "pid" not in session:
        return redirect(url_for("index"))
    return render_template("label.html", emotions=EMOTIONS,
                           tweets=[TWEETS[i] for i in session["tweet_ids"]])


@app.route("/submit", methods=["POST"])
def submit():
    if "pid" not in session:
        return redirect(url_for("index"))
    # Tweet ids come from the session, never the form, so a tampered post can't
    # write labels for tweets this participant was never shown.
    ids = session["tweet_ids"]
    picks = [request.form.get(f"tweet_{i}") for i in ids]
    if any(p not in EMOTIONS for p in picks):
        return render_template("label.html", emotions=EMOTIONS,
                               tweets=[TWEETS[i] for i in ids],
                               error="Please choose one emotion for every tweet."), 400
    now = datetime.now(timezone.utc).isoformat()
    comment = request.form.get("comment", "").strip()
    with db() as con:
        con.executemany("INSERT INTO labels VALUES (?,?,?,?,?,?,?,?)",
                        [(session["pid"], i, TWEETS[i]["text"], p, TWEETS[i]["gold"],
                          int(f"amb_{i}" in request.form), comment, now)
                         for i, p in zip(ids, picks)])
    session.clear()
    return redirect(url_for("done"))


@app.route("/done")
def done():
    return render_template("done.html")


@app.route("/withdraw")
def withdraw():
    session.clear()
    return redirect(url_for("index"))


@app.route("/export")
def export():
    if request.args.get("token") != EXPORT_TOKEN:
        abort(403)
    with db() as con:
        rows = con.execute("SELECT * FROM labels ORDER BY created_at").fetchall()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["participant_id", "tweet_id", "tweet_text", "label", "gold_label",
                "ambiguous", "comment", "created_at"])
    w.writerows(rows)
    return out.getvalue(), 200, {"Content-Type": "text/csv",
                                 "Content-Disposition": "attachment; filename=labels.csv"}


if __name__ == "__main__":
    app.run(debug=True)
