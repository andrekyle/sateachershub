"""Render the P2 2025 paper preview to PDF via Playwright and rasterize the
Q8 pages to verify the three figures render correctly.

Strategy: fetch the preview HTML with Flask's test_client (authenticated as
the paper owner), then load it in Playwright while intercepting /static/*
requests and fulfilling them from disk.
"""
import os
import mimetypes
from app import app

PAPER_ID = '18cc87c0-2ee3-43fe-b74c-89aa56a3ad71'
OWNER = '951c278b-2d76-4969-b0d4-6271479bf397'
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

app.config['SERVER_NAME'] = '127.0.0.1:5004'

with app.test_client() as c:
    with c.session_transaction() as s:
        s['user_id'] = s['_user_id'] = OWNER
        s['user_role'] = 'teacher'
    resp = c.get('/teacher/generator/%s/preview' % PAPER_ID)
    print('status', resp.status_code)
    html = resp.get_data(as_text=True)

with open('_q8_preview.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('wrote _q8_preview.html (%d bytes)' % len(html))

from playwright.sync_api import sync_playwright

def handle_route(route, request):
    url = request.url
    if '/static/' in url:
        rel = url.split('/static/', 1)[1].split('?', 1)[0]
        path = os.path.join(STATIC_DIR, rel.replace('/', os.sep))
        if os.path.isfile(path):
            ctype = mimetypes.guess_type(path)[0] or 'application/octet-stream'
            with open(path, 'rb') as fh:
                route.fulfill(status=200, body=fh.read(), content_type=ctype)
            return
    route.continue_()

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(device_scale_factor=2)
    page.route('**/*', handle_route)
    # Inject a base href so /static/* resolves to an http origin the route
    # interceptor can catch (set_content otherwise uses about:blank).
    if '<head>' in html:
        html_based = html.replace('<head>', '<head><base href="http://localhost/">', 1)
    else:
        html_based = '<base href="http://localhost/">' + html
    page.set_content(html_based, wait_until='networkidle')
    page.pdf(path='_q8_preview.pdf', format='A4', print_background=True)
    browser.close()
print('wrote _q8_preview.pdf')

import pdfplumber
with pdfplumber.open('_q8_preview.pdf') as pdf:
    print('pages:', len(pdf.pages))
    # Q8 is near the end of Section B; rasterize last 4 pages to find it.
    for pno in range(max(1, len(pdf.pages) - 4), len(pdf.pages) + 1):
        page = pdf.pages[pno - 1]
        im = page.to_image(resolution=130)
        out = '_q8_render_p%d.png' % pno
        im.save(out)
        print('wrote', out)
