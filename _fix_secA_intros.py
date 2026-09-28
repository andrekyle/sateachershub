"""Clean Section A's wrong sec.instructions for CAT P2 N25.
   Put proper per-question instructions on qinstructions[0..2]:
     Q1 MCQ:    "Various options are provided as possible answers..."
     Q2 Match:  "Choose a term/concept from COLUMN B..."
     Q3 TF:     auto-rendered by template (leave empty).
   Also blank Section A's section-level instructions so that
   garbled Annexure-B preamble stops rendering under QUESTION 1.
"""
import sqlite3, json
PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'

Q1_MCQ = (
    'Various options are provided as possible answers to the following '
    'questions. Choose the answer and write only the letter (A–D) next to '
    'the question numbers (1.1 to 1.10) in the ANSWER BOOK, e.g. 1.11 D.'
)
Q2_MATCH = (
    'Choose a term/concept from COLUMN B that matches the description in '
    'COLUMN A. Write only the letter (A–T) next to the question numbers '
    '(2.1 to 2.10) in the ANSWER BOOK, e.g. 2.11 U. Only ONE answer per '
    'question is allowed.'
)

c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()
cur.execute("SELECT sections FROM generated_papers WHERE id=?", (PID,))
secs = json.loads(cur.fetchone()[0])
sa = secs[0]
n_groups = len(sa.get('splits') or [0])
qi = list(sa.get('qinstructions') or [])
while len(qi) < n_groups:
    qi.append('')
qi[0] = Q1_MCQ
qi[1] = Q2_MATCH
qi[2] = ''  # TF auto
sa['qinstructions'] = qi
sa['instructions'] = ''
secs[0] = sa
cur.execute("UPDATE generated_papers SET sections=? WHERE id=?", (json.dumps(secs), PID))
c.commit()
print('Section A: cleared sec.instructions; set qinstructions for Q1, Q2, Q3.')
print('Q1 instr:', qi[0][:80], '...')
print('Q2 instr:', qi[1][:80], '...')
