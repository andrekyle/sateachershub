from app import app, db, QuestionBankItem
QID = '79e7f280-711a-46a3-baf7-3436e8662af1'

NEW_ANSWER = (
    '<div style="font-style:italic; font-weight:bold;">'
    'Type of application software and motivation</div>'
    '<table class="memo-cmp" style="border-collapse:collapse; margin-top:0.25em;">'
    '<thead>'
    '<tr>'
    '<th style="border:1px solid #000; padding:4px 8px; text-align:left; font-weight:bold;">Application</th>'
    '<th style="border:1px solid #000; padding:4px 8px; text-align:left; font-weight:bold;">Motivation</th>'
    '</tr>'
    '</thead>'
    '<tbody>'
    '<tr>'
    '<td style="border:1px solid #000; padding:4px 8px; vertical-align:top;">Presentation software</td>'
    '<td style="border:1px solid #000; padding:4px 8px; vertical-align:top;">'
    'Presentation software allows the team leader to create visually engaging slides with text, images and multimedia'
    '</td>'
    '</tr>'
    '<tr>'
    '<td style="border:1px solid #000; padding:4px 8px; vertical-align:top;">Any applicable software</td>'
    '<td style="border:1px solid #000; padding:4px 8px; vertical-align:top;">Suitable motivation</td>'
    '</tr>'
    '</tbody>'
    '<tfoot>'
    '<tr>'
    '<td colspan="2" style="padding:4px 8px; text-align:right; font-style:italic;">'
    '\u2713 (Type of application) \u2713 (Suitable motivation)'
    '</td>'
    '</tr>'
    '</tfoot>'
    '</table>'
)

with app.app_context():
    q = db.session.get(QuestionBankItem, QID)
    print('BEFORE:')
    print(repr(q.answer_text)[:200])
    q.answer_text = NEW_ANSWER
    q.marks = 2
    db.session.commit()
    q2 = db.session.get(QuestionBankItem, QID)
    print('\nAFTER marks =', q2.marks)
    print('AFTER answer_text length =', len(q2.answer_text))
