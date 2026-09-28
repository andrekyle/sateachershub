"""Render the current P2 2025 preview to PDF and save Section B pages as images."""
import app
from playwright.sync_api import sync_playwright

PAPER_ID = '18cc87c0-2ee3-43fe-b74c-89aa56a3ad71'

c = app.app.test_client()
with c.session_transaction() as s:
    s['user_id'] = '951c278b-2d76-4969-b0d4-6271479bf397'
    s['_user_id'] = '951c278b-2d76-4969-b0d4-6271479bf397'
    s['user_role'] = 'teacher'

# Find an available port the running app may already use; instead render HTML to PDF directly
html = c.get(f'/teacher/generator/{PAPER_ID}/preview?embed=1&print=1').get_data(as_text=True)
with open('_secB_preview.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('wrote html', len(html))

# Render via Playwright by serving the html through the live app base URL is complex;
# instead set_content (relative /static URLs need a base). Use file:// base via <base>.
import os
base = 'http://127.0.0.1:5004/'
html2 = html.replace('<head>', f'<head><base href="{base}">', 1)
with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page()
    # attach session cookie so /static auth (if any) works; static is public though
    pg.set_content(html2, wait_until='networkidle')
    pg.emulate_media(media='print')
    pg.pdf(path='_secB_preview.pdf', format='A4', print_background=True,
           margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'},
           prefer_css_page_size=True)
    b.close()
print('wrote pdf')

import pdfplumber
pdf = pdfplumber.open('_secB_preview.pdf')
print('pages', len(pdf.pages))
for i in range(len(pdf.pages)):
    txt = pdf.pages[i].extract_text() or ''
    if 'QUESTION 4' in txt or 'QUESTION 5' in txt or 'QUESTION 6' in txt or 'QUESTION 7' in txt or 'QUESTION 8' in txt:
        pdf.pages[i].to_image(resolution=110).save(f'_secB_render_p{i+1}.png')
        print('saved page', i+1, '| first line:', txt.split(chr(10))[0][:60])
