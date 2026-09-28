# -*- coding: utf-8 -*-
from app import app, db, GeneratedPaper
PID = '2b687490-9157-4e10-b0c9-2bab1ee303fd'

INSTR = "\n\n".join([
 "Owing to the nature of this practical examination, it is important to note that, even if you complete the examination early, you will NOT be permitted to leave the examination room until all the administrative tasks associated with the examination have been finalised. During the examination, the standard examination rules regarding leaving the examination room apply.",
 "If you are working on the network, or the data files have been preloaded on your system, you must follow the instructions provided by the invigilator/educator.",
 "At the end of the examination, you must make sure that ALL your answer files are saved on the network/computer as explained to you by the invigilator/educator.",
 "Make absolutely sure that all files can be read. Do NOT save unnecessary files/folders and do NOT hand in duplicate answer files/folders. Do NOT delete any original files that you did not work on.",
 "The information sheet that has been provided with the question paper MUST BE COMPLETED AFTER THE THREE-HOUR EXAMINATION SESSION. Hand it to the invigilator at the end of the examination.",
 "A copy of the master files will be available from the invigilator. Should there be any problems with a file, you may request another copy from the invigilator.",
 "This question paper consists of SEVEN questions. Answer ALL the questions.",
 "Read through each question before answering or solving the problem. Do NOT do more than is required by the question.",
 "Ensure that you save each document using the file name given in the question paper. Save your work regularly as a precaution against possible power failures.",
 "You may NOT use any resource material.",
 "Accuracy will be taken into account.",
 "Ensure that the regional settings are set to South Africa and date and time settings, number settings and currency settings are correctly set.",
 "In all questions involving word processing, you should set the language to English (South Africa). The paper size is assumed to be A4 Portrait, unless instructed otherwise. Use centimetres as the unit of measurement.",
 "Ensure that the Developer tab and Ruler are activated.",
 "Ensure that the decimal symbol is set as a full stop ('.') and the list separator is set as a comma (',').",
 "Formulae and/or functions must be used for ALL calculations in questions involving spreadsheets. Use absolute cell references only where necessary to ensure that formulae are correct when you copy them to other cells in a spreadsheet.\nNOTE: All formulae and/or functions should be inserted in such a manner that the correct results will still be obtained even if changes are made to the existing data.",
 "You may NOT use a word processing program such as Word to answer the HTML question.",
 ("The examination data folder that you receive with this question paper contains the files listed below. "
  "Ensure that you have all the files before you begin with this examination.\n"
  "\u2022 **1Clean** Image\n"
  "\u2022 **1Health** Word processing file\n"
  "\u2022 **2Marine** Word processing file\n"
  "\u2022 **3Logo** Image\n"
  "\u2022 **3Projects** Spreadsheet\n"
  "\u2022 **4Air** Spreadsheet\n"
  "\u2022 **5Save** Database\n"
  "\u2022 **6_1Clean** HTML file\n"
  "\u2022 **6_1Plastic** Image\n"
  "\u2022 **6_2Pollute** HTML file\n"
  "\u2022 **7Company** Spreadsheet\n"
  "\u2022 **7Date** Spreadsheet\n"
  "\u2022 **7Letter** Word processing file\n"
  "\u2022 **7Picture** Compressed file"),
])

with app.app_context():
    p = GeneratedPaper.query.get(PID)
    p.cover_subtitle = ''
    p.sub_header = 'NSC Confidential'
    p.cover_extra_note = ("This question paper consists of 16 pages, an HTML tag sheet, "
                          "an input mask character sheet, two pages for planning and a separate information sheet.")
    p.instructions = INSTR
    db.session.commit()
    print('cover_subtitle=', repr(p.cover_subtitle))
    print('sub_header=', repr(p.sub_header))
    print('cover_extra_note=', repr(p.cover_extra_note))
    print('instr items:', p.instructions.count('\n\n') + 1)
