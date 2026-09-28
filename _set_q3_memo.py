import sqlite3, json
DB = 'instance/brandcartel.db'
PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'

c = sqlite3.connect(DB)
row = c.execute("select sections from generated_papers where id=?", (PID,)).fetchone()
secs = json.loads(row[0])
secA = secs[0]

# Group titles (3 groups: MCQ, Matching, TF)
qtitles = secA.get('qtitles') or ['', '', '']
while len(qtitles) < 3:
    qtitles.append('')
qtitles[2] = 'TRUE/FALSE ITEMS'
secA['qtitles'] = qtitles

# Per-question paper instructions (Q3 stem on the paper itself)
qinstructions = secA.get('qinstructions') or ['', '', '']
while len(qinstructions) < 3:
    qinstructions.append('')
qinstructions[2] = (
    "Indicate whether the following statements are TRUE or FALSE. Choose the answer "
    "and write 'true' or 'false' next to the question number (3.1 to 3.5) in the "
    "ANSWER BOOK. Correct the statement if it is FALSE. Change the underlined "
    "word(s) to make the statement TRUE. (You may NOT simply use the word 'NOT' to "
    "change the statement.) NO mark will be awarded if only FALSE is written down."
)
secA['qinstructions'] = qinstructions

# Memo (Note to marker:) — only for the TF group (index 2). Allow inline HTML
# (the template renders this with |safe) so the second bullet is underlined
# exactly like the source DBE marking guideline.
qmemo_notes = secA.get('qmemo_notes') or ['', '', '']
while len(qmemo_notes) < 3:
    qmemo_notes.append('')
qmemo_notes[2] = (
    "(Note to marker:\n"
    "\u2022 In Question 3.2, 3.3 and 3.5, candidates need to provide the correct term, e.g. 4IR, in order to get the mark\n"
    "\u2022 <u>Award the mark if the correct answer is given without the word FALSE</u>\n"
    "\u2022 Do NOT award the mark if only the word FALSE is given without the correct answer)"
)
secA['qmemo_notes'] = qmemo_notes

c.execute("update generated_papers set sections=? where id=?", (json.dumps(secs), PID))
c.commit()
c.close()
print('OK. qtitles=', qtitles)
print('qmemo_notes[2]:', qmemo_notes[2])
