import sqlite3, json
c = sqlite3.connect('instance/brandcartel.db')
row = c.execute("select sections from generated_papers where id='8fe0ceee-4092-4c16-9126-506a62da55e1'").fetchone()
secs = json.loads(row[0])
for i, s in enumerate(secs):
    print('---SEC', i, '---')
    print('title:', s.get('title'))
    print('keys:', list(s.keys()))
    for k in ('annexures', 'annexure', 'appendix', 'html_tag_sheet', 'input_mask', 'reference_sheets'):
        if k in s:
            print(' has', k, '=', str(s[k])[:80])
# also look top-level
print('TOP keys (sample):')
print(list(secs[-1].keys()) if secs else 'none')
