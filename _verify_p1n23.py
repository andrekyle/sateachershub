# -*- coding: utf-8 -*-
"""Render the CAT P1 Nov 2023 preview HTML to verify content & catch errors."""
import re
from flask import render_template
from app import app, db, GeneratedPaper, _build_paper_context, _inject_force_page_count

PID = '06a40eac-5b21-4ef1-815c-698cecce89f2'
with app.app_context():
    paper = db.session.get(GeneratedPaper, PID)
    with app.test_request_context(f'/teacher/generator/{PID}/preview'):
        ctx = _build_paper_context(paper, with_memo=False, version='current')
        ctx['version'] = 'current'
        _inject_force_page_count(ctx, paper, with_memo=False, version='current')
        html = render_template('teacher/paper_print.html', **ctx)

    with open('_p1n23_render.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("rendered length:", len(html))

    checks = {
        "MARKS 150": "150" in html,
        "Confidential": "Confidential" in html,
        "WORD PROCESSING": "WORD PROCESSING" in html,
        "SPREADSHEET": "SPREADSHEET" in html,
        "DATABASE": "DATABASE" in html,
        "WEB DESIGN": "WEB DESIGN" in html,
        "SCENARIO transport": "transportation" in html,
        "1234cars password": "1234cars" in html,
        "img q1_2_heading": "q1_2_heading.png" in html,
        "img q7_1_logo": "q7_1_logo.png" in html,
        "all 9 imgs": len(re.findall(r'cat_p1_nov23/', html)) >= 9,
    }
    bad = {
        "[Auto] leak": "[Auto]" in html,
        "tag-sheet dump in body": "Defines the body of the web" in html and "HTML TAG SHEET" in html,
        "trailing (2) in 7.2.3": "row and column headings. (2)" in html,
        "TOTAL: 150 dumped mid": bool(re.search(r'7Bookings spreadsheet\.\s*\[15\]', html)),
    }
    print("\n--- GOOD checks ---")
    for k, v in checks.items():
        print(("OK " if v else "MISSING "), k)
    print("\n--- BAD checks (should all be False) ---")
    for k, v in bad.items():
        print(("FAIL " if v else "ok "), k)
    # count appendices presence
    print("\nHTML TAG SHEET present (appendix):", html.count("HTML TAG SHEET"))
    print("INPUT MASK present (appendix):", "INPUT MASK" in html)
