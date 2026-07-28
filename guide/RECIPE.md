# Charleston Insider's Guide — monthly refresh recipe

This is the procedure the scheduled Cowork session follows on the 10th of each month.
It runs **unattended, in a fresh cloud session, with Jimmy's laptop closed.**

Read this whole file before starting. `config.json` is the source of truth for every
neighborhood definition. Do not rely on project memory — it is unreachable in an
unattended run (see "What you cannot do" below).

---

## What you cannot do in this run

Every `mcp__remote-devices__*` tool is unavailable: no project memory, no device files,
no CHS Gmail alias. They route through a bridge to Jimmy's Mac and fail when it's closed.
The sandbox reaches **only** npm and github.com. `api.cloudflare.com` is blocked, which is
why publishing goes through git.

Available and verified working headless: **Flexmls MCP**, **Todoist MCP**, git over HTTPS.

---

## Step 1 — Clone

```
git clone https://x-access-token:$TOKEN@github.com/jimmy-ynwa/chs-task-reports.git repo
cd repo/guide
```

## Step 2 — Pull the numbers

Load the MLS tool: `ToolSearch` → `select:mcp__FlexMLS__ListingsListingSearch`

For **every** panel in `config.json`, all queries use:
- `property_type_codes: ["A"]` — already includes condos and townhomes
- `status_values: ["Closed"]`
- `_filter`: the panel's `filter`, plus `And CloseDate Ge days(-365)`, plus its
  `extra_sold_filter` if it has one

**Counting.** `_select: ListingId`, `_limit: 1`, read `total_entries`. Never paginate to count.

**Medians — 1 or 2 calls, never pagination.**
1. N = `total_entries`
2. Odd N → `_orderby: "+FIELD"`, `_limit: 1`, `_page: (N+1)/2`. That record's value is the median.
3. Even N → pages `N/2` and `N/2+1`, average them.

**Min / max.** `_orderby: "+FIELD"` or `"-FIELD"`, `_limit: 1`, `_page: 1`.

**Total volume.** Paginate `_select: ListingId,ClosePrice` at `_limit: 25` and sum. Only do
this where the panel needs it, plus the peninsula superlative pool (see Step 3).

**List-to-sale.** `sum(ClosePrice) / sum(ListPrice)` over the same record set. Do NOT use
`MarketStatisticsRatio` — it returns an unweighted monthly series over a different window.

### The DaysOnMarket trap — read this twice

A listing indexes as NULL whenever `OnMarketDate >= CloseDate` (entered into MLS on or
after the day it closed). The payload still renders `0`. These records are invisible to
**every** numeric comparison in both directions, so `Lt 30` + `Ge 30` does not sum to N.

- `DaysOnMarket Ne NULL` and `Eq NULL` both return 0 rows. Never use them.
- Use `DaysOnMarket Ge 0` as the null guard.
- **Sold under 30 days MUST use:** `(count(Lt 30) + (N − count(Ge 0))) / N`
  The naive `count(Lt 30) / N` understates by 3 to 17 points.
- Medians need no correction — nulls sit at the extreme low end and move a median by at
  most one rank position.

Where the null rate exceeds ~10% (Daniel Island ~15%, Sullivan's Island ~17%), the prose
must say those are deals recorded after the fact and never publicly marketed.

### French Quarter is the one manual panel

No subdivision code fits it. Pull **all** closings in
`MLSAreaMinor Eq '51 - Peninsula Charleston Inside of Crosstown'` with `UnparsedAddress`,
then assign by street using `french_quarter_boundary` in `config.json`. Honour the excluded
traps — Elliott St and Bedons Alley are south of Broad and stay out, even though the MLS
codes several of them "South of Broad". Judge by address, never by SubdivisionName.

## Step 3 — Write data.json

One object per panel id. Include every stat key the panel displays, **plus** every metric
named in `superlative_claims.checks` for all 12 peninsula panels even when that panel does
not display it. Skipping this makes the superlative checker pick a winner from a partial
pool and silently lie.

Include last month's values under `_previous` so the anomaly gates can fire:

```json
"sob-market": {
  "median_sold": 3100000, "median_ppsf": 1124.28, "median_dom": 32,
  "sales": 105, "high_sale": 21028560, "pct_under_30": 56,
  "total_volume": 414695447, "list_to_sale": 95.8,
  "_previous": { "median_sold": 3100000, "sales": 105 }
}
```

## Step 4 — Patch

```
python3 refresh.py --data data.json --dry-run    # inspect first
python3 refresh.py --data data.json
```

It aborts rather than publishing if: a panel is missing, a stat is missing, sales fall below
the floor, a median or count moves past the anomaly gate, the stat-cell count changes, div
balance breaks, or any banned active-listing stat appears.

It prints the current holder of each superlative. **Rewrite any prose naming a different
neighborhood.** Four claims on the April 2026 page were false and had been false when
written. Never carry a superlative forward.

## Step 5 — Update the prose

`refresh.py` only touches the 132 stat cells and the date stamps. The note under each panel
and the quick-facts row above it are prose and hold figures too. Re-read them against the
new numbers and rewrite anything now stale or contradicted.

**Hard rule from Jimmy, 2026-07-28: no active-listing data anywhere.** No active counts,
no active median list price, no low active list, no active median DOM. He consults this
page over a 30 to 60 day window and active inventory is stale the day it's entered.
`refresh.py` aborts if it finds any, but prose is on you.

## Step 6 — Publish

```
git add guide/
git commit -m "guide: <Month> <Year> market refresh"
git push
```

Cloudflare Pages is connected to this repo with root directory `guide`, so the push
triggers the deploy to guide.chshappenings.com. Nothing else is needed.

## Step 7 — Notify

Create a Todoist Inbox task, "Insider's Guide refreshed — <Month>", whose description lists:
every value that changed with old → new, the current superlative holders, anything the gates
flagged, and any panel whose sample dropped below 10 sales. If the gates aborted the run,
say so plainly in the title and do not push.
