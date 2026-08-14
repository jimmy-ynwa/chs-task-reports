#!/usr/bin/env python3
"""Regenerate park-circle/index.html and latest.html.

index.html  — reverse-chronological list of every run page
latest.html — redirect to the newest run, so one link always lands current
"""
import os
import re
import sys
from datetime import datetime

folder = sys.argv[1] if len(sys.argv) > 1 else "park-circle"
pages = sorted(
    (f for f in os.listdir(folder) if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.html", f)),
    reverse=True)

rows = []
for i, p in enumerate(pages):
    d = p[:-5]
    try:
        pretty = datetime.strptime(d, "%Y-%m-%d").strftime("%a, %b %-d, %Y")
    except ValueError:
        pretty = d
    flag = '<span class="new">Latest</span>' if i == 0 else ""
    rows.append('<li{cls}><a href="{p}"><span class="d">{pretty}{flag}</span>'
                '<span class="go">Open &rarr;</span></a></li>'.format(
                    cls=' class="top"' if i == 0 else "", p=p, pretty=pretty, flag=flag))

html = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Park Circle Watch &middot; The Farrell Group</title>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@600&family=Montserrat:wght@400;600&display=swap" rel="stylesheet">
<style>
 body{margin:0;background:#FAF7F2;color:#16202B;font-family:'Montserrat',sans-serif;font-size:15px;}
 header{background:#003466;color:#fff;padding:34px 20px;}
 .w{max-width:720px;margin:0 auto;}
 .eyebrow{font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:#ECD19C;font-weight:600;margin-bottom:10px;}
 h1{font-family:'Cormorant Garamond',Georgia,serif;margin:0 0 8px;font-size:38px;font-weight:600;}
 .sub{color:#cfe0ea;font-size:13.5px;}
 main{max-width:720px;margin:0 auto;padding:26px 16px 60px;}
 ul{list-style:none;margin:0;padding:0;}
 li{margin-bottom:9px;}
 a{display:flex;justify-content:space-between;align-items:center;background:#fff;
   border:1px solid #E4DED4;border-radius:4px;padding:15px 18px;text-decoration:none;color:#003466;}
 li.top a{border-left:3px solid #ECD19C;}
 .d{font-weight:600;font-size:15px;}
 .new{background:#003466;color:#ECD19C;font-size:9.5px;letter-spacing:.12em;text-transform:uppercase;
      padding:3px 8px;border-radius:2px;margin-left:10px;vertical-align:2px;}
 .go{font-size:12.5px;color:#7095A7;font-weight:600;}
 .none{background:#fff;border:1px solid #E4DED4;border-radius:4px;padding:40px;text-align:center;color:#7095A7;}
</style></head><body>
<header><div class="w">
 <div class="eyebrow">The Farrell Group &middot; Listing Watch</div>
 <h1>Park Circle</h1>
 <div class="sub">Single Family Detached &middot; 1,750+ sq ft &middot; 3+ bed / 2+ full bath &middot; up to $800,000 &middot; Fridays</div>
</div></header>
<main>%s</main></body></html>""" % (
    "<ul>%s</ul>" % "".join(rows) if rows else '<div class="none">No runs published yet</div>')

with open(os.path.join(folder, "index.html"), "w") as fh:
    fh.write(html)

if pages:
    newest = pages[0]
    redirect = ('<!DOCTYPE html><html><head><meta charset="utf-8">'
                '<meta name="robots" content="noindex, nofollow">'
                '<meta http-equiv="refresh" content="0; url={n}">'
                '<title>Park Circle Watch</title></head>'
                '<body><p><a href="{n}">Open the latest Park Circle Watch</a></p>'
                '</body></html>').format(n=newest)
    with open(os.path.join(folder, "latest.html"), "w") as fh:
        fh.write(redirect)

print("park-circle index rebuilt with {} run(s)".format(len(pages)))
