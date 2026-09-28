"""Round 3: scrub leaked footer/marks junk from item 49 and fix newline wraps in 45-47."""
import sqlite3, json, os, glob
PAPER_ID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
c = sqlite3.connect('instance/brandcartel.db')
r = c.execute("select sections from generated_papers where id=?", (PAPER_ID,)).fetchone()
secs = json.loads(r[0])
qids = secs[1]['question_ids']

UPDATES = {
    45: "Study the screenshot of a conditional formatting rule in a spreadsheet.\n\nBriefly explain the result of the rule.",
    46: 'Study the HTML code below, which is used to place the image Well done.jpg on a web page.',
    47: "Give TWO reasons for setting the width and height attributes in the image tag.",
    49: 'What does "#Stars" in the <a href="#Stars"> tag refer to?',
}
for i, txt in UPDATES.items():
    c.execute("update question_bank_items set question_text=? where id=?", (txt, qids[i]))
    print(f"[{i}] -> {txt[:80]!r}")
c.commit()

# Cleanup temp files
for f in glob.glob(r'static\uploads\cat_p2_n25\_page11_*.png'):
    os.remove(f); print(f"removed {f}")

# Verify
print("\n=== Final Q8 ===")
total = 0
for i in range(34, 50):
    row = c.execute("select marks, question_text, image_path from question_bank_items where id=?", (qids[i],)).fetchone()
    total += row[0] or 0
    img = ' [IMG]' if row[2] else ''
    print(f"[{i}] m={row[0]}{img} | {row[1][:90]!r}")
print(f"Q8 total = {total}")
