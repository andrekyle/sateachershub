"""Strip leftover boilerplate '(1) [5] TOTAL SECTION A: 25' from Q3.5 text."""
import re
from app import app, db, QuestionBankItem

Q35 = '0aaf7e8b-44fe-4b20-bda9-b301f53652f9'

with app.app_context():
    it = db.session.get(QuestionBankItem, Q35)
    print('BEFORE:', repr(it.question_text))
    txt = it.question_text or ''
    # Cut everything from the first standalone trailing mark/total marker.
    txt = re.split(r'\s*\(\d+\)\s*(?:\[|TOTAL\b)', txt, maxsplit=1)[0]
    # Collapse internal whitespace runs but keep single spaces.
    txt = re.sub(r'\s+', ' ', txt).strip()
    it.question_text = txt
    db.session.commit()
    print('AFTER :', repr(it.question_text))
