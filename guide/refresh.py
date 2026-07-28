#!/usr/bin/env python3
"""
Charleston Insider's Guide — deterministic monthly patcher.

Usage:  python3 refresh.py --data data.json [--html index.html] [--dry-run]

Reads config.json (neighborhood definitions, stat layout, gates) and data.json
(this month's numbers, written by the scheduled Cowork session after it makes the
Flexmls MCP calls described in RECIPE.md), then patches index.html in place.

Design notes:
  * All formatting lives here, so the model never hand-formats a number.
  * All gates are enforced here, so a bad pull fails loudly instead of publishing.
  * Every superlative claim is recomputed, never carried forward. Four of them
    were false on the April 2026 page.
"""

import argparse, json, re, sys, datetime
from decimal import Decimal, ROUND_HALF_UP

# ---------------------------------------------------------------- formatting

def _half_up(x, places):
    """Python's round() is banker's rounding: 1.125 -> 1.12. The page uses half-up."""
    d = Decimal(str(x)).quantize(Decimal("1." + "0" * places) if places else Decimal("1"),
                                 rounding=ROUND_HALF_UP)
    return f"{d}"

def money(v):
    """House style, matched to the existing page:
       >=100M -> $649M | >=10M -> $61.3M, $21M | >=1M -> $2.53M | >=10K -> $870K | else $9,500"""
    v = float(v)
    if v >= 100_000_000:
        return f"${_half_up(v/1_000_000, 0)}M"
    if v >= 10_000_000:
        return f"${_half_up(v/1_000_000, 1).rstrip('0').rstrip('.')}M"
    if v >= 1_000_000:
        return f"${_half_up(v/1_000_000, 2).rstrip('0').rstrip('.')}M"
    if v >= 10_000:
        return f"${_half_up(v/1000, 0)}K"
    return f"${v:,.0f}"

def ppsf(v):
    return f"${float(v):,.0f}"

def days(v):
    v = float(v)
    s = f"{v:.1f}".rstrip("0").rstrip(".")
    return f"{s} days"

def pct(v):
    v = float(v)
    s = f"{v:.1f}".rstrip("0").rstrip(".")
    return f"{s}%"

def count(v):
    return f"{int(v):,}"

FORMATTERS = {
    "median_sold": money, "high_sale": money, "high_list": money,
    "entry_point": money, "attached_median": money, "total_volume": money,
    "median_ppsf": ppsf,
    "median_dom": days,
    "sales": count,
    "pct_under_30": pct, "pct_121_plus": pct, "list_to_sale": pct,
}

# ---------------------------------------------------------------- gates

def run_gates(cfg, data, html, errors, warnings):
    g = cfg["anomaly_gates"]
    for p in cfg["panels"]:
        pid = p["id"]
        d = data.get(pid)
        if not d:
            errors.append(f"{pid}: missing from data.json")
            continue
        for label, key in p["stats"]:
            if key not in d:
                errors.append(f"{pid}: missing stat '{key}'")
        if d.get("sales", 0) < g["min_sales_for_publish"]:
            errors.append(f"{pid}: only {d.get('sales')} sales, below floor of {g['min_sales_for_publish']}")
        prev = d.get("_previous", {})
        for key, limit in (("median_sold", g["median_sold_pct_change_abort"]),
                           ("sales", g["sales_count_pct_change_abort"])):
            if key in prev and prev[key]:
                change = abs(float(d[key]) - float(prev[key])) / float(prev[key]) * 100
                if change > limit:
                    errors.append(f"{pid}: {key} moved {change:.0f}% (limit {limit}%). "
                                  f"{prev[key]} -> {d[key]}. Verify before publishing.")
    n_boxes = html.count('<div class="n-stats-box">')
    if n_boxes != g["total_panels_expected"]:
        errors.append(f"HTML has {n_boxes} panels, expected {g['total_panels_expected']}")
    return errors, warnings

# ---------------------------------------------------------------- superlatives

def check_superlatives(cfg, data):
    """Return {claim_text: (winning_panel_name, value)} recomputed from this month's data."""
    out = {}
    ids = set(cfg["superlative_claims"]["peninsula_ids"])
    names = {p["id"]: p["name"] for p in cfg["panels"]}
    for chk in cfg["superlative_claims"]["checks"]:
        pool = [(pid, d.get(chk["metric"])) for pid, d in data.items()
                if pid in ids and d.get(chk["metric"]) is not None]
        if not pool:
            continue
        pick = (min if chk["direction"] == "min" else max)(pool, key=lambda t: float(t[1]))
        out[chk["claim"]] = (names.get(pick[0], pick[0]), pick[1])
    return out

# ---------------------------------------------------------------- patching

CELL = re.compile(r'(<div class="n-stat-val">)(.*?)(</div><div class="n-stat-lbl">)(.*?)(</div>)', re.S)

def panel_offsets(html):
    """Map section id -> offset of its n-stats-box."""
    boxes = [m.start() for m in re.finditer(r'<div class="n-stats-box">', html)]
    ids = [(m.start(), m.group(1)) for m in re.finditer(r'id="([a-z0-9\-]+)"', html)]
    return [(b, [i for i in ids if i[0] < b][-1][1]) for b in boxes]

def patch(cfg, data, html):
    changes = []
    plan = panel_offsets(html)
    by_id = {p["id"]: p for p in cfg["panels"]}
    # patch back-to-front so earlier offsets stay valid
    for off, pid in sorted(plan, key=lambda t: -t[0]):
        p, d = by_id.get(pid), data.get(pid)
        if not p or not d:
            continue
        end = html.find("n-stats-note", off)
        end = end if 0 < end < off + 4000 else off + 3000
        seg = html[off:end]
        cells = list(CELL.finditer(seg))
        if len(cells) != 6:
            raise SystemExit(f"{pid}: expected 6 stat cells, found {len(cells)}")
        for i in range(5, -1, -1):
            c, (label, key) = cells[i], p["stats"][i]
            newval = FORMATTERS[key](d[key])
            if c.group(2) != newval or c.group(4) != label:
                changes.append((pid, label, c.group(2), newval))
            seg = seg[:c.start()] + c.group(1) + newval + c.group(3) + label + c.group(5) + seg[c.end():]
        html = html[:off] + seg + html[end:]

    # date stamps
    now = datetime.date.today()
    month, year = now.strftime("%B"), now.strftime("%Y")
    html = re.sub(r'· [A-Z][a-z]+ \d{4} ·', f'· {month} {year} ·', html)
    return html, changes

# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data.json")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--html", default="index.html")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    cfg = json.load(open(a.config, encoding="utf-8"))
    data = json.load(open(a.data, encoding="utf-8"))
    html = open(a.html, encoding="utf-8").read()

    errors, warnings = run_gates(cfg, data, html, [], [])
    if errors:
        print("GATE FAILURES — nothing was written:\n  " + "\n  ".join(errors))
        sys.exit(2)

    sup = check_superlatives(cfg, data)
    print("Superlative holders recomputed this run:")
    for claim, (who, val) in sup.items():
        print(f"  {claim:48} -> {who} ({val})")
    print("  ^ rewrite any prose that names a different neighborhood for these.\n")

    new_html, changes = patch(cfg, data, html)

    if new_html.count("n-stat-val") - 1 != cfg["anomaly_gates"]["total_stat_cells_expected"]:
        print("ABORT: stat cell count changed during patch."); sys.exit(2)
    if new_html.count("<div") != new_html.count("</div>"):
        print("ABORT: div balance broken during patch."); sys.exit(2)
    for banned in ("Active Listings", "Low List Active", "Active Median DOM", "Active median"):
        if banned in new_html:
            print(f"ABORT: banned active-listing stat '{banned}' present. Jimmy's hard rule."); sys.exit(2)

    print(f"{len(changes)} values changed:")
    for pid, label, old, new in sorted(changes):
        print(f"  {pid:16} {label:22} {old:>12} -> {new}")

    if a.dry_run:
        print("\nDry run, nothing written.")
        return
    open(a.html, "w", encoding="utf-8").write(new_html)
    print(f"\nWrote {a.html} ({len(new_html):,} bytes).")

if __name__ == "__main__":
    main()
