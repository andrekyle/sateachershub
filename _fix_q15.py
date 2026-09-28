"""Update Q1.5 question_text to embed Webdings 209 glyphs."""
import sqlite3
c = sqlite3.connect('instance/brandcartel.db')
new_text = (
    "Find and replace the exact word 'Course' to display as follows: "
    "[wd:209]Info\n\n"
    "Use the symbol [wd:209] (Webdings, character code 209)."
)
c.execute(
    "UPDATE question_bank_items SET question_text = ? WHERE subtopic = ?",
    (new_text, 'CAT P1 Nov 2025 - Q1.5'),
)
c.commit()
print('Q1.5 updated')
