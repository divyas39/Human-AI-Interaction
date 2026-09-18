"""Self-check: python test_app.py"""
import os
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
import app as A  # noqa: E402


def rows():
    with A.db() as con:
        return con.execute("SELECT participant_id, tweet_id, label, gold_label, ambiguous FROM labels").fetchall()


def run(pid, c, bad=False):
    c.post("/start", data={"participant_id": pid})
    with c.session_transaction() as s:
        ids = s["tweet_ids"]
    form = {f"tweet_{i}": "joy" for i in ids}
    form[f"amb_{ids[0]}"] = "1"          # first tweet flagged ambiguous, the rest left unticked
    if bad:
        form.pop(f"tweet_{ids[0]}")
    return ids, c.post("/submit", data=form)


A.app.config["TESTING"] = True
with A.app.test_client() as c:
    assert b"Start data labeling" in c.get("/").data   # instructions page, no ID form
    assert b"Participant ID" in c.get("/join").data    # ID form lives on its own step

    # empty id is rejected
    r = c.post("/start", data={"participant_id": " "})
    assert r.status_code == 400 and b"Participant ID" in r.data
    assert rows() == []

    # incomplete submission writes nothing
    _, r = run("p0", c, bad=True)
    assert r.status_code == 400, r.status_code
    assert rows() == [], rows()

    # full flow writes exactly 5 rows with the gold label attached
    ids1, r = run("p1", c)
    assert r.status_code == 302 and r.headers["Location"].endswith("/done")
    got = rows()
    assert len(got) == A.N_TWEETS and {g[0] for g in got} == {"p1"}, got
    assert sorted(g[1] for g in got) == sorted(ids1)
    assert all(g[3] in A.EMOTIONS for g in got)
    # the ambiguity flag is optional: exactly the one ticked box is stored as 1, rest as 0
    assert sorted(g[4] for g in got) == [0, 0, 0, 0, 1], got
    assert [g[4] for g in got if g[1] == ids1[0]] == [1]

    # a second participant gets an independently sampled set
    sets = {tuple(run(f"p{n}", c)[0]) for n in range(2, 12)}
    assert len(sets) > 1, "every participant saw the same 5 tweets"

    # withdrawing saves nothing and clears the session
    c.post("/start", data={"participant_id": "pw"})
    c.get("/withdraw")
    assert c.get("/label").headers["Location"].endswith("/")
    assert not [g for g in rows() if g[0] == "pw"]

    # export is token-gated
    assert c.get("/export").status_code == 403
    csv = c.get(f"/export?token={A.EXPORT_TOKEN}").data.decode()
    assert csv.count("\n") == len(rows()) + 1 and "p1," in csv

assert len(A.TWEETS) >= 50, len(A.TWEETS)
assert {t["gold"] for t in A.TWEETS.values()} == set(A.EMOTIONS)
print("ok")
