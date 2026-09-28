# -*- coding: utf-8 -*-
"""Correct the front matter (cover note, running header, instructions +
inline file list) of CAT P1 May/June 2021 so it matches the uploaded
DBE PDF verbatim. Also fix two CAT P1 papers whose stored total_marks
is wrong (Nov 2021 & May/June 2022 are 150-mark papers)."""
import app
from app import app as a, GeneratedPaper, db

INSTRUCTIONS = "\n\n".join([
    "Owing to the nature of this practical examination, it is important to note that, even if you complete the examination early, you will NOT be permitted to leave the examination room until all the administrative functions associated with the examination have been finalised. During the examination, the normal rules regarding leaving the examination room apply.",
    "If you are working on the network, or the data files have been preloaded, you must follow the instructions provided by the invigilator/educator. Alternatively, the invigilator will give you a CD/DVD/flash drive containing all the files needed for the examination. If a CD/DVD/flash drive has been issued to you, you must write your examination number and centre number on the CD/DVD/flash drive.",
    "At the end of the examination, you must hand in the CD/DVD/flash drive given to you by the invigilator with ALL your answer files saved onto the CD/DVD/flash drive, OR you should make sure that ALL the answer files are saved on the network/computer as explained to you by the invigilator/educator.",
    "Make absolutely sure that all files can be read. Do NOT save unnecessary files/folders and do NOT hand in duplicate answer files/folders. Do NOT delete any original files that you did not work on.",
    "The information sheet that has been provided with the question paper MUST BE COMPLETED AFTER THE THREE-HOUR EXAMINATION SESSION. Hand it to the invigilator at the end of the examination.",
    "A copy of the master files will be available from the invigilator. Should there be any problems with a file, you may request another copy from the invigilator.",
    "This question paper consists of SEVEN questions. Answer ALL the questions.",
    "Read through each question before answering or solving the problem. Do NOT do more than is required by the question.",
    "Read the question carefully as accuracy will be taken into account.",
    "Ensure that you save each document using the file name given in the question paper. Save your work at regular intervals as a precaution against possible power failures.",
    "You may NOT use any resource material.",
    "Ensure that the regional settings are set to South Africa and that date and time settings, number settings and currency settings are correctly set.",
    "In all questions involving word processing, you should set the language to English (South Africa). The paper size is assumed to be A4 Portrait, unless instructed otherwise. Use centimetres as the unit of measurement.",
    "Formulae and/or functions must be used for ALL calculations in questions involving spreadsheets. Use absolute cell references only where necessary to ensure that formulae are correct when you copy them to other cells in a spreadsheet.\nNOTE: All formulae and/or functions should be inserted in such a manner that the correct results will still be obtained even if changes are made to the existing data.",
    "You may NOT use a word processing program such as Word to answer the HTML question.",
    "\n".join([
        "The examination folder/CD/DVD/flash drive that you receive with this question paper contains the files listed below. Ensure that you have all the files before you begin with this examination.",
        "\u2022 1Review \u2013 Word processing file",
        "\u2022 2History \u2013 Word processing file",
        "\u2022 3Countries \u2013 Spreadsheet",
        "\u2022 3Open \u2013 Compressed folder",
        "\u2022 4Donate \u2013 Spreadsheet",
        "\u2022 5Rescue \u2013 Image",
        "\u2022 5Support \u2013 Database",
        "\u2022 6_1Picture \u2013 Image",
        "\u2022 6_1Sierra \u2013 HTML file",
        "\u2022 6_2Progress \u2013 Image",
        "\u2022 6_2Wash \u2013 HTML file",
        "\u2022 7Distribute \u2013 Word processing file",
        "\u2022 7Prospects \u2013 Spreadsheet",
        "\u2022 7Reorder \u2013 Spreadsheet",
    ]),
])

with a.app_context():
    p = db.session.get(GeneratedPaper, '59936ea1-87fc-4507-8f15-4c4c77e22dfd')
    p.instructions = INSTRUCTIONS
    p.cover_extra_note = ("This question paper consists of 18 pages, an HTML tag "
                          "sheet, an input mask character sheet and a separate "
                          "information sheet.")
    p.header_right = 'DBE/{{year}}'      # -> "DBE/2021" (no month label)
    p.sub_header = 'SC/NSC'              # running sub-header line
    p.cover_subtitle = ''               # remove the "Past Paper Template" badge
    p.total_marks = 180                 # PDF: MARKS: 180
    p.data_files = ''                   # file list is inline in instruction 16

    # Correct two CAT P1 papers whose stored marks contradict their PDFs
    # (both are 150-mark papers) so the cover/total stay right once the
    # template starts honouring total_marks.
    for pid_like, marks in [('CAT P1 Nov 2021', 150), ('CAT P1 May-June 2022', 150)]:
        q = GeneratedPaper.query.filter(GeneratedPaper.title == pid_like).first()
        if q and q.total_marks != marks:
            q.total_marks = marks
            print('Fixed', pid_like, '-> total_marks', marks)

    db.session.commit()
    print('Updated P1 2021 front matter. instructions items:',
          len(p.instructions.split('\n\n')))
