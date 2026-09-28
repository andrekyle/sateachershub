"""
Reorder Q6.5: lead-in → CHART image → prompt + (2).
Achieved by:
  - question_text   = lead-in only
  - q.image_path    = chart  (already set)
  - sec['qpost_texts'][qid] = prompt + "(2)"  -> renders via q.post_text below image
"""
import sqlite3, json
PAPER_ID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
DB = 'instance/brandcartel.db'

c = sqlite3.connect(DB)
r = c.execute("select sections from generated_papers where id=?", (PAPER_ID,)).fetchone()
secs = json.loads(r[0])
secB = secs[1]
qid_65 = secB['question_ids'][28]
print("Q6.5 qid:", qid_65)

# Reset question_text to the lead-in only
c.execute(
    "update question_bank_items set question_text=? where id=?",
    ("Study the chart below showing a summary of responses on a questionnaire.", qid_65),
)

# Add the prompt as post_text via section's qpost_texts map
qpost = secB.get('qpost_texts') or {}
if not isinstance(qpost, dict):
    qpost = {}
qpost[qid_65] = "Give TWO reasons why it is difficult to interpret the chart. (2)"
secB['qpost_texts'] = qpost

c.execute(
    "update generated_papers set sections=? where id=?",
    (json.dumps(secs), PAPER_ID),
)
c.commit()

# Verify
row = c.execute("select question_text, marks, image_path from question_bank_items where id=?", (qid_65,)).fetchone()
print("Body :", repr(row[0]))
print("Marks:", row[1])
print("Image:", row[2])
print("Post :", repr(qpost[qid_65]))
