"""One-off: pull tweets from the dair-ai/emotion dataset into tweets.json.

Run once; tweets.json is committed so the app never depends on HF at runtime.
    python build_dataset.py
"""
import json
import urllib.request
from collections import defaultdict

API = ("https://datasets-server.huggingface.co/rows"
       "?dataset=dair-ai%2Femotion&config=split&split=train&offset={}&length=100")
PER_LABEL = 10


def main():
    by_label = defaultdict(list)
    names = None
    offset = 0
    # ponytail: linear paging from the top of the split, stops once every label is full.
    # Fine for 6 labels x 10; take a random offset if you ever want a less head-biased sample.
    while offset < 2000 and (names is None or any(len(by_label[n]) < PER_LABEL for n in names)):
        with urllib.request.urlopen(API.format(offset)) as r:
            page = json.load(r)
        names = page["features"][1]["type"]["names"]
        for row in page["rows"]:
            label = names[row["row"]["label"]]
            if len(by_label[label]) < PER_LABEL:
                by_label[label].append({"id": row["row_idx"],
                                        "text": row["row"]["text"],
                                        "gold": label})
        offset += 100

    tweets = [t for name in names for t in by_label[name]]
    assert len(tweets) == PER_LABEL * len(names), {k: len(v) for k, v in by_label.items()}
    with open("tweets.json", "w") as f:
        json.dump(tweets, f, indent=1)
    print(f"wrote {len(tweets)} tweets, {len(names)} labels: {', '.join(names)}")


if __name__ == "__main__":
    main()
