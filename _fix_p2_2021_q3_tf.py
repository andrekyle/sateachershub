import json
from app import app, db, GeneratedPaper, QuestionBankItem

# Q3 item texts with __word__ underline markers (verbatim from the DBE QP image)
Q3_TEXT = {
    '3c619a94': "The __wild card__ character can be used in the Find and Replace feature of a word processor.",
    'e98e39f3': "Instant messaging platforms often use __encryption__ to protect user data.",
    '184210bd': "An e-mail program may reject an attachment based on the __date__ of the file.",
    '5b6ffe6d': "The __HDMI__ port on a computer carries both audio and video signals.",
    'e6e768a1': "__Ad-blocking__ programs identify and remove malware.",
}

Q3_INTRO = (
    "Indicate whether the following statements are TRUE or FALSE. Choose the answer and "
    "write 'true' or 'false' next to the question numbers (3.1 to 3.5) in the ANSWER BOOK. "
    "Correct the statement if it is FALSE. Change the underlined word(s) to make the statement "
    "TRUE. (Do NOT simply use the word 'NOT' to change the statement.)"
)

TF_NO_MARK = "NO mark will be awarded if only FALSE is written."

TF_EXAMPLES = [
    {"q": "The initial start-up instructions are stored in the __ROM__.", "a": "True"},
    {"q": "__Wi-Fi__ can only connect devices to each other up to 10 metres.", "a": "False \u2013 Bluetooth"},
]

# Memo note for the marking guideline (3.3 & 3.5 need False + correct term)
Q3_MEMO_NOTE = (
    "(Note to marker: In Question 3.3 and 3.5, candidates need to provide both the word "
    "'False' and the correct term, in order to get the mark.)"
)


def run(paper_id, touch_items):
    p = GeneratedPaper.query.get(paper_id)
    if not p:
        return f'{paper_id}: MISSING'
    secs = json.loads(p.sections)
    s0 = secs[0]

    # Item text edits (shared rows) -- only do once
    if touch_items:
        for pref, text in Q3_TEXT.items():
            q = QuestionBankItem.query.filter(
                QuestionBankItem.id.like(pref + '%')).first()
            q.question_text = text
            q.question_type = 'true_false'
            q.marks = 1
            # answers already correct; leave answer_text as-is

    # Section A TF overrides (per-paper sections JSON)
    qi = s0.get('qinstructions') or ['', '', '']
    while len(qi) < 3:
        qi.append('')
    qi[2] = Q3_INTRO
    s0['qinstructions'] = qi
    s0['tf_examples'] = TF_EXAMPLES
    s0['tf_no_mark'] = TF_NO_MARK
    notes = s0.get('qmemo_notes') or ['', '', '']
    while len(notes) < 3:
        notes.append('')
    notes[2] = Q3_MEMO_NOTE
    s0['qmemo_notes'] = notes

    p.sections = json.dumps(secs, ensure_ascii=False)
    db.session.commit()
    return f'{paper_id}: OK ({p.title})'


with app.app_context():
    print(run('daa560a4-2a50-4a22-8425-cadafeeb4ee0', touch_items=True))
    print(run('e1e44a8f-59de-4c81-bb7e-8af0adfd4416', touch_items=False))
