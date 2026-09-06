#!/usr/bin/env python3
"""
Rebuilds index.html from data/products.csv.

Run this locally with: python3 scripts/build_site.py
(It also runs automatically via GitHub Actions whenever data/products.csv changes —
see .github/workflows/build.yml — so most of the time you never need to run it yourself.)
"""
import csv, html, re, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "data", "products.csv")
OUT_PATH = os.path.join(ROOT, "index.html")

CATEGORY_ORDER = [
    "Footwear", "Apparel & Clothing", "Electronics", "Home & Kitchen",
    "Bags & Accessories", "Baby & Kids", "Health & Fitness",
]

CATEGORY_ICONS = {
    "Footwear": "👟",
    "Apparel & Clothing": "👕",
    "Electronics": "🎧",
    "Home & Kitchen": "🍽️",
    "Bags & Accessories": "👜",
    "Baby & Kids": "🍼",
    "Health & Fitness": "🩹",
}

CATEGORY_SLUG = {c: re.sub(r"[^a-z0-9]+", "-", c.lower()).strip("-") for c in CATEGORY_ORDER}


VALID_STATUSES = {"available", "sold", "coming_soon"}


def load_products(path):
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
    return f"${p:,.2f}"


def price_label(item):
    if item["price_min"] == item["price_max"]:
        return fmt_price(item["price_min"])
    return f"{fmt_price(item['price_min'])} – {fmt_price(item['price_max'])}"


def render_card(item):
    name = html.escape(title_case(item["title"]))
    price = price_label(item)
    status = item["status"]

    qty_badge = f'<span class="qty-badge">×{item["qty"]}</span>' if item["qty"] > 1 else ""

    if item["has_photo"]:
        img_html = f'<img src="{item["photo"]}" alt="{name}" loading="lazy">'
    else:
        icon = CATEGORY_ICONS.get(item["category"], "🏷️")
        img_html = f'<div class="placeholder-img"><span>{icon}</span></div>'

    card_classes = "product-card"
    status_badge = ""
    if status == "sold":
        card_classes += " is-sold"
        status_badge = '<span class="status-badge status-sold">Sold</span>'
        price_html = f'<p class="product-price product-price-sold">{price}</p>'
    elif status == "coming_soon":
        card_classes += " is-coming-soon"
        status_badge = '<span class="status-badge status-coming">Coming Soon</span>'
        price_html = f'<p class="product-price">{price}</p>'
    else:
        price_html = f'<p class="product-price">{price}</p>'

    return f"""<div class="{card_classes}">
      <div class="product-img">{img_html}{qty_badge}{status_badge}</div>
      <div class="product-info">
        <p class="product-name">{name}</p>
        {price_html}
      </div>
    </div>"""


def main():
    products = load_products(CSV_PATH)

    by_cat = {c: [] for c in CATEGORY_ORDER}
    for item in products:
        by_cat.setdefault(item["category"], [])
        by_cat[item["category"]].append(item)

    # Within each category: active/coming-soon items first (alphabetical), sold items sink to the bottom.
    for c in by_cat:
        by_cat[c].sort(key=lambda x: (x["status"] == "sold", x["title"]))

    nav_links = "\n".join(
        f'<a href="#{CATEGORY_SLUG.get(c, re.sub(r"[^a-z0-9]+", "-", c.lower()).strip("-"))}">{CATEGORY_ICONS.get(c, "🏷️")} {html.escape(c)}</a>'
        for c in CATEGORY_ORDER if by_cat.get(c)
    )

    sections = []
    for c in CATEGORY_ORDER:
        items = by_cat.get(c, [])
        if not items:
            continue
        cards = "\n".join(render_card(it) for it in items)
        sections.append(f"""
<section class="category-section" id="{CATEGORY_SLUG[c]}">
  <h2 class="category-title">{CATEGORY_ICONS[c]} {html.escape(c)} <span class="category-count">({len(items)})</span></h2>
  <div class="product-grid">
    {cards}
  </div>
</section>""")

    total_items = len(products)
    total_lots = sum(p["qty"] for p in products)
    n_categories = len([c for c in CATEGORY_ORDER if by_cat.get(c)])

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Thrazha Finds | Quality Overstock &amp; Auction Deals</title>
<meta name="description" content="Thrazha Finds — quality overstock, returns, and auction finds at honest prices. New arrivals added regularly.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="style.css">
</head>
<body>

<header class="site-header">
  <div class="header-inner">
    <a href="#top" class="logo">Thrazha <span>Finds</span></a>
    <nav class="main-nav">
      {nav_links}
    </nav>
  </div>
</header>

<section class="hero" id="top">
  <div class="hero-inner">
    <h1>Quality Finds. Honest Prices.</h1>
    <p>Overstock, returns, and auction-sourced goods — footwear, apparel, electronics, home essentials and more. Every item priced to move.</p>
    <div class="hero-stats">
      <div><strong>{total_items}</strong><span>Unique Items</span></div>
      <div><strong>{total_lots}</strong><span>In Stock</span></div>
      <div><strong>{n_categories}</strong><span>Categories</span></div>
    </div>
  </div>
</section>

<main>
{"".join(sections)}
</main>

<section class="cta-strip">
  <h3>See something you like?</h3>
  <p>Reach out and we'll confirm availability and arrange pickup or delivery.</p>
  <a href="mailto:hello@thrazha.ca" class="btn-cta">Email Us: hello@thrazha.ca</a>
</section>

<footer>
  <div class="tagline">THRAZHA FINDS | A THRAZHA INTERNATIONAL company</div>
  <div class="copyright">&copy; 2026 Thrazha Finds. All rights reserved.</div>
</footer>

</body>
</html>
"""

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"Wrote {OUT_PATH} — {total_items} products, {total_lots} lots, {n_categories} categories")


if __name__ == "__main__":
    main()
