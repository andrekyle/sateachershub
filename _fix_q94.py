"""Apply Q9.4 layout: stem -> image -> SUMS paragraph (post_text); clean 9.4.1 / 9.4.2."""
import sqlite3, json

PAPER_ID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
c = sqlite3.connect('instance/brandcartel.db')
(raw,) = c.execute("select sections from generated_papers where id=?", (PAPER_ID,)).fetchone()
secs = json.loads(raw)
secC = secs[2]
qids = secC['question_ids']

# Indices for Section C:
# 13 -> 9.4 stem
# 14 -> 9.4.1 (1)
# 15 -> 9.4.2 (2)
STEM = "An incomplete spreadsheet is used to capture the total number of hours spent at the club."
POST = ("To calculate the total number of hours spent at the club on Mondays, "
        "the function =SUMS(B3:B6) was entered in cell B7, but it gives an error message.")
Q941 = "What does the #NAME? error message in cell B7 indicate?"
Q942 = ("The spreadsheet data is copied into a word processing document, but not all the "
        "columns are visible on the page.\n\nWithout changing the font size, state TWO ways "
        "in which the learners can adjust the table so that all the columns appear.")

# 13 — stem + image
c.execute(
    "update question_bank_items set question_text=?, image_path=?, image_width=? where id=?",
    (STEM, 'uploads/cat_p2_n25/q9_4.png', 80, qids[13]),
)
# 14 — 9.4.1
c.execute("update question_bank_items set question_text=? where id=?", (Q941, qids[14]))
# 15 — 9.4.2
c.execute("update question_bank_items set question_text=? where id=?", (Q942, qids[15]))

# Attach SUMS paragraph as post_text on the stem (renders BELOW the image)
qpost = secC.get('qpost_texts') or {}
# qpost may be dict or list — paper uses dict keyed by str(qid)
if isinstance(qpost, list):
    qpost = {}
qpost[str(qids[13])] = POST
secC['qpost_texts'] = qpost

c.execute("update generated_papers set sections=? where id=?", (json.dumps(secs), PAPER_ID))
c.commit()

# Verify
print("--- 9.4 group ---")
for i in (13, 14, 15):
    row = c.execute("select marks, image_path, question_text from question_bank_items where id=?", (qids[i],)).fetchone()
    img = ' [IMG]' if row[1] else ''
    print(f"[{i}] m={row[0]}{img} | {row[2][:100]!r}")
print("post_text[13] =", qpost[str(qids[13])][:90], "...")
