#!/usr/bin/env python3
"""
Render the Isle of Palms / Wild Dunes new-listing watch page.

Usage:  python3 render_iop_watch.py listings.json out.html

listings.json shape:
{
  "run_date": "2026-08-03",
  "label": "Baseline"          # optional; omit for normal runs
  "listings": [ { ...StandardFields..., "MLSNumber": "...", "FlexmlsLink": "...",
                  "Photos": ["url", ...] }, ... ]
}

Brand: The Farrell Group — #003466 navy, #7095A7 slate, #ECD19C sand.
Fonts: Gangster Grotesk (display) + Montserrat (body).
"""
import json
import sys
import html
from datetime import date, datetime

NAVY = "#003466"
SLATE = "#7095A7"
SAND = "#ECD19C"
INK = "#12283c"
PAPER = "#f7f8fa"


def money(v):
    try:
        return "${:,.0f}".format(float(v))
    except (TypeError, ValueError):
        return "—"


def num(v, suffix=""):
    try:
        f = float(v)
        if f == int(f):
            return "{:,}{}".format(int(f), suffix)
        return "{:,.1f}{}".format(f, suffix)
    except (TypeError, ValueError):
        return "—"


def flat(v):
    """FlexMLS returns some fields as {"Value": true} dicts. Flatten to a list."""
    if isinstance(v, dict):
        return [k for k, on in v.items() if on]
    if isinstance(v, list):
        return v
    if v:
        return [str(v)]
    return []


def joined(v, sep=" · "):
    items = flat(v)
    return sep.join(items) if items else "—"


def esc(s):
    return html.escape(str(s)) if s is not None else ""


def pretty_date(s):
    if not s:
        return "—"
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").strftime("%b %-d, %Y")
    except ValueError:
        return str(s)[:10]


def card(l):
    f = l
    mls = f.get("MLSNumber") or f.get("ListingId") or ""
    addr = f.get("UnparsedAddress", "")
    street = addr.split(",")[0].strip() if addr else "Address unavailable"
    city_line = ", ".join(p.strip() for p in addr.split(",")[1:]) if "," in addr else ""

    price = f.get("ListPrice")
    orig = f.get("OriginalListPrice")
    sqft = f.get("BuildingAreaTotal")
    try:
        ppsf = "${:,.0f}/sf".format(float(price) / float(sqft))
    except (TypeError, ValueError, ZeroDivisionError):
        ppsf = "—"

    cut = ""
    try:
        if orig and float(orig) > float(price):
            drop = float(orig) - float(price)
            pct = drop / float(orig) * 100
            cut = ('<div class="cut">Price cut {} from {} · down {:.1f}%</div>'
                   .format(money(drop), money(orig), pct))
    except (TypeError, ValueError):
        pass

    photos = f.get("Photos") or []
    lead = photos[0] if photos else None
    gallery = photos[1:12]

    hero = ('<div class="hero"><img loading="lazy" src="{}" alt="{}"></div>'
            .format(esc(lead), esc(street)) if lead else
            '<div class="hero nophoto"><span>No photo available</span></div>')

    strip = ""
    if gallery:
        thumbs = "".join(
            '<a href="{u}" target="_blank" rel="noopener"><img loading="lazy" src="{u}" alt=""></a>'.format(u=esc(u))
            for u in gallery)
        strip = ('<div class="strip">{}</div>'
                 '<div class="stripnote">{} of {} photos · tap any to open full size</div>'
                 .format(thumbs, len(photos), f.get("PhotosCount") or len(photos)))

    baths = f.get("BathsTotal")
    bath_detail = ""
    if f.get("BathsFull") is not None:
        bath_detail = " ({} full{})".format(
            num(f.get("BathsFull")),
            ", {} half".format(num(f.get("BathsHalf"))) if f.get("BathsHalf") else "")

    chips = [
        ("Beds", num(f.get("BedsTotal"))),
        ("Baths", num(baths)),
        ("SqFt", num(sqft)),
        ("$/SF", ppsf),
        ("Lot", num(f.get("LotSizeAcres"), " ac")),
        ("Built", str(f.get("YearBuilt") or "—")),
        ("DOM", num(f.get("DaysOnMarket"))),
    ]
    chiphtml = "".join(
        '<div class="chip"><span class="k">{}</span><span class="v">{}</span></div>'.format(esc(k), esc(v))
        for k, v in chips)

    hoa = "—"
    if f.get("AssociationFee"):
        hoa = "{} {}".format(money(f.get("AssociationFee")),
                             (f.get("AssociationFeeFrequency") or "").lower())

    water = flat(f.get("WaterfrontFeatures")) + flat(f.get("View"))
    water_s = " · ".join(dict.fromkeys(water)) if water else "—"

    rows = [
        ("Area", f.get("MLSAreaMinor")),
        ("Subdivision", f.get("SubdivisionName")),
        ("Baths", (num(baths) + bath_detail) if baths is not None else "—"),
        ("Levels", joined(f.get("Levels"))),
        ("Water / view", water_s),
        ("HOA / regime", hoa),
        ("Annual taxes", money(f.get("TaxAnnualAmount")) if f.get("TaxAnnualAmount") else "—"),
        ("Garage spaces", num(f.get("GarageSpaces")) if f.get("GarageSpaces") else "—"),
        ("Roof", joined(f.get("Roof"))),
        ("Heat", joined(f.get("Heating"))),
        ("Cool", joined(f.get("Cooling"))),
        ("Flooring", joined(f.get("Flooring"))),
        ("Schools", " · ".join(x for x in [f.get("ElementarySchool"),
                                           f.get("MiddleOrJuniorSchool"),
                                           f.get("HighSchool")] if x) or "—"),
        ("MLS list date", pretty_date(f.get("ListingContractDate"))),
        ("Original list price", money(orig) if orig else "—"),
        ("Listing office", f.get("ListOfficeName")),
        ("Listing agent", f.get("ListAgentName")),
    ]
    rowhtml = "".join(
        '<div class="row"><dt>{}</dt><dd>{}</dd></div>'.format(esc(k), esc(v if v else "—"))
        for k, v in rows)

    remarks = (f.get("PublicRemarks") or "").strip()
    remarks_html = ('<div class="remarks"><h4>Public remarks</h4><p>{}</p></div>'
                    .format(esc(remarks).replace("\r\n", "<br>").replace("\n", "<br>"))
                    if remarks else "")

    link = f.get("FlexmlsLink") or "https://members.flexmls.com/start/listing/number/index.html?list=" + esc(mls)

    return """
<article class="card">
  {hero}
  <div class="body">
    <div class="head">
      <div>
        <h3>{street}</h3>
        <div class="sub">{city} · MLS #{mls}</div>
      </div>
      <div class="pricebox">
        <div class="price">{price}</div>
        <div class="ppsf">{ppsf}</div>
      </div>
    </div>
    {cut}
    <div class="chips">{chips}</div>
    {strip}
    <dl class="grid">{rows}</dl>
    {remarks}
    <a class="btn" href="{link}" target="_blank" rel="noopener">Open in Flexmls →</a>
  </div>
</article>""".format(hero=hero, street=esc(street), city=esc(city_line), mls=esc(mls),
                     price=money(price), ppsf=ppsf, cut=cut, chips=chiphtml,
                     strip=strip, rows=rowhtml, remarks=remarks_html, link=link)


def render(data):
    listings = data.get("listings", [])
    run_date = data.get("run_date") or date.today().isoformat()
    label = data.get("label", "")
    try:
        pretty_run = datetime.strptime(run_date, "%Y-%m-%d").strftime("%A, %B %-d, %Y")
    except ValueError:
        pretty_run = run_date

    prices = [float(l["ListPrice"]) for l in listings if l.get("ListPrice")]
    lo, hi = (money(min(prices)), money(max(prices))) if prices else ("—", "—")
    a44 = sum(1 for l in listings if str(l.get("MLSAreaMinor", "")).startswith("44"))
    a45 = sum(1 for l in listings if str(l.get("MLSAreaMinor", "")).startswith("45"))

    ppsfs = []
    for l in listings:
        try:
            ppsfs.append(float(l["ListPrice"]) / float(l["BuildingAreaTotal"]))
        except (TypeError, ValueError, ZeroDivisionError, KeyError):
            pass
    ppsfs.sort()
    med = "${:,.0f}/sf".format(ppsfs[len(ppsfs) // 2]) if ppsfs else "—"

    stats = [("Listings", str(len(listings))), ("Area 44", str(a44)), ("Area 45", str(a45)),
             ("Low", lo), ("High", hi), ("Median $/SF", med)]
    stathtml = "".join(
        '<div class="stat"><div class="n">{}</div><div class="l">{}</div></div>'.format(esc(v), esc(k))
        for k, v in stats)

    cards = "\n".join(card(l) for l in listings) if listings else \
        '<div class="empty">No new listings met the criteria on this run</div>'

    badge = '<span class="badge">{}</span>'.format(esc(label)) if label else ""

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>New Listings Watch · Isle of Palms + Wild Dunes · {run_date}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Gangster+Grotesk:wght@400;500;700&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --navy:{navy}; --slate:{slate}; --sand:{sand}; --ink:{ink}; --paper:{paper};
  }}
  * {{ box-sizing:border-box; }}
  body {{
    margin:0; background:var(--paper); color:var(--ink);
    font-family:'Montserrat',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    font-size:15px; line-height:1.55; -webkit-font-smoothing:antialiased;
  }}
  h1,h2,h3,h4,.price,.n {{ font-family:'Gangster Grotesk','Montserrat',sans-serif; }}
  header {{ background:var(--navy); color:#fff; padding:34px 20px 30px; }}
  .wrap {{ max-width:820px; margin:0 auto; }}
  header .eyebrow {{
    font-size:11px; letter-spacing:.18em; text-transform:uppercase;
    color:var(--sand); font-weight:600; margin-bottom:10px;
  }}
  header h1 {{ margin:0 0 6px; font-size:31px; line-height:1.15; font-weight:700; letter-spacing:-.01em; }}
  header .date {{ color:#cfe0ea; font-size:14px; margin-bottom:16px; }}
  .badge {{
    display:inline-block; background:var(--sand); color:var(--navy);
    font-size:10px; font-weight:700; letter-spacing:.14em; text-transform:uppercase;
    padding:4px 10px; border-radius:3px; margin-left:10px; vertical-align:middle;
  }}
  .criteria {{
    background:rgba(255,255,255,.09); border-left:3px solid var(--sand);
    padding:12px 16px; border-radius:0 4px 4px 0; font-size:13px; color:#dce9f0;
  }}
  .criteria b {{ color:#fff; font-weight:600; }}
  .stats {{
    display:grid; grid-template-columns:repeat(6,1fr); gap:1px;
    background:#dfe5ea; border-bottom:1px solid #dfe5ea;
  }}
  .stat {{ background:#fff; padding:16px 8px; text-align:center; }}
  .stat .n {{ font-size:20px; font-weight:700; color:var(--navy); line-height:1.1; }}
  .stat .l {{
    font-size:9.5px; letter-spacing:.1em; text-transform:uppercase;
    color:var(--slate); margin-top:5px; font-weight:600;
  }}
  main {{ max-width:820px; margin:0 auto; padding:26px 16px 60px; }}
  .card {{
    background:#fff; border:1px solid #e2e7ec; border-radius:8px;
    overflow:hidden; margin-bottom:26px; box-shadow:0 1px 3px rgba(0,52,102,.06);
  }}
  .hero img {{ width:100%; display:block; aspect-ratio:4/3; object-fit:cover; background:#e8edf1; }}
  .hero.nophoto {{
    aspect-ratio:4/3; background:#e8edf1; display:flex; align-items:center;
    justify-content:center; color:var(--slate); font-size:13px;
  }}
  .body {{ padding:20px; }}
  .head {{ display:flex; justify-content:space-between; align-items:flex-start; gap:14px; }}
  .head h3 {{ margin:0; font-size:21px; line-height:1.2; color:var(--navy); font-weight:700; }}
  .sub {{ font-size:12px; color:var(--slate); margin-top:4px; letter-spacing:.02em; }}
  .pricebox {{ text-align:right; flex-shrink:0; }}
  .price {{ font-size:22px; font-weight:700; color:var(--navy); line-height:1.1; }}
  .ppsf {{ font-size:12px; color:var(--slate); margin-top:2px; }}
  .cut {{
    margin-top:12px; background:#fdf3e3; border-left:3px solid var(--sand);
    padding:8px 12px; font-size:12.5px; font-weight:600; color:#8a6224; border-radius:0 3px 3px 0;
  }}
  .chips {{ display:flex; flex-wrap:wrap; gap:7px; margin:16px 0 4px; }}
  .chip {{
    background:var(--paper); border:1px solid #e2e7ec; border-radius:5px;
    padding:6px 10px; display:flex; gap:6px; align-items:baseline;
  }}
  .chip .k {{ font-size:9.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--slate); font-weight:600; }}
  .chip .v {{ font-size:13.5px; font-weight:600; color:var(--navy); }}
  .strip {{
    display:flex; gap:6px; overflow-x:auto; margin:16px -20px 4px; padding:0 20px 6px;
    scrollbar-width:thin;
  }}
  .strip img {{
    height:78px; width:104px; object-fit:cover; border-radius:4px;
    flex-shrink:0; background:#e8edf1; border:1px solid #e2e7ec;
  }}
  .stripnote {{ font-size:11px; color:var(--slate); margin-bottom:4px; }}
  .grid {{
    margin:18px 0 0; display:grid; grid-template-columns:1fr 1fr;
    gap:0 22px; border-top:1px solid #eef1f4; padding-top:6px;
  }}
  .row {{ display:flex; justify-content:space-between; gap:12px; padding:7px 0; border-bottom:1px solid #f2f4f7; }}
  .row dt {{ font-size:11px; letter-spacing:.05em; text-transform:uppercase; color:var(--slate); font-weight:600; flex-shrink:0; }}
  .row dd {{ margin:0; font-size:13px; text-align:right; font-weight:500; }}
  .remarks {{ margin-top:18px; background:var(--paper); border-radius:6px; padding:14px 16px; }}
  .remarks h4 {{
    margin:0 0 8px; font-size:10.5px; letter-spacing:.12em; text-transform:uppercase;
    color:var(--slate); font-weight:700;
  }}
  .remarks p {{ margin:0; font-size:13.5px; line-height:1.65; color:#33465a; }}
  .btn {{
    display:inline-block; margin-top:18px; background:var(--navy); color:#fff;
    text-decoration:none; padding:11px 20px; border-radius:5px;
    font-size:13px; font-weight:600; letter-spacing:.02em;
  }}
  .empty {{
    background:#fff; border:1px solid #e2e7ec; border-radius:8px;
    padding:44px 20px; text-align:center; color:var(--slate); font-size:15px;
  }}
  footer {{
    max-width:820px; margin:0 auto; padding:0 16px 50px;
    font-size:11.5px; color:var(--slate); line-height:1.7;
  }}
  footer strong {{ color:var(--navy); }}
  @media (max-width:620px) {{
    header h1 {{ font-size:25px; }}
    .stats {{ grid-template-columns:repeat(3,1fr); }}
    .grid {{ grid-template-columns:1fr; }}
    .head {{ flex-direction:column; }}
    .pricebox {{ text-align:left; }}
  }}
</style>
</head>
<body>
<header>
  <div class="wrap">
    <div class="eyebrow">The Farrell Group · Listing Watch</div>
    <h1>Isle of Palms + Wild Dunes{badge}</h1>
    <div class="date">{pretty_run}</div>
    <div class="criteria">
      <b>Areas</b> 44 (Isle of Palms) + 45 (Wild Dunes) &nbsp;·&nbsp;
      <b>Type</b> Single Family Detached &nbsp;·&nbsp;
      <b>Beds</b> 4+ &nbsp;·&nbsp;
      <b>Price</b> $1,000,000 – $2,600,000 &nbsp;·&nbsp;
      <b>Status</b> Active
    </div>
  </div>
</header>
<div class="stats">{stats}</div>
<main>{cards}</main>
<footer>
  <strong>The Farrell Group</strong> · Generated {pretty_run} from Charleston Trident MLS via Flexmls.
  Data deemed reliable but not guaranteed. Listings shown are the property of their respective
  listing brokerages, credited on each card. This page is an internal working document, not an advertisement.
</footer>
</body>
</html>""".format(navy=NAVY, slate=SLATE, sand=SAND, ink=INK, paper=PAPER,
                  run_date=esc(run_date), pretty_run=esc(pretty_run),
                  badge=badge, stats=stathtml, cards=cards)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: render_iop_watch.py listings.json out.html")
        sys.exit(1)
    with open(sys.argv[1]) as fh:
        data = json.load(fh)
    with open(sys.argv[2], "w") as fh:
        fh.write(render(data))
    print("wrote {} ({} listings)".format(sys.argv[2], len(data.get("listings", []))))
