import sqlite3
c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()
cur.execute("SELECT id, substr(question_text,1,80), image_path FROM question_bank_items WHERE image_path IS NOT NULL AND image_path != '' LIMIT 8")
for r in cur.fetchall():
    print(r)
print()
# also check image_path values for P2 Nov 2025 questions
cur.execute("""SELECT id, substr(question_text,1,80), image_path
FROM question_bank_items
WHERE id IN (SELECT value FROM (SELECT json_each.value FROM generated_papers, json_each(generated_papers.sections), json_each(json_each.value, '$.question_ids') WHERE generated_papers.id='8fe0ceee-4092-4c16-9126-506a62da55e1'))
AND image_path IS NOT NULL AND image_path != ''""")
print('--- P2 Nov 2025 with image ---')
for r in cur.fetchall():
    print(r)
