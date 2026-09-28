"""Screenshot each .page of the standalone current_preview.html to PNG via Playwright."""
import pathlib
from playwright.sync_api import sync_playwright

outdir = pathlib.Path('_mj23p1_audit')
html = (outdir / 'current_preview.html').resolve().as_uri()

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1240, 'height': 1754}, device_scale_factor=2)
    page.goto(html, wait_until='networkidle')
    pages = page.query_selector_all('.page')
    print("found", len(pages), "pages")
    for i, el in enumerate(pages):
        el.scroll_into_view_if_needed()
        el.screenshot(path=str(outdir / f'cur_p{i+1:02d}.png'))
    browser.close()
print("done ->", outdir)
