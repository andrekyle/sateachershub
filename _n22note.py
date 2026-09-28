from app import app, GeneratedPaper, QuestionBankItem
import json
PID = "49670bf2-0dbd-45c0-a6c1-547fa8091675"
with app.app_context():
    p = GeneratedPaper.query.get(PID)
    secs = json.loads(p.sections)
    secA = secs[0]
    print("qinstructions:")
    for k, v in enumerate(secA.get('qinstructions') or []):
        print(" ", k, repr(v))
    by = {q.id[:8]: q for q in QuestionBankItem.query.all()}
    for idx, pref in [(24, '39215c2c')]:
        it = by[pref]
        print("3.5 question_text:", repr(it.question_text))
        print("3.5 answer_text:", repr(it.answer_text))
