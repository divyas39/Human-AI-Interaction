# Human-AI-Interaction — Assignment 1

Tweet emotion labeling study for CSE 594. Participants enter an ID and label **5 randomly
selected tweets** from the [dair-ai/emotion](https://huggingface.co/datasets/dair-ai/emotion)
dataset with one of six emotions: anger, fear, joy, love, sadness, surprise.

## Files
| file | what |
|---|---|
| `build_dataset.py` | one-off: pulls 60 tweets (10 per emotion) into `tweets.json` |
| `tweets.json` | the committed task dataset |
| `app.py` | Flask app + SQLite backend |
| `templates/` | instructions page, labeling page, thank-you page |
| `test_app.py` | self-check for the whole flow |

## Run locally
```sh
pip install -r requirements.txt
python app.py          # http://127.0.0.1:5000
python test_app.py     # self-check, prints "ok"
```

Rebuild the dataset (not needed unless you want different tweets): `python build_dataset.py`.

## Data collected
One row per (participant, tweet) in SQLite table `labels`:
`participant_id, tweet_id, tweet_text, label, gold_label, comment, created_at`.
The dataset's ground-truth emotion is stored as `gold_label` so accuracy needs no join.

Download results as CSV: `curl "http://localhost:5000/export?token=$EXPORT_TOKEN" -o labels.csv`

## Deploy
Any host that reads a `Procfile` (Render, Railway, Fly). Set these env vars:

| var | why |
|---|---|
| `SECRET_KEY` | signs the session cookie — set a random value in production |
| `EXPORT_TOKEN` | required to download `/export` |
| `DB_PATH` | put it on a **persistent disk**; a host's default filesystem is wiped on redeploy |

For a quick session with real participants without deploying: `ngrok http 5000`.
