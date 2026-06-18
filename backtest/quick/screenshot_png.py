"""Render the HTML viewer to PNGs — one per trade card."""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    root = Path(__file__).parent / "results"
    html = root / "trades.html"
    pngs_dir = root / "pngs"
    pngs_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900}, device_scale_factor=2)
        page.goto(f"file://{html.resolve()}")
        # Wait for charts to render
        page.wait_for_selector(".chart canvas", timeout=15_000)
        page.wait_for_timeout(1200)  # ensure all 9 charts done painting

        cards = page.locator(".card")
        n = cards.count()
        print(f"Found {n} trade cards")
        for i in range(n):
            card = cards.nth(i)
            card.scroll_into_view_if_needed()
            page.wait_for_timeout(200)
            out = pngs_dir / f"trade-{i+1:02d}.png"
            card.screenshot(path=str(out))
            print(f"  → {out.name}")

        # Also full-page overview
        page.screenshot(path=str(pngs_dir / "overview.png"), full_page=True)
        browser.close()
    print(f"\nAll PNGs in: {pngs_dir}")


if __name__ == "__main__":
    main()
