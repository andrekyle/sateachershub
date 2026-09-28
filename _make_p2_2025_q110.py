"""Generate the spreadsheet figure for CAT P2 May-June 2025 Q1.10 and lay it out.

Renders the bilingual Excel grid (columns C-G, rows 8-16) to a crisp PNG,
attaches it to the question, moves the A-D options into the section's
qpost_texts (so they render below the figure), and fixes the item mark to 1
(the [10] is the SECTION A total, rendered separately by the template).
"""
import json
import os
import uuid

import app
from app import GeneratedPaper, QuestionBankItem, db

PAPER_ID = '18cc87c0-2ee3-43fe-b74c-89aa56a3ad71'
QID = '9b2731db-a0e8-4169-8ddc-0ab42e165b5d'

OUT_DIR = os.path.join('static', 'uploads', 'paper_images', 'p2_2025')

STEM = 'Which function will calculate the total price of ALL the hardcover romance books?'
OPTIONS = (
    'A  =SUMIFS(G9:G16,"Romance", F9:F16,"Hardcover")\n'
    'B  =SUMIFS(G9:G16,C9:C16,"Romance", F9:F16,"Hardcover")\n'
    'C  =SUMIFS(G9:G16,D9:D16,"Romance", F9:F16,"Hardcover")\n'
    'D  =SUMIFS(G9:G16,C9:C16,Romance, F9:F16,Hardcover) (1)'
)

ROWS = [
    ('9', 'Romance', '206', '2', 'Hardcover', 'R354.00'),
    ('10', 'Fiction', '643', '4', 'Audiobook', 'R353.00'),
    ('11', 'Romance', '914', '5', 'Audiobook', 'R284.00'),
    ('12', 'Fiction', '484', '2', 'Hardcover', 'R384.00'),
    ('13', 'Fiction', '839', '3', 'Ebook', 'R330.00'),
    ('14', 'Non-Fiction', '173', '1', 'Hardcover', 'R394.00'),
    ('15', 'Science Fiction', '802', '4', 'Audiobook', 'R381.00'),
    ('16', 'Romance', '217', '5', 'Hardcover', 'R425.00'),
]


def build_html():
    data_rows = ''
    for rn, genre, pages, rating, fmt, price in ROWS:
        data_rows += (
            '<tr>'
            f'<td class="rh">{rn}</td>'
            f'<td class="dl">{genre}</td>'
            f'<td class="dc">{pages}</td>'
            f'<td class="dc">{rating}</td>'
            f'<td class="dl">{fmt}</td>'
            f'<td class="dr">{price}</td>'
            '</tr>\n'
        )
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  html,body{{margin:0;padding:0;background:#fff;}}
  #wrap{{display:inline-block;padding:8px;}}
  table.xl{{border-collapse:collapse;font-family:Arial,Helvetica,sans-serif;font-size:15px;}}
  table.xl td,table.xl th{{border:1px solid #b7b7b7;padding:1px 6px;white-space:nowrap;}}
  /* column-letter + row-number headers */
  .colh{{background:#e6e6e6;text-align:center;font-weight:normal;color:#333;height:18px;}}
  .corner{{background:#e6e6e6;width:18px;}}
  .corner span{{display:inline-block;border-top:9px solid #a9a9a9;border-left:9px solid transparent;}}
  .rh{{background:#e6e6e6;text-align:center;color:#333;width:22px;}}
  /* header row 8 (bilingual, bold black border around heading block) */
  .hdr td{{font-weight:bold;text-align:center;border:1px solid #000;}}
  .hdr-af td{{text-align:center;border:1px solid #000;}}
  .dl{{text-align:left;}}
  .dc{{text-align:center;}}
  .dr{{text-align:right;}}
</style></head>
<body>
  <div id="wrap">
    <table class="xl">
      <tr>
        <td class="corner"><span></span></td>
        <td class="colh">C</td><td class="colh">D</td><td class="colh">E</td>
        <td class="colh">F</td><td class="colh">G</td>
      </tr>
      <tr class="hdr">
        <td class="rh" rowspan="2">8</td>
        <td>Genre</td><td>No. of pages</td><td>Rating</td><td>Format</td><td>Price</td>
      </tr>
      <tr class="hdr-af">
        <td>Genre</td><td>Aantal bladsye</td><td>Gradering</td><td>Formaat</td><td>Prys</td>
      </tr>
      {data_rows}
    </table>
  </div>
</body></html>"""


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    fname = f'q1_10_{uuid.uuid4().hex[:8]}.png'
    out_path = os.path.join(OUT_DIR, fname)
    rel_path = f'uploads/paper_images/p2_2025/{fname}'

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(device_scale_factor=3)
            page.set_content(build_html(), wait_until='networkidle')
            page.query_selector('#wrap').screenshot(path=out_path)
        finally:
            browser.close()
    print('Wrote', out_path, os.path.getsize(out_path), 'bytes')

    with app.app.app_context():
        q = QuestionBankItem.query.get(QID)
        if not q:
            raise SystemExit('Question not found: ' + QID)
        print('OLD text:', repr(q.question_text)[:120], '| marks=', q.marks)
        q.question_text = STEM
        q.marks = 1
        q.image_path = rel_path
        q.image_width = 70
        q.image_offset = 0

        p = GeneratedPaper.query.get(PAPER_ID)
        secs = json.loads(p.sections)
        s = secs[0]
        qpost = s.get('qpost_texts') or {}
        if not isinstance(qpost, dict):
            qpost = {}
        qpost[QID] = OPTIONS
        s['qpost_texts'] = qpost
        secs[0] = s
        p.sections = json.dumps(secs, ensure_ascii=False)
        db.session.commit()
        print('NEW text:', repr(q.question_text), '| marks=', q.marks)
        print('image_path:', q.image_path, '| width:', q.image_width)


if __name__ == '__main__':
    main()
