# Deploying to a permanent link (PythonAnywhere, free)

The goal: one HTTPS URL you hand to participants that keeps working when your laptop is shut,
and **does not change when you redeploy**.

Why PythonAnywhere and not Render/Fly: Render's free tier cannot attach a disk, so `labels.db`
is destroyed on every redeploy, restart or idle spin-down, and Fly.io no longer has a free tier.
PythonAnywhere free gives a real persistent filesystem, so SQLite works unchanged.

**What you get:** `https://<username>.pythonanywhere.com` — permanent, always on, no cold start.

---

## Before you start
Push the latest code, because the server deploys by cloning your repo:
```sh
git push origin main
```
Generate the two secrets, and keep them somewhere safe — you will paste them in step 5:
```sh
python -c "import secrets; print('SECRET_KEY   =', secrets.token_urlsafe(32))"
python -c "import secrets; print('EXPORT_TOKEN =', secrets.token_urlsafe(16))"
```

## 1. Sign up
<https://www.pythonanywhere.com/registration/register/beginner/> — the "Beginner" account is
free and needs no card. Your username becomes your URL, so pick one you are happy to send to
participants. Note it down; every `<username>` below is that name.

## 2. Get the code onto the server
**Consoles** tab → **Bash**. Then:
```sh
git clone https://github.com/divyas39/Human-AI-Interaction.git
mkvirtualenv --python=/usr/bin/python3.11 study
pip install flask
```
`mkvirtualenv` leaves the new virtualenv active and named `study`. If the repo is private, use a
GitHub personal access token as the password when prompted.

## 3. Create the web app
**Web** tab → **Add a new web app** → **Manual configuration** (*not* the "Flask" option — that
scaffolds a new app over yours) → same Python version as above.

## 4. Point it at your code
On the Web tab, set:

| field | value |
|---|---|
| Source code | `/home/<username>/Human-AI-Interaction` |
| Working directory | `/home/<username>/Human-AI-Interaction` |
| Virtualenv | `/home/<username>/.virtualenvs/study` |

## 5. The WSGI file
On the Web tab, click the **WSGI configuration file** link. Delete everything in it and paste
the contents of [`wsgi_template.py`](wsgi_template.py) from this repo, replacing every
`<placeholder>` with your username and the two generated secrets. Save.

This file lives at `/var/www/...`, outside your repo — which is why the secrets in it are never
committed. Note that `DB_PATH` points at `/home/<username>/labels.db`, **outside** the checkout,
so a `git pull` can never disturb collected data.

## 6. Reload
Green **Reload** button on the Web tab. Open `https://<username>.pythonanywhere.com/`.

---

## Redeploying later
The URL never changes. In a Bash console:
```sh
cd ~/Human-AI-Interaction && git pull
```
then hit **Reload**. Existing responses are untouched — they live outside the checkout.

## Two things that will lose you data if ignored

**Renew monthly.** Since January 2026 a free web app expires after **1 month**. On the Web tab
there is a "Run until <date>" button — click it any time before the date shown and it extends.
Put a monthly reminder in your calendar; if it expires, the link 404s for participants.

**Back up the data.** PythonAnywhere's disk is your only copy. Pull it down regularly:
```sh
curl "https://<username>.pythonanywhere.com/export?token=<EXPORT_TOKEN>" -o labels_backup.csv
```

## Checks after deploying
1. Open the URL **on your phone**, not just the laptop, and complete all 5 tweets.
2. `curl "https://<username>.pythonanywhere.com/export?token=<token>"` — your submission is there.
3. Hit **Reload**, run check 2 again. The row must survive. This is the whole reason for
   choosing this host.
4. `curl -o /dev/null -w "%{http_code}\n" "https://<username>.pythonanywhere.com/export"` — must
   print `403`. Without the token nobody can read participant data.

## Troubleshooting
- **500 error** → Web tab → **Error log**. A `ModuleNotFoundError: flask` means the virtualenv
  path in step 4 is wrong; a `FileNotFoundError` means the source-code path is.
- **Site shows "Hello from Flask!"** → you picked the Flask option in step 3 instead of Manual
  configuration; delete the web app and redo it.
- **Changes not showing** → you did not press Reload.
