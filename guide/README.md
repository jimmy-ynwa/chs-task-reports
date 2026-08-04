# Charleston Insider's Guide

Source of truth for https://guide.chshappenings.com/ — the CHS Happenings lead magnet.

| File | What it is |
|---|---|
| `index.html` | The guide. CSS is inlined, but it references 122 image files that MUST sit beside it in this folder. |
| `*.jpg` / `*.png` | The 122 photos (121 background-image, 1 `<img>` map) plus `og-image.jpg`. **Never deploy `index.html` without them.** |
| `config.json` | The 22 market panels — MLS definitions, stat layout, French Quarter street rules, Folly price floor, superlative checks, anomaly gates. |
| `refresh.py` | Deterministic patcher. Reads config + data, rewrites the 132 stat cells and date stamps, aborts on anything suspicious. |
| `RECIPE.md` | The procedure the monthly scheduled run follows. Read it before touching anything. |

## Deploy

Cloudflare Pages is connected to this repo with root directory `guide`. A push to `main`
deploys. There is no manual upload step.

## Refresh cadence

Automated, 10th of each month, unattended. See `RECIPE.md`.

## Two rules that are not negotiable

1. **No active-listing data.** Jimmy consults this page over 30 to 60 days; active inventory
   is stale the day it's entered. All 132 stats are closed-sales only. `refresh.py` aborts if
   an active stat appears.
2. **Never carry a superlative forward.** Four "highest/lowest/most on the Peninsula" claims
   on the April 2026 page were false, and had been false when written. `refresh.py` recomputes
   the holder of each one every run.

## Three rules, not two

3. **The guide is not self-contained.** `index.html` pulls 122 images by bare relative
   filename. Cloudflare Pages answers a missing asset with `index.html` and a 200, so a
   deploy that drops the photos looks completely healthy in the network tab and renders as
   empty grey blocks. If you ever rebuild this folder from a downloaded copy of the live
   page, the images do not come with it. Master copy also lives in Drive:
   `Insider Guide / charleston-insiders-guide-FINAL-v4`.

