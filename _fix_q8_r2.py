"""Round 2: clean whitespace-run subitems and 8.6/8.7."""
import sqlite3, json, re
PAPER_ID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
c = sqlite3.connect('instance/brandcartel.db')
r = c.execute("select sections from generated_papers where id=?", (PAPER_ID,)).fetchone()
secs = json.loads(r[0])
qids = secs[1]['question_ids']

# Per-PDF cleaned texts
UPDATES = {
    39: "Name a function, other than a LOOKUP function, that was used to determine the correct level for each percentage.",
    40: "Which spreadsheet feature was used to complete the list of numbers in column A?",
    44: "Why should you NOT make the field size of the Surname field less than 10?",
    # 8.6 = conditional formatting screenshot question — keep as one item for now (no screenshot yet).
    # 8.7 stem = HTML code block — keep, but clean whitespace runs from stem and children.
    # Clean any stray multi-space runs in 45, 46, 47, 48, 49 too.
}

# Generic whitespace collapse for items 45-49
for i in range(45, 50):
    qid = qids[i]
    row = c.execute("select question_text, marks from question_bank_items where id=?", (qid,)).fetchone()
    txt = row[0] or ''
    # Collapse runs of 2+ spaces (but preserve newlines)
    cleaned = re.sub(r'[ \t]{2,}', ' ', txt)
    # Trim trailing marks annotation like " (1)" left at end
    cleaned = re.sub(r'\s*\(\d{1,3}\)\s*$', '', cleaned).strip()
    if cleaned != txt:
        c.execute("update question_bank_items set question_text=? where id=?", (cleaned, qid))
        print(f"[{i}] cleaned: {cleaned[:80]!r}")

for i, txt in UPDATES.items():
    c.execute("update question_bank_items set question_text=? where id=?", (txt, qids[i]))
    print(f"[{i}] updated: {txt[:80]!r}")

c.commit()

print("\n=== Final Q8 ===")
total = 0
for i in range(34, 50):
    row = c.execute("select marks, question_text, image_path from question_bank_items where id=?", (qids[i],)).fetchone()
    total += row[0] or 0
    img = ' [IMG]' if row[2] else ''
    print(f"[{i}] m={row[0]}{img} | {row[1][:90]}")
print(f"Q8 total = {total}")
