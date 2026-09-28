"""Q8.2 memo: render as a 2-column comparison HTML table matching the
source image (Embedded object | Linked object, two body rows, footer
'✓✓ (one per row difference)' spanning both columns, marks=2)."""
from app import app, db, QuestionBankItem

QID = 'd89ab697-2f53-4156-800b-eb775a265c43'

NEW_ANSWER = (
    '<div style="font-style:italic; font-weight:bold; margin-bottom:6px;">'
    'Difference between an embedded object and a linked object</div>\n'
    '<table class="memo-cmp" style="width:100%; border-collapse:collapse;">\n'
    '  <tr>'
    '<th style="border:1px solid #000; padding:4px 6px; text-align:left;">Embedded object</th>'
    '<th style="border:1px solid #000; padding:4px 6px; text-align:left;">Linked object</th>'
    '</tr>\n'
    '  <tr>'
    '<td style="border:1px solid #000; padding:4px 6px; vertical-align:top;">Not linked to the source document</td>'
    '<td style="border:1px solid #000; padding:4px 6px; vertical-align:top;">Linked to the source document</td>'
    '</tr>\n'
    '  <tr>'
    '<td style="border:1px solid #000; padding:4px 6px; vertical-align:top;">Opens as a separate/independent document</td>'
    '<td style="border:1px solid #000; padding:4px 6px; vertical-align:top;">Updates with data from the original source document before opening</td>'
    '</tr>\n'
    '  <tr>'
    '<td colspan="2" style="border:1px solid #000; padding:4px 6px; text-align:right; font-style:italic;">'
    '\u2713\u2713 (one per row difference)</td>'
    '</tr>\n'
    '</table>'
)

with app.app_context():
    q = db.session.get(QuestionBankItem, QID)
    print('BEFORE marks=', q.marks)
    q.answer_text = NEW_ANSWER
    q.marks = 2
    db.session.commit()
    print('AFTER  marks=', q.marks)
    print('AFTER  A: (first 200 chars)')
    print((q.answer_text or '')[:200])
