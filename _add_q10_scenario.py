"""Add per-question scenario for Q10 in Section C; clean Q10 stem text duplicate."""
import sqlite3, json

PAPER_ID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
Q10_SCN = ("A welcoming committee needs to organise an orientation week for 150 Grade 8 learners. "
           "The learners will be placed into specific groups that will participate in different activities.")

c = sqlite3.connect('instance/brandcartel.db')
(raw,) = c.execute("select sections from generated_papers where id=?", (PAPER_ID,)).fetchone()
secs = json.loads(raw)
secC = secs[2]

scenarios = secC.get('scenarios') or {}
scenarios['10'] = Q10_SCN
secC['scenarios'] = scenarios

# qids[21] is the start of Q10 (per splits=[0,21]). Item 21 currently holds the
# scenario text as a stem ('The committee chairperson...'). Q10's first real
# subitem starts at index 22 (10.1.1). Wait — looking at inspector output:
# [21] = 'The committee chairperson will do a presentation at the welcoming ceremony in the ...'
# That's actually 10.1's stem about presentations, NOT the scenario itself.
# The PDF screenshot's bordered scenario is the WHOLE-Q10 intro that appears
# between QUESTION 10 heading and 10.1. Currently nothing in our DB holds it.
# So just adding it via secC['scenarios']['10'] is correct.

c.execute("update generated_papers set sections=? where id=?", (json.dumps(secs), PAPER_ID))
c.commit()
print("Set sec.scenarios['10'] =", scenarios['10'][:80], "...")
