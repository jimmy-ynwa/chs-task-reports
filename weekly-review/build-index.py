#!/usr/bin/env python3
"""Regenerate the Week in Review archive index.

Scans this directory for YYYY-MM-DD.html review pages, pulls the date range and
summary line out of each page header, and writes index.html (the archive) plus
latest.html (a redirect to the newest review).

Run it from anywhere: python3 weekly-review/build-index.py
"""

import os
import re
import glob
import html
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))

NAVY = "#003466"
LIME = "#AEDC2E"
GOLD = "#ECD19C"
STEEL = "#7095A7"
BG = "#F4F5F0"
INK = "#1A1A2E"
BODY = "#3D3D52"
MUTED = "#888899"
RULE = "#E8E8EE"

MONTHS = ["", "January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


def strip_tags(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def grab(pattern, text):
    m = re.search(pattern, text, re.S | re.I)
    return strip_tags(m.group(1)) if m else ""


def header_region(src):
    """Everything from <body> up to the first content card — the page header."""
    body = src.split("<body", 1)[-1]
    for marker in ('class="wrap"', 'class="card', "</header>", "</head>"):
        cut = body.find(marker)
        if cut > 0:
            return body[:cut + len(marker)]
    return body[:2500]


def parse(path):
    src = open(path, encoding="utf-8").read()
    head = header_region(src)
    stamp = os.path.basename(path)[:-5]
    y, m, d = (int(x) for x in stamp.split("-"))

    rng = grab(r'class="[^"]*\brange\b[^"]*"[^>]*>(.*?)</div>', head)
    if not rng:
        rng = grab(r"<title>\s*Week in Review\s*[^A-Za-z0-9]*\s*(.*?)</title>", src)
    if not rng:
        rng = "%s %d, %d" % (MONTHS[m], d, y)

    summary = ""
    for cls in ("summary", "stat", "sub"):
        summary = grab(r'class="[^"]*\b%s\b[^"]*"[^>]*>(.*?)</div>' % cls, head)
        if summary and summary != rng:
            break
        summary = ""

    # Some headers pack the range and the stat line into one div — drop the echo.
    if summary.lower().startswith(rng.lower()):
        summary = summary[len(rng):].lstrip(" ·|—-–,").strip()

    return {
        "stamp": stamp,
        "sort": (y, m, d),
        "range": rng,
        "summary": summary,
        "label": "%s %d, %d" % (MONTHS[m], d, y),
    }


def card(item, is_latest):
    pill = ('<span class="pill">Latest</span>' if is_latest else "")
    summary = ('<div class="sum">%s</div>' % html.escape(item["summary"])
               if item["summary"] else "")
    return """    <a class="row%s" href="%s.html">
      <div class="meta"><span class="date">%s</span>%s</div>
      <div class="rng">%s</div>
%s      <div class="go">Open the review &rarr;</div>
    </a>
""" % (" latest" if is_latest else "", item["stamp"],
       html.escape(item["label"]), pill, html.escape(item["range"]), summary)


def build():
    files = sorted(glob.glob(os.path.join(HERE, "20??-??-??.html")))
    items = sorted((parse(f) for f in files), key=lambda i: i["sort"], reverse=True)

    rows = "".join(card(it, i == 0) for i, it in enumerate(items))
    if not items:
        rows = '    <div class="empty">No reviews published yet</div>\n'

    newest = items[0] if items else None
    count = len(items)
    built = date.today().strftime("%B %-d, %Y")

    page = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Week in Review &middot; Archive</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:%(bg)s;color:%(body)s;
    font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Helvetica Neue",sans-serif;
    -webkit-font-smoothing:antialiased;line-height:1.5}
  .top{background:%(navy)s;padding:34px 20px 30px}
  .inner{max-width:760px;margin:0 auto}
  .eyebrow{color:%(lime)s;font-size:10px;font-weight:700;letter-spacing:.16em;
    text-transform:uppercase;margin-bottom:10px}
  h1{color:#fff;font-size:30px;font-weight:700;letter-spacing:-.02em}
  .sub{color:rgba(255,255,255,.62);font-size:14px;margin-top:8px}
  .wrap{max-width:760px;margin:0 auto;padding:26px 20px 60px}
  .lbl{font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;
    color:%(navy)s;border-left:3px solid %(lime)s;padding-left:10px;margin-bottom:14px}
  .row{display:block;background:#fff;border-radius:16px;padding:20px 22px;margin-bottom:14px;
    text-decoration:none;color:inherit;box-shadow:0 1px 3px rgba(26,26,46,.07);
    border-left:3px solid transparent;transition:transform .12s ease,box-shadow .12s ease}
  .row:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(26,26,46,.11)}
  .row.latest{border-left-color:%(lime)s}
  .meta{display:flex;align-items:center;gap:10px;margin-bottom:4px}
  .date{font-size:16px;font-weight:700;color:%(ink)s;letter-spacing:-.01em}
  .pill{background:%(navy)s;color:#fff;font-size:9px;font-weight:700;letter-spacing:.12em;
    text-transform:uppercase;padding:3px 8px;border-radius:20px}
  .rng{font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:%(steel)s}
  .sum{font-size:14px;color:%(body)s;margin-top:10px}
  .go{font-size:12px;font-weight:600;color:%(navy)s;margin-top:12px}
  .empty{background:#fff;border-radius:16px;padding:24px;color:%(muted)s;font-size:14px}
  .foot{border-top:1px solid %(rule)s;margin-top:26px;padding-top:14px;
    font-size:11px;color:%(muted)s}
  @media(max-width:520px){h1{font-size:25px}.row{padding:18px}}
</style>
</head>
<body>
<header class="top">
  <div class="inner">
    <div class="eyebrow">The Farrell Group &middot; CHS Happenings</div>
    <h1>Week in Review</h1>
    <div class="sub">%(subline)s</div>
  </div>
</header>
<div class="wrap">
  <div class="lbl">Every review, newest first</div>
%(rows)s  <div class="foot">%(count)d review%(plural)s archived &middot; index rebuilt %(built)s</div>
</div>
</body>
</html>
""" % {
        "bg": BG, "navy": NAVY, "lime": LIME, "steel": STEEL, "ink": INK,
        "body": BODY, "muted": MUTED, "rule": RULE, "rows": rows,
        "count": count, "plural": "" if count == 1 else "s", "built": built,
        "subline": ("Latest: %s" % html.escape(newest["range"])) if newest
                   else "No reviews published yet",
    }

    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page)

    if newest:
        with open(os.path.join(HERE, "latest.html"), "w", encoding="utf-8") as fh:
            fh.write(
                '<!DOCTYPE html><html><head><meta charset="utf-8">'
                '<meta http-equiv="refresh" content="0; url=%s.html">'
                '<title>Latest Week in Review</title></head>'
                '<body><a href="%s.html">Open the latest review</a></body></html>\n'
                % (newest["stamp"], newest["stamp"])
            )

    print("index.html rebuilt with %d review(s); latest = %s"
          % (count, newest["stamp"] if newest else "none"))


if __name__ == "__main__":
    build()
