"""
Fix Q8 (visible portion 8.1 - 8.5.2) per CAT P2 Nov 2025 page 11:
- Clean whitespace runs in stem texts (items 34, 38, 41, 42).
- Attach 8.3 spreadsheet screenshot (item 38) - width ~55%
- Attach 8.5 db-fields screenshot (item 42)  - width ~50%
"""
import sqlite3, json, os, shutil

PAPER_ID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
DB = 'instance/brandcartel.db'
IMG_DIR = r'static\uploads\cat_p2_n25'

# Move temp page11 imgs to canonical names
src1 = os.path.join(IMG_DIR, '_page11_img_0.png')
src2 = os.path.join(IMG_DIR, '_page11_img_1.png')
dst_83 = os.path.join(IMG_DIR, 'q8_3.png')
dst_85 = os.path.join(IMG_DIR, 'q8_5.png')
shutil.copyfile(src1, dst_83)
shutil.copyfile(src2, dst_85)
print(f"Saved {dst_83} and {dst_85}")

c = sqlite3.connect(DB)
r = c.execute("select sections from generated_papers where id=?", (PAPER_ID,)).fetchone()
secs = json.loads(r[0])
qids = secs[1]['question_ids']

# Cleaned texts
UPDATES = {
    # idx, qid -> (text, image_path or None, image_width or None)
    34: (
        "State the actions you have to perform in a word processing document prior to creating EACH of the following:",
        None, None,
    ),
    38: (
        "A teacher captured learners' marks in a spreadsheet, as shown in the screenshot below. Levels 1 to 7 in column D are determined by the percentage that the learners obtained in column C.",
        'uploads/cat_p2_n25/q8_3.png', 55,
    ),
    41: (
        "You received a spreadsheet from a friend, but can only enter data in certain cells. You receive a pop-up message when trying to work in other cells.\n\nGive ONE reason why you are only able to work in certain cells.",
        None, None,
    ),
    42: (
        "The following fields were used in a database table to store the records of the learners participating in various sports:",
        'uploads/cat_p2_n25/q8_5.png', 50,
    ),
}

for idx, (text, img, w) in UPDATES.items():
    qid = qids[idx]
    if img is not None:
        c.execute(
            "update question_bank_items set question_text=?, image_path=?, image_width=? where id=?",
            (text, img, w, qid),
        )
        print(f"[{idx}] text cleaned + image attached ({img} {w}%)")
    else:
        c.execute("update question_bank_items set question_text=? where id=?", (text, qid))
        print(f"[{idx}] text cleaned")

c.commit()

# Verify
print("\n=== Verify Q8 (34..44) ===")
for i in range(34, 45):
    row = c.execute("select marks, image_path, image_width, question_text from question_bank_items where id=?", (qids[i],)).fetchone()
    img = row[1] or '-'
    print(f"[{i}] m={row[0]} img={img} w={row[2]} text={row[3][:80]!r}")
