"""Fix CAT P2 Nov 2025 Q2 MATCHING ITEMS.

The PDF extraction merged Column A descriptions and Column B options into a
single jumbled question_text per item. This rewrites each of the 10 Q2 items
so that:
  * question_type = 'match_columns'
  * marks = 1 (was 10 on the last item)
  * question_text = clean Column A description
  * the FIRST item also has the full Column B options appended after
    'Options:' so _annotate_matching_runs() can build the rendered table
  * answer_text simplified to just the letter (e.g. 'R')
"""
import sqlite3

PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
DB = 'instance/brandcartel.db'

# Q2 question_ids in order, with their cleaned Column A descriptions and
# correct answer letters from the official Nov 2025 P2 memo.
ROWS = [
    ('ca86dd56-4de8-44bc-acc5-68d6649bf213',
     'Provides battery backup only for a short period of time to prevent data loss', 'R'),
    ('975dbc3f-5933-48fd-9455-71effba7f257',
     'A compromised computer being remotely controlled by a hacker', 'N'),
    ('8a3c7215-d184-448c-b482-2c5f033774a2',
     'The trend whereby different household devices are connected to one another', 'T'),
    ('cc575bdd-cd1b-4225-b6c1-bc31507a9ab5',
     'A software application used to view and explore pages on the web', 'K'),
    ('ef28e50d-efb0-47b8-839c-b23d41ba7fd5',
     'A wireless technology used to make wireless payments if the devices are close to the POS', 'Q'),
    ('488ed40b-4ee3-40a2-99b7-e77656e163c3',
     'A type of memory that stores data and instructions permanently', 'D'),
    ('c60b8986-9574-4171-b722-e9721c807250',
     'Multiple software updates installed simultaneously', 'P'),
    ('f36b88cc-9ee5-43cd-a9e4-05a3f237dd2b',
     'Online platforms where many people contribute to a project financially', 'B'),
    ('9f71fbd4-3a3d-4453-b1ce-b29502a06aeb',
     'A feature that uses multiple settings to format an entire document with certain fonts, '
     'colour schemes and effects', 'G'),
    ('17d5f557-82cc-4b78-ae11-7e9d597b522b',
     'A spreadsheet function that chooses one of two options based on a condition', 'J'),
]

OPTIONS = [
    ('A', 'website'),
    ('B', 'crowd funding'),
    ('C', 'botnet'),
    ('D', 'ROM'),
    ('E', 'blogs'),
    ('F', 'COUNTIFS'),
    ('G', 'theme'),
    ('H', 'solar'),
    ('I', 'big data'),
    ('J', 'IF'),
    ('K', 'browser'),
    ('L', 'patch'),
    ('M', 'style'),
    ('N', 'zombie'),
    ('O', 'RFID'),
    ('P', 'service pack'),
    ('Q', 'NFC'),
    ('R', 'UPS'),
    ('S', 'RAM'),
    ('T', 'IoT'),
]

opts_block = 'Options:\n' + '\n'.join(f'{l}) {t}' for l, t in OPTIONS)

con = sqlite3.connect(DB)
cur = con.cursor()

# Sanity: confirm the paper exists
cur.execute("SELECT title FROM generated_papers WHERE id=?", (PID,))
row = cur.fetchone()
assert row, f'paper {PID} not found'
print(f'Patching: {row[0]}')

for idx, (qid, desc, ans) in enumerate(ROWS):
    if idx == 0:
        new_text = f'{desc}\n\n{opts_block}'
    else:
        new_text = desc
    cur.execute(
        'UPDATE question_bank_items SET question_type=?, marks=?, '
        'question_text=?, answer_text=? WHERE id=?',
        ('match_columns', 1, new_text, ans, qid),
    )
    print(f'  2.{idx+1} -> {ans}   ({desc[:60]}...)')

con.commit()
con.close()
print('Done.')
