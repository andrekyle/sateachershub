"""Add a post_text on Q6.1 (after the figure) containing the NOTE block.
Template already renders q.post_text below the figure."""
import sqlite3, json
c = sqlite3.connect('instance/brandcartel.db')
PID = '48c8c8d1-b356-490a-90a6-56868b67d10d'
QID_61 = '93ef504a-d10e-4a6d-a141-35985cd16340'
NOTE = (
    "NOTE:\n"
    "• Use the example on the previous page as a guideline when answering "
    "this question.\n"
    "• Question numbers appear as comments in the coding to indicate where "
    "you should insert the answer(s). Do NOT delete these comments."
)
r = c.execute("SELECT sections FROM generated_papers WHERE id=?", (PID,)).fetchone()
s = json.loads(r[0])
sec0 = s[0]
qp = sec0.get('qpost_texts') or {}
qp[QID_61] = NOTE
sec0['qpost_texts'] = qp
c.execute("UPDATE generated_papers SET sections=? WHERE id=?",
          (json.dumps(s), PID))
c.commit()
print('post_text set')
