"""Render the 8y HTML viewer to PNGs.

- Each per-trade card → trade-NNN.png
- Equity curve + KPI header → overview.png
- Yearly performance panel → yearly.png
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    root = Path(__file__).parent / "results"
    html = root / "trades_8y.html"
    pngs_dir = root / "pngs_8y"
    pngs_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900}, device_scale_factor=2)
        page.goto(f"file://{html.resolve()}")
        page.wait_for_selector(".chart canvas", timeout=30_000)
        # Wait for all charts to render
        page.wait_for_timeout(3000)

        # Header KPIs + equity curve
        page.locator("body").evaluate("el => el.scrollTo(0, 0)")
        page.wait_for_timeout(300)
        page.locator(".kpis").screenshot(path=str(pngs_dir / "kpis.png"))
        page.locator(".panel:has(#equity)").screenshot(path=str(pngs_dir / "equity_curve.png"))
        page.locator(".panel:has(#yearly)").screenshot(path=str(pngs_dir / "yearly.png"))

        cards = page.locator(".card")
        n = cards.count()
        print(f"Rendering {n} trade cards…")
        for i in range(n):
            card = cards.nth(i)
            card.scroll_into_view_if_needed()
            page.wait_for_timeout(120)
            out = pngs_dir / f"trade-{i+1:03d}.png"
            card.screenshot(path=str(out))
            if (i + 1) % 20 == 0:
                print(f"  {i+1}/{n}")

        browser.close()
    print(f"\nAll PNGs in: {pngs_dir}")


if __name__ == "__main__":
    main()
