import json
import uuid
from app import app, db, GeneratedPaper, QuestionBankItem

Q41_TEXT = (
    "A SOHO computer user must choose computer hardware and software for his "
    "auditing business.\n\n"
    "Study the table below to help him make the correct buying decisions.\n\n"
    "[[Q41TABLE]]\n\n"
    "Complete the table above by writing down only the answers next to the "
    "question numbers (4.1.1 to 4.1.4) in your ANSWER BOOK. (4 x 1)"
)

STEM_44 = "A hard disk analysis shows that the drive is almost full."

NEW_441_TEXT = "Explain TWO problems that may occur when the hard disk drive is full."
NEW_441_ANS = (
    "TWO problems that occur when the hard disk drive is full\n"
    "(1) (Getting prompts that) there is no space left/Cannot save anything\n"
    "(2) Thrashing/System is slow\n"
    "(3) System sometimes freezes/crashes\n"
    "(4) Programs do not open\n"
    "(Any two)"
)


def restructure(paper_id, new_qid):
    p = GeneratedPaper.query.get(paper_id)
    if not p:
        return f'{paper_id}: MISSING'
    secs = json.loads(p.sections)
    s1 = secs[1]
    if s1.get('splits') != [0, 15, 25, 31, 39]:
        return f'{paper_id}: SecB splits differ ({s1.get("splits")}) — skipped'
    qids = s1['question_ids']
    if qids[3][:8] != 'dcac59ca':
        return f'{paper_id}: idx3 is {qids[3][:8]} not dcac59ca — skipped'
    # insert new 4.4.1 qid at index 4
    qids.insert(4, new_qid)
    s1['question_ids'] = qids
    # shift splits
    s1['splits'] = [0, 16, 26, 32, 40]
    # shift subitems (>=4 -> +1) then add new index 4
    old = s1.get('subitems') or []
    shifted = sorted(set([(i + 1 if i >= 4 else i) for i in old] + [4]))
    s1['subitems'] = shifted
    p.sections = json.dumps(secs, ensure_ascii=False)
    db.session.commit()
    return f'{paper_id}: OK splits={s1["splits"]} subitems={shifted}'


with app.app_context():
    # 1) Q4.1 table marker
    q0 = QuestionBankItem.query.filter(QuestionBankItem.id.like('50104069%')).first()
    q0.question_text = Q41_TEXT
    # 2) 4.4 stem (shared row)
    q3 = QuestionBankItem.query.filter(QuestionBankItem.id.like('dcac59ca%')).first()
    q3.question_text = STEM_44
    q3.marks = 0
    q3.question_type = 'short_answer'
    # 3) new 4.4.1 item
    new_qid = str(uuid.uuid4())
    ni = QuestionBankItem(
        id=new_qid, owner_id=q3.owner_id, grade=q3.grade, subject=q3.subject,
        topic=q3.topic, question_type='explain', question_text=NEW_441_TEXT,
        answer_text=NEW_441_ANS, marks=2,
    )
    db.session.add(ni)
    # 4) 4.11 marks 4 -> 2
    q14 = QuestionBankItem.query.filter(QuestionBankItem.id.like('86e0e47c%')).first()
    q14.marks = 2
    db.session.commit()
    print('new 4.4.1 qid:', new_qid)

    # 5) restructure both papers
    for pid in ['daa560a4-2a50-4a22-8425-cadafeeb4ee0',
                'e1e44a8f-59de-4c81-bb7e-8af0adfd4416']:
        print(restructure(pid, new_qid))
