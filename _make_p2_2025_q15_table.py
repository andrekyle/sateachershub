"""Generate the HTML-table figure for CAT P2 May-June 2025 Q1.5 and attach it.

The official paper shows an HTML table (Day / Times) whose last row
("25 December: Closed") spans both columns via colspan. We render that
table to a tightly-cropped PNG with headless Chromium and store it as the
question's figure, matching the repo convention
(uploads/paper_images/p2_2025/<uuid>.png).
"""
import os
import uuid

import app
from app import QuestionBankItem, db

PAPER_ID = '18cc87c0-2ee3-43fe-b74c-89aa56a3ad71'
# Q1.5 is index 4 of section A group 0 (the "Identify the attribute ..." MCQ).
QID = '7369fb99-76bc-4edb-8782-b9f3bb81d477'

OUT_DIR = os.path.join('static', 'uploads', 'paper_images', 'p2_2025')

TABLE_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  html,body{margin:0;padding:0;background:#fff;}
  #wrap{display:inline-block;padding:6px;}
  table.tbl{
    border-collapse:collapse;
    border:2.5px solid #000;
    font-family:'Times New Roman', Times, serif;
    font-size:20px;
    font-weight:bold;
  }
  table.tbl td, table.tbl th{
    border:1px solid #000;
    padding:2px 8px;
    text-align:left;
    white-space:nowrap;
  }
  table.tbl th{text-align:center;}
</style></head>
<body>
  <div id="wrap">
    <table class="tbl">
      <tr><th>Day</th><th>Times</th></tr>
      <tr><td>Mon&#8211;Thur</td><td>08:30 to 18:30</td></tr>
      <tr><td>Fri&#8211;Sun</td><td>09:00 to 16:30</td></tr>
      <tr><td colspan="2" style="text-align:center;">25&nbsp;December: Closed</td></tr>
    </table>
  </div>
</body></html>"""


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    fname = f'q1_5_{uuid.uuid4().hex[:8]}.png'
    out_path = os.path.join(OUT_DIR, fname)
    rel_path = f'uploads/paper_images/p2_2025/{fname}'

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(device_scale_factor=3)
            page.set_content(TABLE_HTML, wait_until='networkidle')
            el = page.query_selector('#wrap')
            el.screenshot(path=out_path)
        finally:
            browser.close()
    print('Wrote', out_path, os.path.getsize(out_path), 'bytes')

    with app.app.app_context():
        q = QuestionBankItem.query.get(QID)
        if not q:
            raise SystemExit('Question not found: ' + QID)
        print('Before:', repr(q.image_path), '| width=', q.image_width, '| offset=', q.image_offset)
        q.image_path = rel_path
        q.image_width = 40   # percent of the column width
        q.image_offset = 0
        db.session.commit()
        print('After :', repr(q.image_path), '| width=', q.image_width)


if __name__ == '__main__':
    main()
