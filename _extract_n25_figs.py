"""Extract example-figure crops from the CAT P1 Nov 2025 PDF.

For each question that has an "as shown in the example below" figure
embedded between the question text and the next sub-question, render
the page region as a PNG and save under static/uploads/cat_p1_n25/.

We then update the corresponding question_bank_items.image_path so the
paper renderer shows the figure under the question.
"""
import fitz, os, sqlite3, re

PDF = 'static/uploads/Computer Applications Technology P1 Nov 2025 Eng.pdf'
OUTDIR = 'static/uploads/cat_p1_n25'
os.makedirs(OUTDIR, exist_ok=True)

doc = fitz.open(PDF)

# Each entry: (subtopic, page-1based, top-anchor (text just BEFORE the figure),
# bottom-anchor (text just AFTER the figure), x-pad).
# top_anchor = end-of-question-text marker; bottom_anchor = start of next item.
JOBS = [
    # Q1.4 figure on page 5 between end of 1.4 text and start of "1.5"
    ('CAT P1 Nov 2025 - Q1.4', 5,
        "to display as shown in the example below.",
        "Find and replace the exact word 'Course'"),
    # Q1.7 figure on page 6 between end of 1.7 NOTES and start of "1.8"
    ('CAT P1 Nov 2025 - Q1.7', 6,
        "the same size as the other images in the",
        "Find the word 'business'"),
    # Q2.4 figure on page 7 between end of 2.4 NOTE and start of "2.5"
    ('CAT P1 Nov 2025 - Q2.4', 7,
        "Set the distance from text to 0.2 cm.",
        "Add a line between the columns"),
    # Q2.6 figure spans pages 7-8 — crop end of pg7 + top of pg8
    ('CAT P1 Nov 2025 - Q2.6', 8,
        "appears in column D",
        "Find the SmartArt"),
    # Q2.7 SmartArt figure on page 8
    ('CAT P1 Nov 2025 - Q2.7', 8,
        "modify the SmartArt to",
        "Make sure that the page numbering"),
]

ZOOM = 2.0  # 144 dpi

c = sqlite3.connect('instance/brandcartel.db')

for subtopic, pg, top_anchor, bot_anchor in JOBS:
    page = doc[pg - 1]
    pr = page.rect
    # find top y
    top_y = None
    rs = page.search_for(top_anchor)
    if rs:
        top_y = max(r.y1 for r in rs) + 4
    if top_y is None:
        print(f'  !! {subtopic}: top anchor not found on pg {pg}')
        continue
    bot_y = pr.y1 - 70  # leave room for footer
    if bot_anchor:
        rs2 = page.search_for(bot_anchor)
        if rs2:
            bot_y = min(r.y0 for r in rs2) - 4
    # x: indented body — start at ~115 to capture the wavy/border frame
    clip = fitz.Rect(115, top_y, pr.x1 - 60, bot_y)
    if clip.height < 20:
        print(f'  !! {subtopic}: clip too small {clip}')
        continue
    pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), clip=clip, alpha=False)
    fname = subtopic.replace('CAT P1 Nov 2025 - ', '').replace('.', '_').lower() + '.png'
    out = os.path.join(OUTDIR, fname)
    pix.save(out)
    rel = '/' + out.replace('\\', '/')
    print(f'{subtopic}: saved {out} ({pix.width}x{pix.height})')
    c.execute("UPDATE question_bank_items SET image_path = ? WHERE subtopic = ?",
              (rel, subtopic))

c.commit()
print('done')
