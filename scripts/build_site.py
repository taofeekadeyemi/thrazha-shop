#!/usr/bin/env python3
"""
Rebuilds index.html (Thrazha Bazaar) from data/products.csv.

Run this locally with: python3 scripts/build_site.py
(It also runs automatically via GitHub Actions whenever data/products.csv changes —
see .github/workflows/build.yml — so most of the time you never need to run it yourself.)

Design: "Thrazha Bazaar" redesign (Sept 2026), implementing the Claude Design handoff
(design_handoff_thrazha_bazaar/README.md + STYLE_GUIDE.md). Colors, type and spacing
values below are copied literally from STYLE_GUIDE.md — don't round them.

To add/edit inventory, edit data/products.csv. Columns:
  id, title, category, qty, price_min, price_max, status, lots, photo, condition
`condition` is one of: New, sealed / Open box / Customer return / Renewed / Overstock.
If you leave it blank, items default to "Overstock" — update it as you grade items.
"""
import csv, html, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "data", "products.csv")
OUT_PATH = os.path.join(ROOT, "index.html")

CATEGORY_ORDER = [
    "Footwear", "Apparel & Clothing", "Electronics", "Home & Kitchen",
    "Bags & Accessories", "Baby & Kids", "Health & Fitness",
]

# Chip label shown in the catalogue toolbar -> real category value in the CSV.
CHIP_LABELS = {
    "Footwear": "Footwear",
    "Apparel & Clothing": "Apparel",
    "Electronics": "Electronics",
    "Home & Kitchen": "Home & Kitchen",
    "Bags & Accessories": "Bags & Accessories",
    "Baby & Kids": "Baby & Kids",
    "Health & Fitness": "Health & Fitness",
}

VALID_STATUSES = {"available", "sold", "coming_soon"}
VALID_CONDITIONS = {"New, sealed", "Open box", "Customer return", "Renewed", "Overstock"}
FIELDNAMES = ["id", "title", "category", "qty", "price_min", "price_max", "status", "lots", "photo", "condition"]


def ensure_condition_column(path):
    """Back-compat migration: adds a `condition` column (default Overstock) the first
    time this runs against an older products.csv that doesn't have one yet."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        had_condition = reader.fieldnames and "condition" in reader.fieldnames
    if had_condition:
        return
    for row in rows:
        row["condition"] = "Overstock"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def load_products(path):
    ensure_condition_column(path)
    products = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["qty"] = int(row["qty"])
            row["price_min"] = float(row["price_min"])
            row["price_max"] = float(row["price_max"])
            row["lots"] = row["lots"].split(";") if row["lots"] else []
            row["has_photo"] = bool(row["photo"].strip())
            status = (row.get("status") or "available").strip().lower()
            row["status"] = status if status in VALID_STATUSES else "available"
            cond = (row.get("condition") or "").strip()
            row["condition"] = cond if cond in VALID_CONDITIONS else "Overstock"
            products.append(row)
    return products


def title_case(t):
    words = t.split()
    out = []
    for w in words:
        if re.match(r"^[\d.]+$", w) or re.search(r"\d", w) or (w.isupper() and len(w) <= 4):
            out.append(w)
        else:
            out.append(w.capitalize())
    return " ".join(out)


def fmt_price(p):
    if p == int(p):
        return f"${int(p)}"
    return f"${p:,.2f}"


def price_label(item):
    if item["price_min"] == item["price_max"]:
        return fmt_price(item["price_min"])
    return f"{fmt_price(item['price_min'])} – {fmt_price(item['price_max'])}"


def unit_label(item):
    return "1 of 1" if item["qty"] <= 1 else f"{item['qty']} units"


def img_src(item):
    return item["photo"].strip() if item["has_photo"] else ""


def to_card_dict(item):
    """Shape passed to the client-side renderer (kept close to the design's RAW schema)."""
    return {
        "id": item["id"],
        "title": title_case(item["title"]),
        "category": item["category"],
        "chip": CHIP_LABELS.get(item["category"], item["category"]),
        "price": item["price_max"],
        "priceLabel": price_label(item),
        "img": img_src(item),
        "condition": item["condition"],
        "qty": item["qty"],
        "unitLabel": unit_label(item),
        "status": item["status"],
    }


def main():
    products = load_products(CSV_PATH)
    available = [p for p in products if p["status"] == "available"]

    unique_items = len(available)
    units_in_stock = sum(p["qty"] for p in available)
    lowest_price = min((p["price_min"] for p in available), default=0)
    departments = len({p["category"] for p in available if p["category"] in CATEGORY_ORDER})

    cards = [to_card_dict(p) for p in products]
    cards_available = [c for c in cards if c["status"] == "available"]

    # New arrivals: most recently added available rows (CSV append order = newest last).
    arrivals = cards_available[-8:][::-1]

    # The vault: five highest-priced available items.
    featured = sorted(cards_available, key=lambda c: c["price"], reverse=True)[:5]

    # Hero right column: top product + next two by price.
    by_price = sorted(cards_available, key=lambda c: c["price"], reverse=True)
    top_product = by_price[0] if by_price else None
    side_tiles = by_price[1:3]

    products_json = json.dumps(cards, ensure_ascii=False)
    chips_json = json.dumps(
        ["All items"] + [CHIP_LABELS[c] for c in CATEGORY_ORDER if any(p["category"] == c for p in available)],
        ensure_ascii=False,
    )

    def esc(s):
        return html.escape(str(s))

    def mini_card_html(c, badge=None, width_class=""):
        img = f'<img src="{esc(c["img"])}" alt="{esc(c["title"])}" loading="lazy">' if c["img"] else ""
        badge_html = f'<span class="badge-new">{esc(badge)}</span>' if badge else ""
        return f"""<div class="rail-card {width_class}" data-id="{esc(c['id'])}">
      <div class="rail-img">{img}{badge_html}</div>
      <div class="rail-body">
        <p class="rail-cat">{esc(c['chip'])}</p>
        <p class="rail-title">{esc(c['title'])}</p>
        <p class="rail-price">{esc(c['priceLabel'])}</p>
      </div>
    </div>"""

    def featured_card_html(c):
        img = f'<img src="{esc(c["img"])}" alt="{esc(c["title"])}" loading="lazy">' if c["img"] else ""
        return f"""<div class="feat-card">
      <div class="feat-img">{img}</div>
      <div class="feat-body">
        <p class="feat-cat">{esc(c['chip'])}</p>
        <p class="feat-title">{esc(c['title'])}</p>
        <p class="feat-price">{esc(c['priceLabel'])}</p>
        <button class="btn-reserve-solid" data-reserve="{esc(c['id'])}">Reserve this item</button>
      </div>
    </div>"""

    arrivals_html = "\n".join(mini_card_html(c, badge="NEW IN") for c in arrivals)
    featured_html = "\n".join(featured_card_html(c) for c in featured)

    top_img = f'<img src="{esc(top_product["img"])}" alt="{esc(top_product["title"])}" loading="lazy">' if top_product and top_product["img"] else ""
    tile_imgs = "".join(
        f'<div class="hero-tile"><img src="{esc(t["img"])}" alt="{esc(t["title"])}" loading="lazy"></div>' if t["img"] else '<div class="hero-tile"></div>'
        for t in side_tiles
    )

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Thrazha Bazaar | Overstock, Returns &amp; Auction Finds</title>
<meta name="description" content="Thrazha Bazaar — premium-brand overstock, open-box and customer-return inventory at outlet prices. New items every week. A Thrazha International company.">
<link rel="icon" href="thrazha-logo.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=Source+Serif+4:wght@400;600;700&family=Manrope:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
{CSS}
</style>
</head>
<body>

<div class="announce">
  <span>New items added weekly</span>
  <span class="ann-accent">Inspected before listing</span>
  <span>Local pickup · Shipping Canada-wide</span>
</div>

<header class="site-header" id="top">
  <div class="header-inner">
    <a href="#top" class="brand">
      <img src="thrazha-logo.png" alt="Thrazha" class="brand-mark">
      <span class="brand-text">
        <span class="brand-word">THRAZHA BAZAAR</span>
        <span class="brand-sub">A Thrazha International company</span>
      </span>
    </a>
    <nav class="main-nav">
      <a href="#catalogue">Catalogue</a>
      <a href="#how-it-works">How it works</a>
      <a href="#pickup">Pickup &amp; delivery</a>
      <a href="https://www.thrazha.ca" class="nav-out">Thrazha.ca ↗</a>
      <button class="watchlist-pill" id="watchlistBtn" type="button">
        Watchlist <span class="watchlist-count" id="watchlistCount">0</span>
      </button>
    </nav>
  </div>
</header>

<section class="hero">
  <div class="hero-inner">
    <div class="hero-copy">
      <div class="eyebrow-pill"><span class="dot"></span>{unique_items} items in stock</div>
      <h1>Premium brands.<br>Outlet prices.</h1>
      <p class="hero-body">Overstock, open-box and customer-return inventory from name brands —
      footwear, apparel, electronics, home essentials and more. Every item is opened, tested
      and condition-tagged.</p>
      <div class="hero-buttons">
        <a href="#catalogue" class="btn-primary">Browse the catalogue</a>
        <a href="#how-it-works" class="btn-secondary">How it works</a>
      </div>
      <div class="hero-stats">
        <div class="stat"><strong>{unique_items}</strong><span>Unique items</span></div>
        <div class="stat"><strong>{units_in_stock}</strong><span>Units in stock</span></div>
        <div class="stat"><strong>{fmt_price(lowest_price)}</strong><span>Lowest price</span></div>
        <div class="stat"><strong>{departments}</strong><span>Departments</span></div>
      </div>
    </div>
    <div class="hero-visual">
      <div class="top-product-bar">Today's top product — {esc(top_product['title']) if top_product else ''} · {esc(top_product['priceLabel']) if top_product else ''}</div>
      <div class="hero-feature">{top_img}</div>
      <div class="hero-tiles">{tile_imgs}</div>
    </div>
  </div>
</section>

<section class="trust-strip">
  <div class="trust-inner">
    <div class="trust-cell"><div class="trust-num">01</div><p class="trust-title">Graded before listing</p><p class="trust-body">Every item is opened, tested and condition-tagged before it goes up.</p></div>
    <div class="trust-cell"><div class="trust-num">02</div><p class="trust-title">Hold it for 48 hours</p><p class="trust-body">Reserve any item and we hold it — no payment required up front.</p></div>
    <div class="trust-cell"><div class="trust-num">03</div><p class="trust-title">One-of-one stock</p><p class="trust-body">Most items are single units. Once it's reserved, it's gone.</p></div>
    <div class="trust-cell"><div class="trust-num">04</div><p class="trust-title">Backed by Thrazha</p><p class="trust-body">Part of Thrazha International Inc., trading since day one on straight answers.</p></div>
  </div>
</section>

<section class="arrivals">
  <div class="arrivals-head">
    <div>
      <p class="eyebrow eyebrow-dark">JUST LANDED</p>
      <h2>New arrivals this week</h2>
    </div>
    <span class="scroll-meta">Scroll →</span>
  </div>
  <div class="rail">
    {arrivals_html}
  </div>
</section>

<section class="vault" id="vault">
  <div class="vault-head">
    <div>
      <p class="eyebrow">THE VAULT</p>
      <h2>The pieces worth coming in for</h2>
    </div>
    <a href="#catalogue" class="see-all">See all {unique_items} items →</a>
  </div>
  <div class="vault-grid">
    {featured_html}
  </div>
</section>

<section class="catalogue" id="catalogue">
  <div class="cat-head">
    <div>
      <p class="eyebrow">THE CATALOGUE</p>
      <h2>The full inventory</h2>
    </div>
    <span class="cat-meta" id="resultMeta">{unique_items} items shown / {unique_items} total</span>
  </div>

  <div class="toolbar" id="toolbar">
    <div class="search-field">
      <span class="search-slash">/</span>
      <input type="text" id="searchInput" placeholder="Search brand, size or item…" autocomplete="off">
    </div>
    <select id="sortSelect" class="sort-select">
      <option value="featured">Curated</option>
      <option value="low">Price low → high</option>
      <option value="high">Price high → low</option>
      <option value="az">A–Z</option>
    </select>
    <div class="chips" id="chipRow"></div>
  </div>

  <div class="product-grid" id="productGrid"></div>
  <div class="empty-state" id="emptyState" hidden>
    <p class="empty-title">Nothing matches that yet.</p>
    <p class="empty-body">New items land every week — check back soon or clear your filters.</p>
    <button class="btn-clear" id="clearFilters">Clear filters</button>
  </div>
</section>

<section class="how-it-works" id="how-it-works">
  <p class="eyebrow eyebrow-dark">HOW IT WORKS</p>
  <h2>Three steps, no bidding wars.</h2>
  <div class="steps">
    <div class="step"><div class="step-num">1</div><p class="step-title">Browse &amp; reserve</p><p class="step-body">Find something in the catalogue and reserve it — no payment now.</p></div>
    <div class="step"><div class="step-num">2</div><p class="step-title">We confirm condition</p><p class="step-body">We hold the item for 48 hours while we confirm condition with you.</p></div>
    <div class="step"><div class="step-num">3</div><p class="step-title">Pick up or ship</p><p class="step-body">Collect it in person or have it shipped Canada-wide.</p></div>
  </div>
</section>

<section class="pickup" id="pickup">
  <div class="pickup-grid">
    <div class="pickup-terms">
      <div class="term-row"><span class="term-label">Pickup window</span><span class="term-value">Tue – Sat, 10:00 – 18:00</span></div>
      <div class="term-row"><span class="term-label">Local delivery</span><span class="term-value">Flat $15 within city</span></div>
      <div class="term-row"><span class="term-label">Canada-wide</span><span class="term-value">Quoted per item</span></div>
      <a href="mailto:hello@thrazha.ca" class="btn-outline-dark">Email us: hello@thrazha.ca</a>
    </div>
    <div class="stock-alerts">
      <h3>Stock alerts</h3>
      <p class="alerts-body">Tell us what you're hunting for and we'll email you when it lands.</p>
      <form id="alertForm">
        <input type="email" placeholder="Email address" required id="alertEmail">
        <select id="alertCategory">
          <option value="">What are you hunting?</option>
          {"".join(f'<option value="{esc(CHIP_LABELS[c])}">{esc(CHIP_LABELS[c])}</option>' for c in CATEGORY_ORDER)}
        </select>
        <button type="submit" id="alertSubmit">Notify me</button>
      </form>
    </div>
  </div>
</section>

<footer class="site-footer">
  <div class="footer-grid">
    <div class="footer-brand">
      <img src="thrazha-logo.png" alt="Thrazha" class="footer-mark">
      <span class="footer-word">THRAZHA BAZAAR</span>
      <p class="footer-tag">Overstock, returns and auction finds. Shipping Canada-wide.</p>
    </div>
    <div class="footer-col">
      <p class="footer-heading">Shop</p>
      <a href="#catalogue">Catalogue</a>
      <a href="#vault">The vault</a>
      <a href="#how-it-works">How it works</a>
    </div>
    <div class="footer-col">
      <p class="footer-heading">Company</p>
      <a href="https://www.thrazha.ca">Thrazha.ca</a>
      <a href="https://www.thrazha.ca/about.html">About</a>
      <a href="https://www.thrazha.ca/services.html">Services</a>
      <a href="https://www.thrazha.ca/contact.html">Contact</a>
    </div>
    <div class="footer-col">
      <p class="footer-heading">Get in touch</p>
      <a href="mailto:hello@thrazha.ca">hello@thrazha.ca</a>
      <a href="returns.html">Returns &amp; holds policy</a>
      <a href="conditions.html">Condition grades</a>
    </div>
  </div>
  <div class="legal-bar">
    <span>© 2026 Thrazha International Inc.</span>
    <span>Prices in CAD · Condition graded per item</span>
  </div>
</footer>

<div class="sheet-overlay" id="sheetOverlay">
  <div class="sheet" id="sheet">
    <div class="sheet-header">
      <img id="sheetImg" class="sheet-thumb" src="" alt="">
      <div class="sheet-info">
        <p class="sheet-meta" id="sheetMeta"></p>
        <p class="sheet-title" id="sheetTitle"></p>
        <p class="sheet-price" id="sheetPrice"></p>
      </div>
      <button class="sheet-close" id="sheetClose" type="button">×</button>
    </div>
    <div class="sheet-body" id="sheetForm">
      <form id="reserveForm">
        <input type="text" placeholder="Your name" required id="rName">
        <input type="text" placeholder="Email or phone" required id="rContact">
        <select id="rFulfilment">
          <option value="Pickup Tue–Sat">Pickup Tue–Sat</option>
          <option value="Local delivery $15">Local delivery $15</option>
          <option value="Ship Canada-wide — quote me">Ship Canada-wide — quote me</option>
        </select>
        <textarea placeholder="Anything we should know? (optional)" id="rNote" rows="3"></textarea>
        <button type="submit" class="btn-hold">Hold this item for 48 hours</button>
        <p class="sheet-fineprint">No payment now. We confirm condition first.</p>
      </form>
    </div>
    <div class="sheet-done" id="sheetDone" hidden>
      <p class="done-title">Held for 48 hours.</p>
      <p class="done-body">We've opened an email to our team with your details — send it and
      we'll confirm within one business day.</p>
      <button class="btn-outline-dark" id="sheetDoneClose" type="button">Close</button>
    </div>
  </div>
</div>

<script>
window.__PRODUCTS__ = {products_json};
window.__CHIPS__ = {chips_json};
{JS}
</script>
</body>
</html>
"""

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"Wrote {OUT_PATH} — {unique_items} items, {units_in_stock} units, {departments} departments")


CSS = r"""
:root{
  --olive:#3E4C1E; --ink:#1B1E10; --olive-mid:#6E8038; --olive-deep-ink:#4E5A22;
  --leaf:#A8C23F; --leaf-hover:#B9D256; --leaf-light:#C9DE86;
  --paper:#FDFCF4; --paper-sunk:#F3F2E4; --line:#E0DECB; --body-muted:#4F5340; --meta-muted:#63644B;
}
*{box-sizing:border-box;}
html{scroll-behavior:smooth;}
body{margin:0;background:var(--paper);color:var(--ink);font-family:Manrope,sans-serif;font-size:16px;line-height:1.6;}
a{color:inherit;text-decoration:none;}
h1,h2{font-family:'Source Serif 4',serif;font-weight:700;text-wrap:pretty;margin:0;}
p{margin:0;text-wrap:pretty;}
button,select,input,textarea{font-family:inherit;}
img{display:block;max-width:100%;}
.eyebrow{font-family:'IBM Plex Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:.14em;color:var(--olive-deep-ink);margin-bottom:8px;}
.eyebrow-dark{color:var(--leaf-light);}

.announce{background:var(--ink);color:#F3F2E4;display:flex;flex-wrap:wrap;justify-content:center;gap:10px 28px;padding:10px 20px;font-family:'IBM Plex Mono',monospace;font-size:12px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;}
.ann-accent{color:var(--leaf-light);}

.site-header{position:sticky;top:0;z-index:40;background:rgba(253,252,244,.92);backdrop-filter:blur(12px);border-bottom:1px solid var(--line);}
.header-inner{max-width:1280px;margin:0 auto;padding:12px 20px;display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap;}
.brand{display:flex;align-items:center;gap:10px;}
.brand-mark{width:40px;height:40px;object-fit:contain;}
.brand-text{display:flex;flex-direction:column;}
.brand-word{font-family:Cinzel,serif;font-weight:700;font-size:18px;letter-spacing:.06em;}
.brand-sub{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.14em;color:var(--meta-muted);}
.main-nav{display:flex;align-items:center;gap:22px;flex-wrap:wrap;}
.main-nav a{font-size:14px;font-weight:600;}
.main-nav a.nav-out{color:var(--meta-muted);}
.watchlist-pill{background:var(--paper-sunk);border:1px solid var(--line);border-radius:999px;padding:9px 16px;font-size:14px;font-weight:600;display:flex;align-items:center;gap:8px;cursor:pointer;}
.watchlist-count{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:999px;background:var(--olive);color:var(--paper-sunk);font-family:'IBM Plex Mono',monospace;font-size:12px;}

.hero{background:var(--olive);background-image:radial-gradient(circle at 82% 18%, rgba(168,194,63,.22), transparent 55%);padding:76px 20px 64px;}
.hero-inner{max-width:1280px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:56px;}
.eyebrow-pill{display:inline-flex;align-items:center;gap:8px;border:1px solid rgba(243,242,228,.3);border-radius:999px;padding:7px 14px;font-family:'IBM Plex Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:.14em;color:var(--leaf-light);margin-bottom:20px;}
.eyebrow-pill .dot{width:7px;height:7px;border-radius:999px;background:var(--leaf);}
.hero h1{color:var(--paper);font-size:clamp(40px,6.4vw,74px);line-height:1.02;letter-spacing:-.025em;margin-bottom:22px;}
.hero-body{color:rgba(243,242,228,.82);font-size:clamp(16px,1.6vw,19px);line-height:1.6;max-width:46ch;margin-bottom:28px;}
.hero-buttons{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:44px;}
.btn-primary{background:var(--leaf);color:var(--ink);border-radius:10px;padding:15px 26px;font-weight:700;font-size:15px;}
.btn-primary:hover{background:var(--leaf-hover);}
.btn-secondary{border:1px solid rgba(243,242,228,.35);color:var(--paper);border-radius:10px;padding:15px 26px;font-weight:700;font-size:15px;}
.btn-secondary:hover{border-color:var(--leaf-light);color:var(--leaf-light);}
.hero-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));border-top:1px solid rgba(243,242,228,.16);padding-top:22px;}
.stat strong{display:block;font-family:'Source Serif 4',serif;font-weight:700;font-size:30px;color:var(--leaf-light);}
.stat span{display:block;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.12em;color:rgba(243,242,228,.7);margin-top:4px;}
.hero-visual{display:grid;grid-template-columns:1fr 1fr;gap:14px;align-content:start;}
.top-product-bar{grid-column:1/-1;background:rgba(243,242,228,.06);border:1px solid rgba(243,242,228,.14);border-radius:16px;padding:14px 16px;color:var(--paper);font-size:13px;font-weight:600;}
.hero-feature{grid-column:1/-1;aspect-ratio:16/11;background:var(--paper-sunk);border-radius:16px;overflow:hidden;display:flex;align-items:center;justify-content:center;}
.hero-feature img{width:100%;height:100%;object-fit:cover;}
.hero-tiles{grid-column:1/-1;display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.hero-tile{aspect-ratio:1;background:var(--paper-sunk);border-radius:16px;overflow:hidden;}
.hero-tile img{width:100%;height:100%;object-fit:cover;}

.trust-strip{border-bottom:1px solid var(--line);}
.trust-inner{max-width:1280px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:26px;padding:26px 20px;}
.trust-num{width:30px;height:30px;background:var(--paper-sunk);border:1px solid var(--line);border-radius:8px;display:flex;align-items:center;justify-content:center;font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--olive-mid);margin-bottom:10px;}
.trust-title{font-size:14px;font-weight:700;margin-bottom:4px;}
.trust-body{font-size:13px;line-height:1.5;color:var(--meta-muted);}

.arrivals{max-width:1280px;margin:0 auto;padding:52px 20px;}
.arrivals-head,.vault-head,.cat-head{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;margin-bottom:24px;flex-wrap:wrap;}
.arrivals h2,.vault-head h2{font-size:clamp(26px,3.2vw,38px);letter-spacing:-.02em;}
.scroll-meta,.cat-meta{font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--meta-muted);}
.rail{display:flex;gap:14px;overflow-x:auto;scroll-snap-type:x proximity;padding-bottom:6px;}
.rail-card{flex:none;width:210px;scroll-snap-align:start;border:1px solid var(--line);border-radius:14px;overflow:hidden;background:var(--paper);}
.rail-img{position:relative;aspect-ratio:1;background:#fff;display:flex;align-items:center;justify-content:center;}
.rail-img img{width:100%;height:100%;object-fit:contain;padding:10px;}
.badge-new{position:absolute;top:8px;left:8px;background:var(--leaf);color:var(--ink);font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;padding:5px 8px;border-radius:6px;}
.rail-body{padding:13px 14px;}
.rail-cat{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:var(--meta-muted);margin-bottom:4px;}
.rail-title{font-size:13px;font-weight:600;line-height:1.35;margin-bottom:6px;}
.rail-price{font-family:'Source Serif 4',serif;font-weight:700;font-size:16px;color:var(--olive);}

.vault{background:var(--paper-sunk);padding:52px 20px;}
.vault-head,.vault-grid{max-width:1280px;margin:0 auto;}
.see-all{font-size:14px;font-weight:700;color:var(--olive);}
.vault-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:16px;}
.feat-card{background:var(--paper);border:1px solid var(--line);border-radius:16px;overflow:hidden;display:flex;flex-direction:column;}
.feat-img{aspect-ratio:1;background:#fff;display:flex;align-items:center;justify-content:center;}
.feat-img img{width:100%;height:100%;object-fit:contain;padding:10px;}
.feat-body{padding:14px 15px;display:flex;flex-direction:column;gap:4px;}
.feat-cat{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:var(--meta-muted);}
.feat-title{font-size:13px;font-weight:600;line-height:1.35;}
.feat-price{font-family:'Source Serif 4',serif;font-weight:700;font-size:20px;color:var(--olive);margin-bottom:8px;}
.btn-reserve-solid{background:var(--olive);color:var(--paper-sunk);border:none;border-radius:8px;padding:10px 0;font-size:12px;font-weight:700;cursor:pointer;}
.btn-reserve-solid:hover{background:var(--olive-mid);}

.catalogue{max-width:1280px;margin:0 auto;padding:52px 20px 0;}
.toolbar{position:sticky;top:68px;z-index:30;background:rgba(253,252,244,.94);backdrop-filter:blur(12px);border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:14px 20px;margin:0 -20px;display:flex;gap:12px;flex-wrap:wrap;align-items:center;}
.search-field{flex:1 1 240px;display:flex;align-items:center;gap:8px;background:var(--paper-sunk);border:1px solid var(--line);border-radius:10px;padding:10px 14px;}
.search-slash{font-family:'IBM Plex Mono',monospace;color:var(--meta-muted);}
.search-field input{border:none;background:none;outline:none;font-size:14px;flex:1;color:var(--ink);}
.sort-select{background:var(--paper-sunk);border:1px solid var(--line);border-radius:10px;padding:10px 14px;font-size:13px;font-weight:600;}
.chips{flex:1 1 100%;display:flex;gap:10px;overflow-x:auto;padding-top:2px;}
.chip{flex:none;border-radius:999px;padding:9px 15px;font-size:13px;font-weight:700;background:var(--paper);border:1px solid var(--line);color:var(--body-muted);cursor:pointer;}
.chip.active{background:var(--olive);border-color:var(--olive);color:var(--paper-sunk);}

.product-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;padding:28px 0 64px;}
.card{background:var(--paper);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column;animation:fadeUp .35s ease;}
.card:hover{border-color:var(--olive);}
@keyframes fadeUp{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:translateY(0);}}
.card-img{position:relative;aspect-ratio:1;background:#fff;display:flex;align-items:center;justify-content:center;}
.card-img img{width:100%;height:100%;object-fit:contain;padding:10px;}
.condition-chip{position:absolute;top:8px;left:8px;background:rgba(27,30,16,.88);color:#F3F2E4;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;padding:5px 8px;border-radius:6px;}
.save-btn{position:absolute;top:8px;right:8px;border-radius:999px;font-size:10px;font-weight:700;text-transform:uppercase;padding:6px 10px;border:1px solid var(--line);background:rgba(253,252,244,.92);color:var(--body-muted);cursor:pointer;}
.save-btn.saved{background:var(--olive);border-color:var(--olive);color:#F3F2E4;}
.card-body{padding:13px 15px;display:flex;flex-direction:column;gap:3px;flex:1;}
.card-cat{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:var(--meta-muted);}
.card-title{font-size:13px;font-weight:600;line-height:1.35;}
.card-price{font-family:'Source Serif 4',serif;font-weight:700;font-size:22px;color:var(--olive);margin-top:2px;}
.card-meta{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--meta-muted);}
.card-status{font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:700;color:var(--meta-muted);text-transform:uppercase;}
.btn-outline{margin-top:auto;border:1px solid var(--olive);background:var(--paper-sunk);color:var(--olive);border-radius:8px;padding:10px 0;font-size:12px;font-weight:700;cursor:pointer;}
.btn-outline:hover{background:var(--olive);color:var(--paper-sunk);}
.btn-outline[disabled]{opacity:.5;cursor:not-allowed;}

.empty-state{border:1px dashed var(--line);border-radius:16px;padding:70px 20px;text-align:center;margin-bottom:64px;}
.empty-title{font-size:16px;font-weight:700;margin-bottom:6px;}
.empty-body{font-size:14px;color:var(--meta-muted);margin-bottom:18px;}
.btn-clear{background:var(--olive);color:var(--paper-sunk);border:none;border-radius:8px;padding:10px 20px;font-size:13px;font-weight:700;cursor:pointer;}

.how-it-works{background:var(--ink);padding:52px 20px;max-width:1280px;margin:0 auto;border-radius:0;}
.how-it-works h2{color:var(--paper);font-size:clamp(26px,3.2vw,38px);margin-bottom:26px;}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px;}
.step{border:1px solid rgba(243,242,236,.16);border-radius:16px;padding:26px;}
.step-num{font-family:'Source Serif 4',serif;font-weight:700;font-size:34px;color:var(--leaf-light);margin-bottom:10px;}
.step-title{color:var(--paper);font-weight:700;font-size:15px;margin-bottom:6px;}
.step-body{color:rgba(243,242,228,.7);font-size:13px;line-height:1.5;}

.pickup{max-width:1280px;margin:0 auto;padding:52px 20px;}
.pickup-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:36px;}
.term-row{display:flex;justify-content:space-between;gap:10px;background:var(--paper-sunk);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-bottom:10px;}
.term-label{font-weight:700;font-size:13px;}
.term-value{font-family:'IBM Plex Mono',monospace;font-size:13px;color:var(--meta-muted);}
.btn-outline-dark{display:inline-block;margin-top:6px;border:1px solid var(--olive);color:var(--olive);border-radius:8px;padding:12px 20px;font-size:13px;font-weight:700;}
.btn-outline-dark:hover{background:var(--olive);color:var(--paper-sunk);}
.stock-alerts{background:var(--paper-sunk);border-radius:18px;padding:30px;}
.stock-alerts h3{font-family:'Source Serif 4',serif;font-size:20px;margin-bottom:8px;}
.alerts-body{font-size:13px;color:var(--meta-muted);margin-bottom:18px;}
#alertForm{display:flex;flex-direction:column;gap:10px;}
#alertForm input,#alertForm select{background:var(--paper);border:1px solid var(--line);border-radius:9px;padding:12px 14px;font-size:14px;}
#alertForm button{background:var(--leaf);color:var(--ink);border:none;border-radius:9px;padding:13px;font-weight:700;font-size:14px;cursor:pointer;}
#alertForm button:hover{background:var(--leaf-hover);}

.site-footer{background:var(--olive);color:var(--paper);padding:52px 20px 20px;}
.footer-grid{max-width:1280px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:36px;padding-bottom:26px;}
.footer-mark{width:38px;height:38px;object-fit:contain;margin-bottom:10px;}
.footer-word{font-family:Cinzel,serif;font-weight:700;font-size:17px;letter-spacing:.06em;display:block;margin-bottom:8px;}
.footer-tag{font-size:13px;color:rgba(243,242,228,.7);max-width:32ch;}
.footer-heading{font-weight:700;font-size:13px;margin-bottom:10px;}
.footer-col a{display:block;font-size:14px;color:rgba(243,242,228,.82);margin-bottom:8px;}
.legal-bar{max-width:1280px;margin:0 auto;border-top:1px solid rgba(243,242,228,.16);padding-top:18px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;font-family:'IBM Plex Mono',monospace;font-size:12px;color:rgba(243,242,228,.6);}

.sheet-overlay{position:fixed;inset:0;background:rgba(27,30,16,.55);backdrop-filter:blur(4px);z-index:50;display:none;align-items:flex-end;justify-content:center;}
.sheet-overlay.open{display:flex;}
.sheet{background:var(--paper);width:100%;max-width:520px;max-height:92vh;overflow-y:auto;border-radius:18px 18px 0 0;animation:fadeUp .25s ease;}
.sheet-header{display:flex;gap:14px;padding:20px;border-bottom:1px solid var(--line);align-items:flex-start;}
.sheet-thumb{width:76px;height:76px;object-fit:contain;background:#fff;border:1px solid var(--line);border-radius:10px;}
.sheet-info{flex:1;}
.sheet-meta{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--meta-muted);text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px;}
.sheet-title{font-size:14px;font-weight:600;margin-bottom:4px;}
.sheet-price{font-family:'Source Serif 4',serif;font-weight:700;font-size:20px;color:var(--olive);}
.sheet-close{background:none;border:none;font-size:24px;line-height:1;cursor:pointer;color:var(--body-muted);}
.sheet-body{padding:20px;}
#reserveForm{display:flex;flex-direction:column;gap:10px;}
#reserveForm input,#reserveForm select,#reserveForm textarea{background:var(--paper-sunk);border:1px solid var(--line);border-radius:9px;padding:12px 14px;font-size:14px;}
.btn-hold{background:var(--olive);color:var(--paper-sunk);border:none;border-radius:9px;padding:14px;font-weight:700;font-size:14px;cursor:pointer;margin-top:4px;}
.btn-hold:hover{background:var(--olive-mid);}
.sheet-fineprint{font-size:12px;color:var(--meta-muted);text-align:center;margin-top:4px;}
.sheet-done{padding:36px 24px;text-align:center;}
.done-title{font-size:18px;font-weight:700;margin-bottom:8px;}
.done-body{font-size:14px;color:var(--meta-muted);margin-bottom:20px;}

@media (max-width:640px){
  .hero-inner{gap:36px;}
  .footer-grid{gap:26px;}
}
"""

JS = r"""
(function(){
  const PRODUCTS = window.__PRODUCTS__;
  const CHIPS = window.__CHIPS__;
  const grid = document.getElementById('productGrid');
  const emptyState = document.getElementById('emptyState');
  const resultMeta = document.getElementById('resultMeta');
  const chipRow = document.getElementById('chipRow');
  const searchInput = document.getElementById('searchInput');
  const sortSelect = document.getElementById('sortSelect');
  const watchlistCount = document.getElementById('watchlistCount');

  const state = {
    q: '',
    cat: 'All items',
    sort: 'featured',
    saved: new Set(loadSaved()),
  };

  function loadSaved(){
    try { return JSON.parse(localStorage.getItem('thrazha_watchlist') || '[]'); }
    catch(e){ return []; }
  }
  function persistSaved(){
    try { localStorage.setItem('thrazha_watchlist', JSON.stringify([...state.saved])); }
    catch(e){}
  }

  function esc(s){
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  function renderChips(){
    chipRow.innerHTML = CHIPS.map(c =>
      `<button type="button" class="chip${c === state.cat ? ' active' : ''}" data-chip="${esc(c)}">${esc(c)}</button>`
    ).join('');
  }

  function matches(p){
    const q = state.q.trim().toLowerCase();
    const hay = (p.title + ' ' + p.chip + ' ' + p.condition).toLowerCase();
    const okQ = !q || hay.includes(q);
    const okCat = state.cat === 'All items' || p.chip === state.cat;
    return okQ && okCat;
  }

  function sortList(list){
    const arr = list.slice();
    if (state.sort === 'low') arr.sort((a,b) => a.price - b.price);
    else if (state.sort === 'high') arr.sort((a,b) => b.price - a.price);
    else if (state.sort === 'az') arr.sort((a,b) => a.title.localeCompare(b.title));
    return arr;
  }

  function cardHtml(p){
    const saved = state.saved.has(p.id);
    const img = p.img ? `<img src="${esc(p.img)}" alt="${esc(p.title)}" loading="lazy">` : '';
    const soldOrComing = p.status !== 'available';
    const ctaLabel = p.status === 'sold' ? 'Sold' : (p.status === 'coming_soon' ? 'Coming soon' : 'Reserve');
    return `<div class="card" data-id="${esc(p.id)}">
      <div class="card-img">${img}
        <span class="condition-chip">${esc(p.condition)}</span>
        <button type="button" class="save-btn${saved ? ' saved' : ''}" data-save="${esc(p.id)}">${saved ? 'Saved' : 'Save'}</button>
      </div>
      <div class="card-body">
        <p class="card-cat">${esc(p.chip)}</p>
        <p class="card-title">${esc(p.title)}</p>
        <p class="card-price">${esc(p.priceLabel)}</p>
        <p class="card-meta">${esc(p.unitLabel)}</p>
        <button type="button" class="btn-outline" data-reserve="${esc(p.id)}" ${soldOrComing ? 'disabled' : ''}>${ctaLabel}</button>
      </div>
    </div>`;
  }

  function render(){
    const filtered = sortList(PRODUCTS.filter(matches));
    resultMeta.textContent = `${filtered.length} items shown / ${PRODUCTS.length} total`;
    if (!filtered.length){
      grid.innerHTML = '';
      emptyState.hidden = false;
    } else {
      emptyState.hidden = true;
      grid.innerHTML = filtered.map(cardHtml).join('');
    }
    watchlistCount.textContent = state.saved.size;
  }

  chipRow.addEventListener('click', e => {
    const btn = e.target.closest('[data-chip]');
    if (!btn) return;
    state.cat = btn.dataset.chip;
    renderChips();
    render();
  });

  searchInput.addEventListener('input', e => { state.q = e.target.value; render(); });
  sortSelect.addEventListener('change', e => { state.sort = e.target.value; render(); });

  document.getElementById('clearFilters').addEventListener('click', () => {
    state.q = ''; state.cat = 'All items'; state.sort = 'featured';
    searchInput.value = ''; sortSelect.value = 'featured';
    renderChips(); render();
  });

  document.addEventListener('click', e => {
    const saveBtn = e.target.closest('[data-save]');
    if (saveBtn){
      e.stopPropagation();
      const id = saveBtn.dataset.save;
      if (state.saved.has(id)) state.saved.delete(id); else state.saved.add(id);
      persistSaved();
      render();
      return;
    }
    const reserveBtn = e.target.closest('[data-reserve]');
    if (reserveBtn && !reserveBtn.disabled){
      openSheet(reserveBtn.dataset.reserve);
    }
  });

  document.getElementById('watchlistBtn').addEventListener('click', () => {
    state.cat = 'All items'; state.q = '';
    searchInput.value = '';
    renderChips();
    const filtered = PRODUCTS.filter(p => state.saved.has(p.id));
    resultMeta.textContent = `${filtered.length} items shown / ${PRODUCTS.length} total`;
    grid.innerHTML = filtered.length ? filtered.map(cardHtml).join('') : '';
    emptyState.hidden = !!filtered.length;
    document.getElementById('catalogue').scrollIntoView({behavior:'smooth'});
  });

  // --- Reserve sheet ---
  const overlay = document.getElementById('sheetOverlay');
  const sheetForm = document.getElementById('sheetForm');
  const sheetDone = document.getElementById('sheetDone');
  let activeProduct = null;

  function openSheet(id){
    activeProduct = PRODUCTS.find(p => p.id === id);
    if (!activeProduct) return;
    document.getElementById('sheetImg').src = activeProduct.img || '';
    document.getElementById('sheetImg').alt = activeProduct.title;
    document.getElementById('sheetMeta').textContent = `${activeProduct.condition} · ${activeProduct.chip}`;
    document.getElementById('sheetTitle').textContent = activeProduct.title;
    document.getElementById('sheetPrice').textContent = activeProduct.priceLabel;
    sheetForm.hidden = false;
    sheetDone.hidden = true;
    document.getElementById('reserveForm').reset();
    overlay.classList.add('open');
  }
  function closeSheet(){
    overlay.classList.remove('open');
    activeProduct = null;
  }
  document.getElementById('sheetClose').addEventListener('click', closeSheet);
  document.getElementById('sheetDoneClose').addEventListener('click', closeSheet);
  overlay.addEventListener('click', e => { if (e.target === overlay) closeSheet(); });
  document.getElementById('sheet').addEventListener('click', e => e.stopPropagation());

  document.getElementById('reserveForm').addEventListener('submit', e => {
    e.preventDefault();
    if (!activeProduct) return;
    const name = document.getElementById('rName').value.trim();
    const contact = document.getElementById('rContact').value.trim();
    const fulfilment = document.getElementById('rFulfilment').value;
    const note = document.getElementById('rNote').value.trim();
    if (!name || !contact) return;
    const subject = `Reserve request: ${activeProduct.title}`;
    const body = [
      `Item: ${activeProduct.title} (${activeProduct.priceLabel})`,
      `Condition: ${activeProduct.condition}`,
      `Name: ${name}`,
      `Contact: ${contact}`,
      `Fulfilment: ${fulfilment}`,
      note ? `Note: ${note}` : ''
    ].filter(Boolean).join('\n');
    const mailto = `mailto:hello@thrazha.ca?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.location.href = mailto;
    sheetForm.hidden = true;
    sheetDone.hidden = false;
  });

  // --- Stock alerts (static site: confirms locally, opens a prefilled email) ---
  document.getElementById('alertForm').addEventListener('submit', e => {
    e.preventDefault();
    const email = document.getElementById('alertEmail').value.trim();
    const category = document.getElementById('alertCategory').value;
    if (!email) return;
    const btn = document.getElementById('alertSubmit');
    btn.textContent = "You're on the list";
    btn.disabled = true;
    const subject = 'Stock alert sign-up';
    const body = `Email: ${email}\nHunting for: ${category || 'anything'}`;
    window.location.href = `mailto:hello@thrazha.ca?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  });

  renderChips();
  render();
})();
"""


if __name__ == "__main__":
    main()
