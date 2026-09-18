"""Emotion labeling study: each participant labels 5 random tweets."""
import csv
import io
import json
import os
import random
import sqlite3
from datetime import datetime, timezone

from flask import Flask, abort, redirect, render_template, request, session, url_for

EMOTIONS = ["anger", "fear", "joy", "love", "sadness", "surprise"]
N_TWEETS = 5
TWEETS = {t["id"]: t for t in json.load(open("tweets.json"))}

# ponytail: SQLite on an ephemeral host disk is wiped on redeploy. Point DB_PATH at a
# mounted volume, or move to Postgres, if the study runs on more than a handful of people.
DB_PATH = os.environ.get("DB_PATH", "labels.db")
EXPORT_TOKEN = os.environ.get("EXPORT_TOKEN", "dev-token")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")


def db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS labels (
        participant_id TEXT, tweet_id INTEGER, tweet_text TEXT,
        label TEXT, gold_label TEXT, comment TEXT, created_at TEXT)""")
    return con


@app.route("/")
def index():
    session.clear()
    return render_template("index.html", emotions=EMOTIONS, n=N_TWEETS)


@app.route("/start", methods=["POST"])
def start():
    pid = request.form.get("participant_id", "").strip()
    if not pid:
        return render_template("index.html", emotions=EMOTIONS, n=N_TWEETS,
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
        con.executemany("INSERT INTO labels VALUES (?,?,?,?,?,?,?)",
                        [(session["pid"], i, TWEETS[i]["text"], p, TWEETS[i]["gold"], comment, now)
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
                "comment", "created_at"])
    w.writerows(rows)
    return out.getvalue(), 200, {"Content-Type": "text/csv",
                                 "Content-Disposition": "attachment; filename=labels.csv"}


if __name__ == "__main__":
    app.run(debug=True)
