"""Show current cover/instructions/scenario/qinstructions for n25."""
import sqlite3, json
c = sqlite3.connect('instance/brandcartel.db')
r = c.execute("SELECT instructions, sections FROM generated_papers WHERE id = ?",
              ('48c8c8d1-b356-490a-90a6-56868b67d10d',)).fetchone()
print('=== INSTRUCTIONS ===')
print(r[0])
print()
print('=== SECTIONS[0] scenario / qinstructions ===')
s = json.loads(r[1])
print('scenario:', repr(s[0].get('scenario'))[:300])
for i, qi in enumerate(s[0].get('qinstructions') or []):
    print(f'qi[{i}]:', repr(qi)[:300])
