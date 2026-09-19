# Human-AI-Interaction — Assignment 1

Tweet emotion labeling study for CSE 594. Participants enter an ID and label **5 randomly
selected tweets** from the [dair-ai/emotion](https://huggingface.co/datasets/dair-ai/emotion)
dataset with one of six emotions: anger, fear, joy, love, sadness, surprise.

The interface itself carries no course branding — to a participant it is simply a labeling
task. Flow: an instructions page (`/`) introduces the task, defines the six emotions, gives a
worked example of each with the reasoning, and lists labeling tips → *Start data labeling*
leads to `/join` for the participant ID → tweets are presented **one at a time** with a
progress bar, each carrying an optional *I wasn't sure* ambiguity flag.

## Files
| file | what |
|---|---|
| `build_dataset.py` | one-off: pulls 60 tweets (10 per emotion) into `tweets.json` |
| `tweets.json` | the committed task dataset |
| `app.py` | Flask app + SQLite backend |
| `templates/` | instructions, ID entry, labeling, thank-you pages |
| `test_app.py` | self-check for the whole flow |
| `DEPLOY.md` | step-by-step deployment to a permanent public URL |
| `wsgi_template.py` | the WSGI entry file to paste into PythonAnywhere |
| `run_study.sh` | serve it from your own laptop over a temporary public link |

## Run locally
```sh
pip install -r requirements.txt
python app.py          # http://127.0.0.1:5000
python test_app.py     # self-check, prints "ok"
```

Rebuild the dataset (not needed unless you want different tweets): `python build_dataset.py`.

## Data collected
One row per (participant, tweet) in SQLite table `labels`:
`participant_id, tweet_id, tweet_text, label, gold_label, ambiguous, comment, created_at`.
The dataset's ground-truth emotion is stored as `gold_label` so accuracy needs no join, and
`ambiguous` is 1 when the participant ticked *I wasn't sure* for that tweet, else 0 — useful
for checking whether self-reported uncertainty predicts disagreement with the gold label.

The table is created on first use. If you have an older `labels.db` from before the `ambiguous`
column existed, delete it (`rm labels.db`) — there is no migration.

Download results as CSV: `curl "http://localhost:5000/export?token=$EXPORT_TOKEN" -o labels.csv`

## Configuration
All have local-dev defaults, so `python app.py` works with none of them set. **Set the first
two for anything a real participant can reach.** `PORT` is a fifth name you may see, but the
host sets that one itself.

| var | default | why |
|---|---|---|
| `SECRET_KEY` | `dev-secret` | signs the session cookie holding the 5 assigned tweet ids. A known key means forged submissions |
| `EXPORT_TOKEN` | `dev-token` | required on `/export?token=…`, or anyone downloads every participant's data |
| `DB_PATH` | `labels.db` beside `app.py` | in production point it **outside the checkout**, so `git pull` can never touch collected data |
| `HTTPS_ONLY` | unset | set to `1` when served over HTTPS to mark the session cookie secure |

Generate real values:
```sh
python -c "import secrets; print('SECRET_KEY =', secrets.token_urlsafe(32))"
python -c "import secrets; print('EXPORT_TOKEN =', secrets.token_urlsafe(16))"
```

Locally, none are required — `python app.py` works with the defaults:
```sh
export SECRET_KEY=... EXPORT_TOKEN=...
python app.py
```

## Deploy
**[DEPLOY.md](DEPLOY.md) — PythonAnywhere, free, permanent URL.** That is the supported path:
persistent disk (so SQLite is fine), `https://<username>.pythonanywhere.com` that survives
redeploys, always on. Deployment there is a WSGI file — see [`wsgi_template.py`](wsgi_template.py),
which is also where the env vars above get set, since the free tier has no env-var UI.

Render's free tier is not usable here: no persistent disk, so `labels.db` is wiped on every
redeploy and idle spin-down. Fly.io no longer has a free tier. The `Procfile` is kept and
correct for any Procfile-based host (it binds `0.0.0.0:$PORT`), but is unused on PythonAnywhere.

### Running it from your own machine instead
`./run_study.sh` serves the study locally and opens a public `cloudflared` link. Good for a
pilot or a supervised in-person session. Not for unattended data collection: the link changes
on every restart and dies when the laptop sleeps.

## Seeing the collected data
```sh
sqlite3 -header -column labels.db "SELECT participant_id, tweet_id, label, gold_label, ambiguous FROM labels;"

# agreement with the dataset's ground truth, per participant
sqlite3 -header -column labels.db "SELECT participant_id, COUNT(*) AS labels, \
  SUM(label = gold_label) AS agreed, \
  ROUND(100.0 * SUM(label = gold_label) / COUNT(*)) || '%' AS accuracy, \
  SUM(ambiguous) AS flagged_unsure FROM labels GROUP BY participant_id;"

# everything as CSV
curl "http://localhost:5000/export?token=$EXPORT_TOKEN" -o labels.csv
```

`rm labels.db` before collecting real responses if you have been testing — the file is
gitignored and recreated on the next run.
