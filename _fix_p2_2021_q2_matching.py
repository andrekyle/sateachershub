import json
from app import app, db, GeneratedPaper, QuestionBankItem

PID = 'daa560a4-2a50-4a22-8425-cadafeeb4ee0'

# COLUMN A descriptions (verbatim from the DBE P2 May/June 2021 QP), 2.1..2.10
COL_A = [
    "A feature that refers to whether a printer can be used with a particular operating system",
    "One way of solving the problem of an application that has stopped responding",
    "A specification that measures the quality of pictures taken by a camera",
    "A technology that can be used to establish a wireless connection between two devices by bringing them close together",
    "An attempt to access personal information by tricking a user into clicking on a link in an e-mail",
    "Websites that read like a personal journal and are often updated with news and events",
    "A spreadsheet function that returns both the date and time",
    "A system utility that reorganises parts of files",
    "The term given to the practice of accessing a network without permission",
    "A hardware component that can be added to a computer to improve video editing performance",
]

# COLUMN B options A..T (verbatim)
COL_B = [
    ("A", "blogs"),
    ("B", "ADSL"),
    ("C", "defragmenter"),
    ("D", "NOW"),
    ("E", "hacking"),
    ("F", "graphics card"),
    ("G", "Wi-Fi functionality"),
    ("H", "MP"),
    ("I", "click-jacking"),
    ("J", "network card"),
    ("K", "NFC"),
    ("L", "update"),
    ("M", "phishing"),
    ("N", "DPI"),
    ("O", "restart"),
    ("P", "compatibility"),
    ("Q", "identity theft"),
    ("R", "TODAY"),
    ("S", "Disk Cleanup"),
    ("T", "wikis"),
]

# Correct answer per row 2.1..2.10 (verified vs MG). Stored as
# "LETTER term \u2713" so _annotate_matching_runs resolves each row key by term
# (bare-letter answers do not resolve) and the memo shows the right letter.
_ANS_LETTERS = ["P", "O", "H", "K", "M", "A", "D", "C", "E", "F"]
_COL_B_MAP = dict((L, t) for L, t in [
    ("A", "blogs"), ("B", "ADSL"), ("C", "defragmenter"), ("D", "NOW"),
    ("E", "hacking"), ("F", "graphics card"), ("G", "Wi-Fi functionality"),
    ("H", "MP"), ("I", "click-jacking"), ("J", "network card"), ("K", "NFC"),
    ("L", "update"), ("M", "phishing"), ("N", "DPI"), ("O", "restart"),
    ("P", "compatibility"), ("Q", "identity theft"), ("R", "TODAY"),
    ("S", "Disk Cleanup"), ("T", "wikis"),
])
ANSWERS = [f"{L} {_COL_B_MAP[L]} \u2713" for L in _ANS_LETTERS]

MATCH_INSTR = (
    "Choose a term/concept from COLUMN B that matches a description in COLUMN A. "
    "Write only the letter (A\u2013T) next to the question numbers (2.1 to 2.10) in the "
    "ANSWER BOOK, e.g. 2.11 U."
)


def run(paper_id):
    p = GeneratedPaper.query.get(paper_id)
    if not p:
        return f'{paper_id}: MISSING'
    secs = json.loads(p.sections)
    s0 = secs[0]
    qids = s0['question_ids']
    splits = s0['splits']
    q2 = qids[splits[1]:splits[2]]
    assert len(q2) == 10, f'q2 len {len(q2)}'

    opts_tail = '\n'.join(f'{L}) {t}' for L, t in COL_B)

    for i, qid in enumerate(q2):
        q = db.session.get(QuestionBankItem, qid)
        text = COL_A[i].strip()
        if i == 0:
            text = f'{text}\nOptions:\n{opts_tail}'
        q.question_text = text
        q.question_type = 'match_columns'
        q.marks = 1
        q.answer_text = ANSWERS[i]

    # Section A titles + Q2 instruction
    s0['qtitles'] = ['MULTIPLE-CHOICE QUESTIONS', 'MATCHING ITEMS', 'TRUE/FALSE ITEMS']
    qi = s0.get('qinstructions') or ['', '', '']
    while len(qi) < 3:
        qi.append('')
    qi[1] = MATCH_INSTR
    s0['qinstructions'] = qi

    p.sections = json.dumps(secs, ensure_ascii=False)
    db.session.commit()
    return f'{paper_id}: OK ({p.title})'


with app.app_context():
    # Fix the original AND the "Copy of" duplicate (shares the same item rows anyway).
    for pid in ['daa560a4-2a50-4a22-8425-cadafeeb4ee0',
                'e1e44a8f-59de-4c81-bb7e-8af0adfd4416']:
        print(run(pid))
