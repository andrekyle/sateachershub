# -*- coding: utf-8 -*-
"""Fix CAT P1 Nov 2023 cover + instructions + per-question intros (verbatim vs PDF)."""
import json
from app import app, db, GeneratedPaper

PID = '06a40eac-5b21-4ef1-815c-698cecce89f2'

INSTRUCTIONS = """Owing to the nature of this practical examination, it is important to note that, even if you complete the examination early, you will NOT be permitted to leave the examination room until all the administrative tasks associated with the examination have been finalised. During the examination, the standard examination rules regarding leaving the examination room apply.

If you are working on the network, or the data files have been preloaded on your system, you must follow the instructions provided by the invigilator/educator.

At the end of the examination, you must make sure that ALL your answer files are saved on the network/computer as explained to you by the invigilator/educator.

Make absolutely sure that all files can be read. Do NOT save unnecessary files/folders and **do NOT hand in duplicate answer files/folders**. **Do NOT delete any original files that you did not work on.**

The information sheet that has been provided with the question paper **MUST BE COMPLETED AFTER THE THREE-HOUR EXAMINATION SESSION.** Hand it to the invigilator at the end of the examination.

A copy of the master files will be available from the invigilator. Should there be any problems with a file, you may request another copy from the invigilator.

This question paper consists of SEVEN questions. Answer ALL the questions.

Read through each question before answering or solving the problem. Do NOT do more than is required by the question.

Ensure that you save each document using the file name given in the question paper. Save your work regularly as a precaution against possible power failures.

You may NOT use any resource material.

Accuracy will be taken into account.

Ensure that the regional settings are set to South Africa and date and time settings, number settings and currency settings are correctly set.

In all questions involving word processing, you should set the language to English (South Africa). The paper size is assumed to be A4 Portrait, unless instructed otherwise. Use centimetres as the unit of measurement.

Ensure that the Developer tab and Ruler are activated.

Ensure that the decimal symbol is set as a full stop ('.') and the list separator is set as a comma (',').

Formulae and/or functions must be used for ALL calculations in questions involving spreadsheets. Use absolute cell references only where necessary to ensure that formulae are correct when you copy them to other cells in a spreadsheet.
NOTE: All formulae and/or functions should be inserted in such a manner that the correct results will still be obtained even if changes are made to the existing data.

You may NOT use a word processing program such as Word to answer the HTML question.

Borders around images or screenshots in this question paper are intended for clarity. Do NOT insert borders unless you are instructed to do so.

The data files that you need to complete this question paper have been provided to you on the disk/CD/DVD/flash disk or on the disk space allocated to you. The files are provided in the form of a password-protected executable file.
Do the following:
• Double-click on the password-protected executable file: <b>CAT P1 Nov 2023 DATA.exe</b>
• Click on the 'Extract' button.
• Click the 'Show Password' check box.
• Enter the following password: <b>1234cars</b>
• Once extracted, verify the contents of the folder by opening one or more files.
• Once the contents of the files have been verified, rename the folder <b>CAT P1 Nov 2023 DATA</b> with your examination number.
The following list of files will be available in the folder:
• <b>1Top10</b> Word processing document
• <b>1Toyota</b> Image
• <b>2Tips</b> Word processing document
• <b>3CarSales</b> Spreadsheet
• <b>4Sales</b> Spreadsheet
• <b>5Bus</b> Image
• <b>5Card</b> Image
• <b>5Shuttle</b> Database
• <b>6_1Rover</b> Image
• <b>6_1Win</b> HTML file
• <b>6_2Father</b> Image
• <b>6_2Logo</b> Image
• <b>6_2Opening</b> HTML file
• <b>7Bookings</b> Spreadsheet
• <b>7New</b> Word processing document"""

SPREADSHEET_NOTE = """NOTE:
• Use formulae and/or functions for ALL calculations in the spreadsheet.
• Use absolute cell references ONLY where necessary to ensure that formulae are correct when you copy it to other cells in a spreadsheet.
• Insert formulae and/or functions in such a manner that the correct results will still be obtained even if values are changed in the existing data.
• Should you need to use building blocks, use the space allocated for this in the spreadsheet data file."""

QINSTRUCTIONS = [
    # Q1 WORD PROCESSING
    "Open the **1Top10** word processing document and insert your examination number in the header or footer.\n\nThe document contains information about the top ten car brand sales in South Africa during 2022.",
    # Q2 WORD PROCESSING
    "Open the **2Tips** word processing document and insert your examination number in the header or footer.\n\nThe document contains tips that can be followed when buying a vehicle.",
    # Q3 SPREADSHEET
    SPREADSHEET_NOTE + "\n\nOpen the **3CarSales** spreadsheet which contains the number of cars sold by the salespersons for the period October 2022 to September 2023.\n\nWork in the **Total** worksheet.",
    # Q4 SPREADSHEET
    SPREADSHEET_NOTE + "\n\nOpen the **4Sales** spreadsheet which contains information on cars bought in September 2023 at Sam's Dealership.\n\nNOTE: A dialogue box will display when opening the file. Click on OK.\n\nWork in the **Sales** worksheet.",
    # Q5 DATABASE
    "The database contains information on the drivers and clients of a shuttle company.\n\nOpen the **5Shuttle** database.",
    # Q6 WEB DESIGN (HTML)
    "NOTE:\n• You may NOT use a word processing program such as Word to answer the HTML questions.\n• An HTML tag sheet has been attached for reference.\n• All files needed to complete this question can be found in the data folder.\n\nA web page was created for a promotional competition to win a car from Sam's Dealership.",
    # Q7 GENERAL
    "Open the **7New** word processing document.",
]

with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    p.total_marks = 150
    p.cover_subtitle = 'Confidential'
    p.sub_header = 'NSC Confidential'
    p.cover_extra_note = 'This question paper consists of 16 pages, an HTML tag sheet, an input mask character sheet, two pages for planning and a separate information sheet.'
    p.instructions = INSTRUCTIONS  # NO [Auto] prefix -> auto-fill won't overwrite

    secs = json.loads(p.sections or '[]')
    sec = secs[0]
    sec['qinstructions'] = QINSTRUCTIONS
    sec['qtitles'] = ['WORD PROCESSING', 'WORD PROCESSING', 'SPREADSHEET',
                      'SPREADSHEET', 'DATABASE', 'WEB DESIGN (HTML)', 'GENERAL']
    p.sections = json.dumps(secs, ensure_ascii=False)
    db.session.commit()
    print("DONE. total_marks=", p.total_marks)
    print("cover_subtitle=", p.cover_subtitle, "sub_header=", p.sub_header)
    print("qtitles=", sec['qtitles'])
