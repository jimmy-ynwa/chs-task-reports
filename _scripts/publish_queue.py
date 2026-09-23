#!/usr/bin/env python3
"""Empty the Airtable Publish Queue into this repo.

Reads every row with Status = Queued, writes its HTML (or its first attachment)
to Path, commits and pushes once, then marks each row Published or Failed.
Pushing redeploys guide.chshappenings.com (Cloudflare) and GitHub Pages.
Standard library only.
"""
import datetime
import json
import os
import pathlib
import subprocess
import sys
import urllib.parse
import urllib.request

BASE = "appWa4GJWOvIujI2Q"
TABLE = "tbltFUn4uyxQt8u0n"
API = f"https://api.airtable.com/v0/{BASE}/{TABLE}"
MAX_BYTES = 15 * 1024 * 1024
BLOCKED_PREFIXES = (".git/", ".github/", ".git", ".github")

TOKEN = os.environ.get("AIRTABLE_TOKEN", "").strip()


def airtable(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def queued_rows():
    rows, offset = [], None
    while True:
        q = {"filterByFormula": "{Status}='Queued'", "pageSize": "100"}
        if offset:
            q["offset"] = offset
        page = airtable("GET", API + "?" + urllib.parse.urlencode(q))
        rows += page.get("records", [])
        offset = page.get("offset")
        if not offset:
            return rows


def update(records):
    for i in range(0, len(records), 10):
        airtable("PATCH", API, {"records": records[i:i + 10], "typecast": True})


def safe_path(raw):
    p = (raw or "").strip().replace("\\", "/")
    if not p:
        raise ValueError("Path is empty")
    if p.startswith("/") or ":" in p.split("/")[0]:
        raise ValueError("Path must be relative to the repo root")
    parts = p.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("Path has an empty, '.' or '..' segment")
    if p.startswith(BLOCKED_PREFIXES):
        raise ValueError("Path may not be inside .git or .github")
    if p.endswith("/"):
        raise ValueError("Path must name a file, not a folder")
    return p


def content_for(fields):
    html = fields.get("HTML")
    if html and html.strip():
        return html.encode("utf-8")
    files = fields.get("File") or []
    if files:
        with urllib.request.urlopen(files[0]["url"], timeout=120) as r:
            data = r.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("Attachment is larger than 15 MB")
        return data
    raise ValueError("Row has neither HTML nor a File attachment")


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout.strip()


def main():
    if not TOKEN:
        print("AIRTABLE_TOKEN secret is not set yet; nothing to do.")
        return 0
    rows = queued_rows()
    if not rows:
        print("Queue is empty.")
        return 0

    written, failed, messages = [], [], []
    for row in rows:
        f = row.get("fields", {})
        try:
            path = safe_path(f.get("Path"))
            data = content_for(f)
            target = pathlib.Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            written.append((row["id"], path))
            messages.append(f.get("Commit Message") or f"publish {path}")
            print(f"wrote {path} ({len(data)} bytes)")
        except Exception as e:  # one bad row never blocks the rest
            failed.append({"id": row["id"], "fields": {"Status": "Failed", "Error": str(e)[:5000]}})
            print(f"FAILED {f.get('Path')!r}: {e}")

    commit = "unchanged"
    if written:
        git("config", "user.name", "CHS Task Bot")
        git("config", "user.email", "jimmy@chshappenings.com")
        git("add", "--", *[p for _, p in written])
        if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode != 0:
            title = messages[0] if len(messages) == 1 else f"publish queue: {len(messages)} pages"
            body = "\n".join(f"- {m}" for m in messages) if len(messages) > 1 else ""
            git("commit", "-m", title, *(["-m", body] if body else []))
            for attempt in range(3):
                try:
                    git("pull", "--rebase", "--quiet", "origin", "HEAD")
                    git("push", "--quiet", "origin", "HEAD")
                    break
                except subprocess.CalledProcessError as e:
                    if attempt == 2:
                        err = (e.stderr or str(e))[:5000]
                        update(failed + [{"id": rid, "fields": {"Error": "push failed, will retry next run: " + err}} for rid, _ in written])
                        print("push failed:", err)
                        return 1
            commit = git("rev-parse", "--short", "HEAD")
            # Nudge GitHub Pages; Cloudflare redeploys on the push by itself.
            try:
                subprocess.run(["gh", "api", "-X", "POST", f"repos/{os.environ.get('GITHUB_REPOSITORY', '')}/pages/builds"],
                               capture_output=True, timeout=60)
            except (OSError, subprocess.SubprocessError):
                pass

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    done = [{"id": rid, "fields": {"Status": "Published", "Published At": now, "Commit": commit, "Error": ""}}
            for rid, _ in written]
    update(done + failed)
    print(f"published {len(done)}, failed {len(failed)}, commit {commit}")
    return 1 if failed and not done else 0


if __name__ == "__main__":
    sys.exit(main())
