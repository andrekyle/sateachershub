"""Update per-Question intros (qinstructions) for CAT P1 Nov 2025 with full
opening stems matching the source PDF, including NOTE blocks for Q3/Q4/Q6."""
import sqlite3, json

PAPER_ID = '48c8c8d1-b356-490a-90a6-56868b67d10d'
c = sqlite3.connect('instance/brandcartel.db')

NOTE_SS = (
    "NOTE:\n"
    "\u2022 Use formulae and/or functions for ALL calculations in the spreadsheet.\n"
    "\u2022 Use absolute cell references ONLY where necessary to ensure that formulae are correct when you copy it to other cells in a spreadsheet.\n"
    "\u2022 Insert formulae and/or functions in such a manner that the correct results will still be obtained even if values are changed in the existing data.\n"
    "\u2022 Should you need to use building blocks, use the space allocated for this in the spreadsheet data file."
)

NOTE_HTML = (
    "NOTE:\n"
    "\u2022 You may NOT use a word processing program such as Word to answer the HTML questions.\n"
    "\u2022 An HTML tag sheet has been attached for reference.\n"
    "\u2022 All files needed to complete this question can be found in the examination folder."
)

INTROS = [
    # Q1
    "Open the **1Courses** word processing document that contains information about the different types of courses that TechnoGeek offers.\n\nInsert your examination number in the header of the document.",
    # Q2
    "Open the **2Brochure** word processing document that contains information about the history and courses of the TechnoGeek institution.\n\nInsert your examination number in the header of the document.",
    # Q3
    NOTE_SS + "\n\nOpen the **3Lecturers** spreadsheet that contains information about the lecturers that teach at the different campuses of the TechnoGeek institution.\n\nWork in the Lecturers worksheet.",
    # Q4
    NOTE_SS + "\n\nOpen the **4Students** spreadsheet that contains information about courses which part-time students will take during 2026.\n\nWork in the Students worksheet.",
    # Q5
    "The database contains details of lecturers and students at the TechnoGeek institution.\n\nOpen the **5Records** database.",
    # Q6
    NOTE_HTML + "\n\nA web page was created for the Home page of the TechnoGeek institution.",
    # Q7
    "Open the **7Letter** document that contains an acceptance letter for new students.",
]

row = c.execute("SELECT sections FROM generated_papers WHERE id=?", (PAPER_ID,)).fetchone()
secs = json.loads(row[0])
secs[0]['qinstructions'] = INTROS
c.execute("UPDATE generated_papers SET sections=? WHERE id=?", (json.dumps(secs), PAPER_ID))
c.commit()
print("qinstructions updated.")
