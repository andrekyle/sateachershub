import sqlite3
c = sqlite3.connect('instance/brandcartel.db')
rows = c.execute("""
    select id, title, created_at from generated_papers
    where title like '%2025%' or title like '%Nov%' or title like '%P2%' or title like '%CAT%'
    order by created_at desc limit 30
""").fetchall()
for r in rows:
    print(r)
