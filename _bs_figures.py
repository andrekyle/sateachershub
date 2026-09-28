# Crop the DBE table figures from the Business Studies May-June 2023 papers
# and attach them to the matching bank items (same pattern as the CAT
# imports: figure crops live in static/uploads/paper_images/<folder>/ and are
# referenced from QuestionBankItem.image_path).
import os
import re
import sqlite3

import pymupdf

DB = 'instance/brandcartel.db' if os.path.exists('instance/brandcartel.db') else 'brandcartel.db'
OUT = 'static/uploads/paper_images/bs_mj2023'
os.makedirs(OUT, exist_ok=True)


def crop(doc, page_no, rect, out_name):
    page = doc[page_no]
    pix = page.get_pixmap(dpi=200, clip=pymupdf.Rect(*rect))
    path = os.path.join(OUT, out_name)
    pix.save(path)
    return f'uploads/paper_images/bs_mj2023/{out_name}'


def find_y(doc, page_no, needle, which=0):
    hits = doc[page_no].search_for(needle)
    if not hits or which >= len(hits):
        return None
    return hits[which]


def main():
    db = sqlite3.connect(DB)

    def attach(subtopic, rel, width=90, offset=0, strip_matching_text=False):
        row = db.execute(
            'select id, question_text from question_bank_items where subtopic=?',
            (subtopic,)).fetchone()
        if not row:
            print('  !! no item for', subtopic)
            return
        qid, qtext = row
        if strip_matching_text:
            # Keep only the instruction paragraph; the scrambled column text
            # is replaced by the exact table image.
            first = qtext.split('\n\n')[0].strip()
            db.execute('update question_bank_items set question_text=? where id=?',
                       (first, qid))
        db.execute(
            'update question_bank_items set image_path=?, image_width=?, image_offset=? where id=?',
            (rel, width, offset, qid))
        print('  attached', rel, '->', subtopic)

    for pno in (1, 2):
        doc = pymupdf.open(f'static/uploads/Business Studies P{pno} May-June 2023 Eng.pdf')
        tag = f'BSTD P{pno} May-June 2023'
        print(f'--- P{pno}')

        # 1) Q1.3 matching table (COLUMN A / COLUMN B), page 5 (index 4).
        col = find_y(doc, 4, 'COLUMN A', which=1)
        marks = find_y(doc, 4, '(5 x 2)')
        if col and marks:
            # Bound by the drawn table borders around the matching columns.
            page5 = doc[4]
            trs = [d['rect'] for d in page5.get_drawings()
                   if d['rect'].y1 > col.y0 - 12 and d['rect'].y0 < marks.y0]
            if trs:
                rect = (min(r.x0 for r in trs) - 3, min(r.y0 for r in trs) - 3,
                        max(r.x1 for r in trs) + 3, max(r.y1 for r in trs) + 3)
            else:
                rect = (85, col.y0 - 8, 520, marks.y0 - 4)
            rel = crop(doc, 4, rect, f'p{pno}_q1_3_matching.png')
            attach(f'{tag} - Q1.3', rel, width=95, strip_matching_text=True)

        # 2) "Use the table as a GUIDE" boxes in Section B (search all pages).
        for pgno in range(len(doc)):
            page = doc[pgno]
            guide = page.search_for('as a GUIDE')
            if not guide:
                continue
            g = guide[0]
            text = page.get_text()
            # Which sub-question does this guide belong to? The line reads
            # "Use the table below as a GUIDE to answer QUESTION(S) 4.2.1..."
            m = re.search(r'GUIDE to answer QUESTIONS?\s+(\d+\.\d+)', text)
            if not m:
                continue
            sub = m.group(1)
            # Bound the crop by the drawn table borders directly below the
            # guide line (the first contiguous cluster only — later boxes on
            # the page, e.g. scenario borders, belong to other questions).
            cand = sorted((d['rect'] for d in page.get_drawings()
                           if d['rect'].y0 > g.y1 - 2 and d['rect'].width > 30),
                          key=lambda r: r.y0)
            if not cand:
                continue
            table_rects = [cand[0]]
            for r in cand[1:]:
                if r.y0 <= max(t.y1 for t in table_rects) + 45:
                    table_rects.append(r)
                else:
                    break
            x0 = min(r.x0 for r in table_rects) - 3
            x1 = max(r.x1 for r in table_rects) + 3
            y0 = min(r.y0 for r in table_rects) - 3
            y1 = max(r.y1 for r in table_rects) + 3
            rect = (x0, y0, x1, y1)
            if rect[3] - rect[1] < 24:
                continue
            rel = crop(doc, pgno, rect, f'p{pno}_q{sub.replace(".", "_")}_table.png')
            # The guide table belongs to the STEM item (e.g. Q4.2) when the
            # question has children, else the sub-question item itself.
            stem_key = f'{tag} - Q{sub}'
            attach(stem_key, rel, width=85)

    db.commit()
    print('done')


if __name__ == '__main__':
    main()
