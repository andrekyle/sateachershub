import sqlite3, json
c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()
cur.execute("SELECT sections FROM generated_papers WHERE title='CAT P2 Nov 2023'")
sections = json.loads(cur.fetchone()[0])
sa = sections[0]

# Ensure qtitles / qinstructions arrays have one slot per group (3 groups)
ng = len(sa['splits'])  # 3
qt = list(sa.get('qtitles') or [])
qi = list(sa.get('qinstructions') or [])
while len(qt) < ng: qt.append('')
while len(qi) < ng: qi.append('')
qt = qt[:ng]; qi = qi[:ng]

# --- DBE Nov 2023 CAT P2 Section A headers + instructions ---
qt[0] = 'MULTIPLE-CHOICE QUESTIONS'
qi[0] = ("Various options are given as possible answers to the following questions. "
         "Choose the answer and write only the letter (A\u2013D) next to the question "
         "numbers (1.1 to 1.10) in the ANSWER BOOK, e.g. 1.11 D.")

qt[1] = 'MATCHING ITEMS'
qi[1] = ("Choose a term/concept from COLUMN B that matches a description in COLUMN A. "
         "Write only the letter (A\u2013T) next to the question numbers (2.1 to 2.10) "
         "in the ANSWER BOOK, e.g. 2.11 U.")

qt[2] = 'TRUE/FALSE ITEMS'
# Keep existing Q3 instruction if already present, else set the DBE wording.
if not (qi[2] or '').strip():
    qi[2] = ("Indicate whether the following statements are TRUE or FALSE. Write 'true' or "
             "'false' next to the question numbers (3.1 to 3.5) in the ANSWER BOOK. If the "
             "statement is true, write 'TRUE'. If the statement is false, write 'FALSE' and "
             "change the underlined word(s) to make the statement TRUE. (Do NOT simply use "
             "the word 'NOT' to change the statement.)")

sa['qtitles'] = qt
sa['qinstructions'] = qi

new_json = json.dumps(sections, ensure_ascii=False)
cur.execute("UPDATE generated_papers SET sections=? WHERE title='CAT P2 Nov 2023'", (new_json,))
c.commit()

print('Updated Section A:')
print('  qtitles       =', qt)
for k, v in enumerate(qi):
    print(f'  qinstr[{k}] =', v[:90] + ('...' if len(v) > 90 else ''))
