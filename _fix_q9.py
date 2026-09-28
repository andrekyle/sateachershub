"""
Fix Q9 (Section C) visible portion (items 0-9):
- Add Section C QUESTION 9 boxed intro scenario via secC['qinstructions'][0].
- 9.1 stem (item 0): clean whitespace + attach quotation box (q9_1.png, 95%).
- 9.1.1 .. 9.1.5: clean whitespace runs (items 1-5).
- 9.2 stem (item 6): keep clean.
- 9.2.1, 9.2.2, 9.2.3 (items 7-9): clean.
"""
import sqlite3, json, glob, os, re

PAPER_ID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
c = sqlite3.connect('instance/brandcartel.db')
r = c.execute("select sections from generated_papers where id=?", (PAPER_ID,)).fetchone()
secs = json.loads(r[0])
secC = secs[2]
qids = secC['question_ids']

INTRO = "Mr Brown is establishing a coding and robotics club at the school. The club will consist of learners from all grades and volunteer teachers."

# Set Q9 group intro (qinstructions[0])
qinstr = secC.get('qinstructions') or ['', '']
while len(qinstr) < 2:
    qinstr.append('')
qinstr[0] = INTRO
secC['qinstructions'] = qinstr

UPDATES = {
    0: ("The club needs laptops. Mr Brown submitted TWO quotations for laptops to the school governing body.",
        'uploads/cat_p2_n25/q9_1.png', 95),
    1: ("Which operating system is installed on both laptops?", None, None),
    2: ("State TWO functions of an operating system.", None, None),
    3: ("Give TWO reasons why Quotation 2 is better than Quotation 1.", None, None),
    4: ("What is the purpose of the 802.11 specification?", None, None),
    5: ("State ONE disadvantage that can be associated with using the type of antivirus indicated in the quotations.", None, None),
    6: ("The new laptops need to be set up in a network.", None, None),
    7: ("Why is a WAN NOT a suitable type of network for these computers?", None, None),
    8: ("Suggest a network communication medium that the club can use. Motivate your answer.", None, None),
    9: ("Explain TWO ways in which the club can ensure ethical use of the network.", None, None),
}

for i, (text, img, w) in UPDATES.items():
    qid = qids[i]
    if img is not None:
        c.execute(
            "update question_bank_items set question_text=?, image_path=?, image_width=? where id=?",
            (text, img, w, qid),
        )
        print(f"[{i}] cleaned + image attached ({img} {w}%)")
    else:
        c.execute("update question_bank_items set question_text=? where id=?", (text, qid))
        print(f"[{i}] cleaned: {text[:70]!r}")

c.execute("update generated_papers set sections=? where id=?", (json.dumps(secs), PAPER_ID))
c.commit()

# Cleanup temp files
for f in glob.glob(r'static\uploads\cat_p2_n25\_p13_*.png') + glob.glob(r'static\uploads\cat_p2_n25\_page13_*.png'):
    try:
        os.remove(f); print(f"removed {f}")
    except Exception:
        pass

# Verify
print("\n=== Final Q9 (items 0-9) ===")
for i in range(0, 10):
    row = c.execute("select marks, image_path, question_text from question_bank_items where id=?", (qids[i],)).fetchone()
    img = ' [IMG]' if row[1] else ''
    print(f"[{i}] m={row[0]}{img} | {row[2][:90]!r}")
print(f"\nQ9 group intro: {qinstr[0][:100]!r}")
