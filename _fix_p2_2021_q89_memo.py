# -*- coding: utf-8 -*-
from app import app, db, GeneratedPaper, QuestionBankItem
import json

PID = 'daa560a4-2a50-4a22-8425-cadafeeb4ee0'
ITEM = '4a812e41'  # 8.9

TICK = (
    '<svg class="tick" viewBox="0 0 16 16" width="13" height="13" '
    'aria-hidden="true" style="vertical-align:-2px; display:inline-block;">'
    '<path d="M1.8 8.4 L4.5 8.0 L6.8 11.6 L13.0 1.6 L14.6 2.6 L7.6 14.0 L5.6 13.2 Z" '
    'fill="currentColor" stroke="currentColor" stroke-width="0.4" '
    'stroke-linejoin="round"/></svg>'
)

CELL = 'border:1px solid #000; padding:6px 26px; text-align:center;'
HANG = 'padding-left:1.7em; text-indent:-1.7em;'

html = (
    '<div style="font-weight:bold; margin-bottom:4px;">Diagram of table in HTML</div>'
    '<table style="border-collapse:collapse; margin:6px 0 8px 0; '
    "font-family:'Courier New',Courier,monospace; font-size:11pt;\">"
    '<tr><td colspan="2" style="' + CELL + '">DESCRIPTION</td></tr>'
    '<tr><td style="' + CELL + '">Item 2</td>'
    '<td style="' + CELL + '">Item 1</td></tr>'
    '</table>'
    '<div style="font-weight:bold; margin-top:4px;">Mark distribution:</div>'
    '<div style="' + HANG + '">(1) Correct diagram of a table structure: '
    '2 rows x 2 columns, 1<sup>st</sup> row merged ' + TICK + '</div>'
    '<div style="' + HANG + '">(2) Correct labels ' + TICK + '</div>'
    '<div style="' + HANG + '">(3) Correct order: Description, Item 2, Item 1 ' + TICK + '</div>'
)

with app.app_context():
    # resolve full id by 8-char prefix
    p = GeneratedPaper.query.get(PID)
    qids = json.loads(p.sections)[1]['question_ids']
    qid = next(x for x in qids if x.startswith(ITEM))
    q = db.session.get(QuestionBankItem, qid)
    print('BEFORE marks=', q.marks, 'ans=', repr((q.answer_text or '')[:100]))
    q.answer_text = html
    if q.marks != 3:
        q.marks = 3
    db.session.commit()
    q2 = db.session.get(QuestionBankItem, qid)
    print('AFTER marks=', q2.marks)
    print(q2.answer_text[:120], '...')
