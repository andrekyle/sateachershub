"""
Fix Q6 (Section B, INFORMATION MANAGEMENT) per PDF page 9 of CAT P2 Nov 2025.

Issues:
1. 6.5 marks stored as 10 -> should be 2 (text: "Give TWO reasons" + "(2)")
2. 6.5 missing chart image
3. Question texts have whitespace runs (e.g., "service.                State TWO benefits")
   that print poorly — split lead-ins onto their own paragraph using \n\n.
"""
import sqlite3, json, shutil, os, re

PAPER_ID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
DB = 'instance/brandcartel.db'

# Copy extracted chart -> public path
src_chart = r"static\uploads\cat_p2_n25\_page9_img_0.png"
dst_chart = r"static\uploads\cat_p2_n25\q6_5.png"
shutil.copyfile(src_chart, dst_chart)
print(f"Saved chart -> {dst_chart}")

c = sqlite3.connect(DB)
r = c.execute("select sections from generated_papers where id=?", (PAPER_ID,)).fetchone()
secs = json.loads(r[0])
qids = secs[1]['question_ids']
splits = secs[1]['splits']  # [0,16,24,29,34]
q6_idx = list(range(splits[2], splits[3]))  # 24..28
print("Q6 indices:", q6_idx)

# Cleaned texts per PDF (lead-in then prompt, separated by blank line)
NEW_TEXTS = {
    24: "A user uses a URL shortening service.\n\nState TWO benefits of using a URL shortening service.",
    25: "Name TWO elements of a report that must be included in your final practical assessment task (PAT) report.",
    26: "State TWO criteria you should consider when evaluating the reliability of an online source.",
    27: "When working on your PAT, it is important to create a suitable folder structure.\n\nState TWO factors that you need to consider when creating your folder structure.",
    28: "Study the chart below showing a summary of responses on a questionnaire.\n\nGive TWO reasons why it is difficult to interpret the chart.",
}

CHART_PATH = "/static/uploads/cat_p2_n25/q6_5.png"

for i in q6_idx:
    qid = qids[i]
    row = c.execute("select question_text, marks, image_path, image_width from question_bank_items where id=?", (qid,)).fetchone()
    old_text, old_marks, old_img, old_w = row
    new_text = NEW_TEXTS[i]
    if i == 28:
        # Fix marks (10 -> 2) AND attach chart image (60% width)
        c.execute(
            "update question_bank_items set question_text=?, marks=?, image_path=?, image_width=? where id=?",
            (new_text, 2, CHART_PATH, 60, qid),
        )
        print(f"[{i}] 6.5: marks {old_marks}->2, image set, width 60%")
    else:
        c.execute(
            "update question_bank_items set question_text=? where id=?",
            (new_text, qid),
        )
        print(f"[{i}] text cleaned (marks {old_marks} unchanged)")

c.commit()

# Verify
print("\n=== Verify ===")
total = 0
for i in q6_idx:
    row = c.execute("select marks, image_path from question_bank_items where id=?", (qids[i],)).fetchone()
    total += row[0] or 0
    print(f"[{i}] marks={row[0]} img={row[1]}")
print(f"Q6 total = {total} (PDF says [10])")
