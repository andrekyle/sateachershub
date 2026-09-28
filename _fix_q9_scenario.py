"""Move Q9 intro from qinstructions[0] into sec.scenario so it renders inside the bordered .scenario-box."""
import sqlite3, json

PAPER_ID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
INTRO = "Mr Brown is establishing a coding and robotics club at the school. The club will consist of learners from all grades and volunteer teachers."

c = sqlite3.connect('instance/brandcartel.db')
(raw,) = c.execute("select sections from generated_papers where id=?", (PAPER_ID,)).fetchone()
secs = json.loads(raw)
secC = secs[2]
secC['scenario'] = INTRO
# Clear the qinstructions[0] we set previously so the text isn't duplicated under QUESTION 9.
if secC.get('qinstructions') and len(secC['qinstructions']) > 0:
    secC['qinstructions'][0] = ''
c.execute("update generated_papers set sections=? where id=?", (json.dumps(secs), PAPER_ID))
c.commit()
print("scenario =", secC['scenario'][:80], "...")
print("qinstructions[0] =", repr(secC['qinstructions'][0]))
