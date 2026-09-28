import sqlite3, json

PAPER = '48c8c8d1-b356-490a-90a6-56868b67d10d'
QID_71 = '36989481-6cf5-4ecf-b765-e4acd566984e'
QID_72 = '773d462c-a76f-4593-a6c3-05b02af2f761'
QID_73 = '061eb638-7f6c-4c74-b522-d2b018251e83'

# Q7.1: stem + bullets + "Do NOT complete the mail merge."
NEW_Q71 = ('Prepare a mail merge document as follows:\n\n'
           '• Link the 7Letter document with the 7NewStudents spreadsheet.\n'
           "• Select only students who enrolled for the 'Web Design' or the 'Game Development' courses.\n"
           '• Add the <i>First name_Voornaam</i> merge field to the letter.\n\n'
           'Do NOT complete the mail merge.')

POST_71 = ('Save and close the 7Letter document.\n\n'
           'Open the 7Stats spreadsheet.\n\n'
           'Work in the TotalCost worksheet.')

# Q7.2: stem only; Steps go to qpost so figure renders between
NEW_Q72 = ("TechnoGeek's head office wants to calculate the total income percentage in cell C5 per course (cell B5).\n\n"
           'Use the steps below to calculate the total income percentage for a specific course, as displayed in the example below.')

POST_72 = ('**Step 1:**\n'
           '• Use a formula in cell E8 to determine the total income for Web Design.\n\n'
           '**Step 2:**\n'
           '• Create a data validation drop-down list in cell B5 and use the list in the Courses worksheet.\n\n'
           '**Step 3:**\n'
           '• Modify the function in cell C5 so that the total income percentage per course is automatically calculated based on the type of course selected in cell B5. (5)\n\n'
           'Work in the Time worksheet.')

# Q7.3: stem + bullets only; figure renders, then post text
NEW_Q73 = ('Students who completed a course will collect their certificates in an allocated time slot on a specific day as follows:\n\n'
           '• Times will be between 07:00 and 10:00 (inclusive).\n'
           '• Time slots are in intervals of 15 minutes.\n'
           '• There will be 12 intervals.')

POST_73 = ('Modify the function in cell D3 to randomly generate a time slot for each student.\n\n'
           '**NOTE:** Ignore if students have the same time slot. (5)\n\n'
           'Save and close the 7Stats spreadsheet.')

c = sqlite3.connect('instance/brandcartel.db')
c.execute("UPDATE question_bank_items SET question_text=? WHERE id=?", (NEW_Q71, QID_71))
c.execute("UPDATE question_bank_items SET question_text=?, image_path=? WHERE id=?",
          (NEW_Q72, 'uploads/cat_p1_n25/q7_2.png', QID_72))
c.execute("UPDATE question_bank_items SET question_text=?, image_path=? WHERE id=?",
          (NEW_Q73, 'uploads/cat_p1_n25/q7_3.png', QID_73))

s = c.execute("SELECT sections FROM generated_papers WHERE id=?", (PAPER,)).fetchone()[0]
sec = json.loads(s)
qpt = sec[0].get('qpost_texts') or {}
qpt[QID_71] = POST_71
qpt[QID_72] = POST_72
qpt[QID_73] = POST_73
sec[0]['qpost_texts'] = qpt
c.execute("UPDATE generated_papers SET sections=? WHERE id=?", (json.dumps(sec), PAPER))
c.commit()
print('OK. qpost_texts keys:', list(qpt.keys()))
