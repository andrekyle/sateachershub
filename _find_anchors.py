"""Find the y-coordinate ranges in the source PDF for each Q1.x / Q2.x
example block by searching for known text anchors. Print as a CSV-ish
table so we can decide which to crop."""
import fitz

PDF = 'static/uploads/Computer Applications Technology P1 Nov 2025 Eng.pdf'
doc = fitz.open(PDF)

ANCHORS = [
    # label, page (1-based), start anchor, end anchor
    ('Q1.4', 4, "Format the paragraphs that starts with 'TechnoGeek started in", "Find and replace the exact word 'Course'"),
    ('Q1.5', 5, "Find and replace the exact word 'Course'", "Find the citation below the subheading"),
    ('Q1.7', 5, "Edit the paragraph below the heading 'Mobile App Development'", "Find the word 'business'"),
    ('Q2.4', 6, "Change the 'T' in the first paragraph", "Add a line between the columns"),
    ('Q2.6', 6, "Modify the table below the heading 'Course prices'", "Find the SmartArt"),
    ('Q2.7', 6, "Find the SmartArt below the heading 'Slogan'", "Make sure that the page numbering"),
]

for label, pg, start, end in ANCHORS:
    p = doc[pg - 1]
    rs = p.search_for(start)
    re_ = p.search_for(end)
    if not rs:
        # try next page
        for off in (0, 1):
            p2 = doc[pg - 1 + off]
            rs = p2.search_for(start)
            if rs:
                p, pg = p2, pg + off
                break
    if not re_:
        for off in (0, 1, 2):
            p2 = doc[pg - 1 + off]
            re2 = p2.search_for(end)
            if re2:
                re_, end_pg = re2, pg + off
                break
        else:
            end_pg = pg
    else:
        end_pg = pg
    print(label, 'startpg=', pg, 'rs=', rs[:1], 'end_pg=', end_pg, 're=', (re_ or [None])[:1])
