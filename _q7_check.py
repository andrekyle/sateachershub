import sqlite3, json
PAPER = '48c8c8d1-b356-490a-90a6-56868b67d10d'
c = sqlite3.connect('instance/brandcartel.db')
s = c.execute("SELECT sections FROM generated_papers WHERE id=?", (PAPER,)).fetchone()[0]
sec = json.loads(s)
# Q7 should be section 0 (single section). Find Q7 question_ids and items.
print('section keys:', list(sec[0].keys()))
qids = sec[0]['question_ids']
print('# qids:', len(qids))
# Get questions
rows = {}
for qid in qids:
    r = c.execute("SELECT id,topic,subtopic,question_text,marks,image_path FROM question_bank_items WHERE id=?", (qid,)).fetchone()
    if r:
        rows[qid] = r

# Print last part for Q7
print('\n=== Q7 questions ===')
for qid in qids:
    r = rows.get(qid)
    if not r: continue
    qt = (r[3] or '')
    if '7Letter' in qt or '7Stats' in qt or 'TechnoGeek' in qt and '7' in r[2] or '7.' in r[2] or (r[1] and 'GENERAL' in r[1].upper()):
        print('QID:', qid, 'subtopic:', r[2], 'marks:', r[4], 'img:', r[5])
        print('TEXT:', qt[:500])
        print('---')
print('\nsubitems:', sec[0].get('subitems'))
print('\nqpost_texts:', sec[0].get('qpost_texts'))
print('\nqtitles:', sec[0].get('qtitles'))
print('\nqinstructions:', sec[0].get('qinstructions'))
