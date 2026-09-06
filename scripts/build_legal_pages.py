#!/usr/bin/env python3
"""
Generates the two static legal/info pages referenced from the footer:
returns.html and conditions.html. Run after build_site.py (or via the
same GitHub Action — see .github/workflows/build.yml).

These share the CSS tokens from build_site.py so they stay visually
consistent with the main page without duplicating the token list.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from build_site import CSS  # noqa: E402

PAGE_CSS = CSS + """
.legal-page{max-width:760px;margin:0 auto;padding:64px 20px 80px;}
.legal-page h1{font-size:clamp(30px,4vw,42px);margin-bottom:8px;}
.legal-back{font-size:13px;font-weight:600;color:var(--olive-mid);margin-bottom:28px;display:inline-block;}
.legal-page h2{font-family:Manrope,sans-serif;font-size:16px;font-weight:700;margin:32px 0 8px;}
.legal-page p{margin-bottom:14px;color:var(--body-muted);}
.legal-page .lede{color:var(--ink);font-size:17px;}
.grade-row{border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-bottom:10px;}
.grade-name{font-weight:700;font-size:14px;margin-bottom:4px;color:var(--ink);}
.grade-desc{font-size:13px;color:var(--meta-muted);margin:0;}
"""


def shell(title, body):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | Thrazha Bazaar</title>
<link rel="icon" href="thrazha-logo.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=Source+Serif+4:wght@400;600;700&family=Manrope:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{PAGE_CSS}</style>
</head>
<body>
<header class="site-header">
  <div class="header-inner">
    <a href="index.html" class="brand">
      <img src="thrazha-logo.png" alt="Thrazha" class="brand-mark">
      <span class="brand-text">
        <span class="brand-word">THRAZHA BAZAAR</span>
        <span class="brand-sub">A Thrazha International company</span>
      </span>
    </a>
    <nav class="main-nav">
      <a href="index.html#catalogue">Catalogue</a>
      <a href="index.html#how-it-works">How it works</a>
      <a href="index.html#pickup">Pickup &amp; delivery</a>
    </nav>
  </div>
</header>
<main class="legal-page">
  <a href="index.html" class="legal-back">← Back to Thrazha Bazaar</a>
  {body}
</main>
<footer class="site-footer">
  <div class="legal-bar">
    <span>© 2026 Thrazha International Inc.</span>
    <span>Prices in CAD · Condition graded per item</span>
  </div>
</footer>
</body>
</html>
"""


def main():
    returns_body = """
  <p class="eyebrow">RETURNS &amp; HOLDS</p>
  <h1>Returns &amp; holds policy</h1>
  <p class="lede">Plain terms — no small print. Every item is opened, tested and
  condition-tagged before it's listed, so what you see is what you get.</p>

  <h2>Holds</h2>
  <p>Reserving an item through the catalogue holds it for 48 hours. No payment is taken
  at reservation — we confirm condition with you first, then arrange pickup, local
  delivery, or Canada-wide shipping. If we don't hear back within 48 hours, the hold is
  released and the item goes back on the shelf.</p>

  <h2>Returns</h2>
  <p>Because these are overstock, open-box and customer-return items sold at outlet
  prices, all sales are final once picked up or delivered — we won't misrepresent an
  item's condition, and we'll tell you plainly if something is scuffed, missing a box, or
  untested. If an item arrives materially different from how it was described, email
  <a href="mailto:hello@thrazha.ca">hello@thrazha.ca</a> within 48 hours of pickup or
  delivery and we'll make it right.</p>

  <h2>Shipping</h2>
  <p>Local delivery is a flat $15 within city limits. Canada-wide shipping is quoted per
  item based on size and weight — ask before you reserve if you need a number up front.</p>
  """

    conditions_body = """
  <p class="eyebrow">CONDITION GRADES</p>
  <h1>Condition grades</h1>
  <p class="lede">Every item on Thrazha Bazaar is tagged with one of the grades below.
  We name the condition — we don't soften it.</p>

  <div class="grade-row"><p class="grade-name">New, sealed</p><p class="grade-desc">Unopened, factory-sealed packaging. No signs of use.</p></div>
  <div class="grade-row"><p class="grade-name">Open box</p><p class="grade-desc">Packaging opened for inspection or display. Item itself is unused.</p></div>
  <div class="grade-row"><p class="grade-name">Customer return</p><p class="grade-desc">Previously purchased and returned. Tested and functional unless noted; may show light signs of handling.</p></div>
  <div class="grade-row"><p class="grade-name">Renewed</p><p class="grade-desc">Inspected, cleaned and tested to confirm it works as expected.</p></div>
  <div class="grade-row"><p class="grade-name">Overstock</p><p class="grade-desc">Excess new inventory from a supplier or liquidation lot. New unless otherwise noted.</p></div>
  """

    with open(os.path.join(ROOT, "returns.html"), "w", encoding="utf-8") as f:
        f.write(shell("Returns &amp; holds policy", returns_body))
    with open(os.path.join(ROOT, "conditions.html"), "w", encoding="utf-8") as f:
        f.write(shell("Condition grades", conditions_body))

    print("Wrote returns.html and conditions.html")


if __name__ == "__main__":
    main()
