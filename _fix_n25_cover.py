"""Comprehensive DB fixes for CAT P1 Nov 2025 paper to match the DBE PDF."""
import sqlite3, json

PAPER_ID = '48c8c8d1-b356-490a-90a6-56868b67d10d'
DB = 'instance/brandcartel.db'

c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row

# ----- 1. Cover-page authority + subtitle + page-count + total marks -----
cover_authority = 'NATIONAL\nSENIOR CERTIFICATE\nGRADE 12'
cover_subtitle  = 'Confidential'
cover_extra_note = (
    "This question paper consists of 19 pages, an HTML tag sheet, "
    "an input mask character sheet, two pages for planning and "
    "a separate information sheet."
)

# ----- 2. Instructions (verbatim from PDF, numbered 1..20) -----
INSTRUCTIONS = [
    # 1
    "Owing to the nature of this practical examination, it is important to note that, "
    "even if you complete the examination early, you will NOT be permitted to leave "
    "the examination room until all the administrative tasks associated with the "
    "examination have been finalised. During the examination, the standard "
    "examination rules regarding leaving the examination room apply.",
    # 2
    "If you are working on the network, or the data files have been preloaded on "
    "your system, you must follow the instructions provided by the invigilator/"
    "teacher.",
    # 3
    "At the end of the examination, you must make sure that ALL your answer files "
    "are saved on the network/computer as explained to you by the invigilator/"
    "teacher.",
    # 4
    "Make absolutely sure that all files can be read. Do NOT save unnecessary "
    "files/folders and do NOT hand in duplicate answer files/folders. Do NOT "
    "delete any original files that you did not work on.",
    # 5
    "The information sheet that has been provided with the question paper MUST "
    "BE COMPLETED AFTER THE THREE-HOUR EXAMINATION SESSION. "
    "Hand it to the invigilator at the end of the examination.",
    # 6
    "A copy of the master files will be available from the invigilator. Should there be "
    "any problems with a file, you may request another copy from the invigilator.",
    # 7
    "This question paper consists of SEVEN questions. Answer ALL the questions.",
    # 8
    "Read through each question before answering or solving the problem. Do NOT "
    "do more than is required by the question.",
    # 9
    "Ensure that you save each document using the file name given in the question "
    "paper. Save your work regularly as a precaution against possible power "
    "failures.",
    # 10
    "You may NOT use any resource material.",
    # 11
    "Accuracy will be taken into account.",
    # 12
    "Ensure that the regional settings are set to South Africa and date and time "
    "settings, number settings and currency settings are correctly set.",
    # 13
    "In all questions involving word processing, you should set the language to "
    "English (South Africa). The paper size is assumed to be A4 Portrait, unless "
    "instructed otherwise. Use centimetres as the unit of measurement.",
    # 14
    "Ensure that the Developer tab and Ruler are activated.",
    # 15
    "Ensure that the decimal symbol is set as a full stop ('.') and the list separator is "
    "set as a comma (',').",
    # 16
    "Formulae and/or functions must be used for ALL calculations in questions "
    "involving spreadsheets. Use absolute cell references only where necessary to "
    "ensure that formulae are correct when you copy them to other cells in a "
    "spreadsheet.\n"
    "NOTE: All formulae and/or functions should be inserted in such a manner that "
    "the correct results will still be obtained even if changes are made to the "
    "existing data.",
    # 17
    "You may NOT use a word processing program such as Word to answer the "
    "HTML question.",
    # 18
    "Borders around images or screenshots in this question paper are intended for "
    "clarity. Do NOT insert borders unless you are instructed to do so.",
    # 19
    "Use the correct settings or features in an application as required by a question.",
    # 20 — data-files block + extraction steps + file list
    "The data files that you need to complete this question paper have been "
    "provided to you on the disk/CD/DVD/flash disk or on the disk space allocated "
    "to you. The files are provided in the form of a password-protected executable "
    "file.\n"
    "Do the following:\n"
    "\u2022 Double-click on the password-protected executable file: "
    "<b>CAT P1 Nov 2025 DATA.exe</b>\n"
    "\u2022 Click on the 'Extract' button.\n"
    "\u2022 Click the 'Show Password' check box.\n"
    "\u2022 Enter the following password: <b>TG25#</b>\n"
    "\u2022 Once extracted, verify the contents of the folder by opening one or more files.\n"
    "\u2022 Delete the .exe file.\n"
    "\u2022 Once the contents of the files have been verified, rename the folder "
    "<b>CAT P1 Nov 2025 DATA</b> with your examination number.\n"
    "The following list of files will be available in the folder:\n"
    "\u2022 <b>1App</b> Image\n"
    "\u2022 <b>1Courses</b> Word processing file\n"
    "\u2022 <b>2Brochure</b> Word processing file\n"
    "\u2022 <b>3Lecturers</b> Spreadsheet\n"
    "\u2022 <b>4Students</b> Spreadsheet\n"
    "\u2022 <b>5Records</b> Database\n"
    "\u2022 <b>6_1Head</b> Image\n"
    "\u2022 <b>6_1Home</b> HTML file\n"
    "\u2022 <b>6_1Tech</b> Image\n"
    "\u2022 <b>6_2Course</b> Image\n"
    "\u2022 <b>6_2Popular</b> HTML file\n"
    "\u2022 <b>7Letter</b> Word processing file\n"
    "\u2022 <b>7NewStudents</b> Spreadsheet\n"
    "\u2022 <b>7Stats</b> Spreadsheet",
]
instructions_str = "[Auto] CAT P1 Nov 2025 (cover instructions)\n\n" + "\n\n".join(INSTRUCTIONS)

# ----- 3. Update sections JSON: add SCENARIO -----
row = c.execute("SELECT sections FROM generated_papers WHERE id=?", (PAPER_ID,)).fetchone()
secs = json.loads(row['sections'])
SCENARIO = (
    "<b>TechnoGeek</b> is a tertiary institution that specialises in computer-related courses. "
    "They have designed a few documents to promote the institution and need your assistance "
    "with modifying the files."
)
for s in secs:
    s['scenario'] = SCENARIO
sections_str = json.dumps(secs)

# ----- 4. Apply -----
c.execute("""UPDATE generated_papers SET
    cover_authority = ?,
    cover_subtitle  = ?,
    cover_extra_note = ?,
    instructions    = ?,
    total_marks     = 150,
    sections        = ?
    WHERE id = ?""",
    (cover_authority, cover_subtitle, cover_extra_note, instructions_str, sections_str, PAPER_ID))
c.commit()
print("Cover/instructions/scenario updated.")
