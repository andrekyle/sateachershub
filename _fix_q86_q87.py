"""
8.6: stem only + q8_6.png screenshot + prompt-below-image with (2) in post_text
8.7: stem only + q8_7.png HTML-code-box image (then 8.7.1/.2/.3 children unchanged)
"""
import sqlite3, json, shutil, os

PAPER_ID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
IMG_DIR = r'static\uploads\cat_p2_n25'

# Promote temp screenshot to canonical q8_6.png
shutil.copyfile(os.path.join(IMG_DIR, '_page12_img_0.png'),
                os.path.join(IMG_DIR, 'q8_6.png'))
print("Saved q8_6.png")

c = sqlite3.connect('instance/brandcartel.db')
r = c.execute("select sections from generated_papers where id=?", (PAPER_ID,)).fetchone()
secs = json.loads(r[0])
secB = secs[1]
qids = secB['question_ids']

qid_86 = qids[45]
qid_87 = qids[46]

# 8.6: stem = lead-in only, attach screenshot (40% width), prompt in post_text
c.execute(
    "update question_bank_items set question_text=?, image_path=?, image_width=? where id=?",
    ("Study the screenshot of a conditional formatting rule in a spreadsheet.",
     'uploads/cat_p2_n25/q8_6.png', 40, qid_86),
)
# 8.7: stem = lead-in only, attach HTML-code-box image (75% width)
c.execute(
    "update question_bank_items set question_text=?, image_path=?, image_width=? where id=?",
    ("Study the HTML code below, which is used to place the image Well done.jpg on a web page.",
     'uploads/cat_p2_n25/q8_7.png', 75, qid_87),
)

# Post-text map: 8.6 gets the explain prompt with (2)
qpost = secB.get('qpost_texts') or {}
if not isinstance(qpost, dict):
    qpost = {}
qpost[qid_86] = "Briefly explain the result of the rule that was applied to cells A1:A5. (2)"
secB['qpost_texts'] = qpost

c.execute("update generated_papers set sections=? where id=?", (json.dumps(secs), PAPER_ID))
c.commit()

# Cleanup temp
for f in [os.path.join(IMG_DIR, '_page12_img_0.png')]:
    if os.path.exists(f):
        os.remove(f); print(f"Removed {f}")

# Verify
print("\n=== Final 8.6 - 8.7.3 ===")
for i in range(45, 50):
    row = c.execute("select marks, question_text, image_path from question_bank_items where id=?", (qids[i],)).fetchone()
    img = ' [IMG]' if row[2] else ''
    print(f"[{i}] m={row[0]}{img} | {row[1][:90]!r}")
print(f"\npost_text(8.6): {qpost.get(qid_86)!r}")
