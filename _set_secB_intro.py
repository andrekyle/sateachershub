"""Move the Section B intro from qinstructions[0] to sec.instructions."""
import sqlite3, json
PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
INTRO = (
    'An input mask character sheet is provided as Annexure B. Save the '
    'database after each subquestion to ensure that no work is lost. '
    'Do NOT add or remove records from the table unless asked to do so. '
    'An information sheet with HTML tags is provided as Annexure A. '
    'A text editor (e.g. Notepad++) MUST be used to answer the web '
    'development question. ANY HTML QUESTION ANSWERED USING A WORD '
    'PROCESSOR OR OTHER WEB DESIGN SOFTWARE (e.g. Dreamweaver, Wix, '
    'WordPress) WILL NOT BE MARKED. All changes made to web pages must '
    'be saved before the file is closed.'
)
c = sqlite3.connect('instance/brandcartel.db')
cur = c.cursor()
cur.execute("SELECT sections FROM generated_papers WHERE id=?", (PID,))
secs = json.loads(cur.fetchone()[0])
sb = secs[1]
qi = sb.get('qinstructions') or []
if qi and qi[0]:
    print('Clearing Section B qinstructions[0]')
    qi[0] = ''
    sb['qinstructions'] = qi
sb['instructions'] = INTRO
print(f'Set sec.instructions for Section B (len={len(INTRO)})')
secs[1] = sb
cur.execute("UPDATE generated_papers SET sections=? WHERE id=?", (json.dumps(secs), PID))
c.commit()
print('done')
