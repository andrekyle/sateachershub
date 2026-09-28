# -*- coding: utf-8 -*-
"""Clean CAT P1 Nov 2023 item text: strip embedded (N) marks, move closers /
worksheet-context lines to qpost_texts, and remove the HTML-tag-sheet dump."""
import json
from app import app, db, GeneratedPaper, QuestionBankItem

PID = '06a40eac-5b21-4ef1-815c-698cecce89f2'

# idx -> (new_question_text, post_text)
# post_text = '' means leave existing post_text untouched / none.
FIXES = {
    # 1.9 — strip (2), move closer
    8: ("Insert the file path in the header of the last page only.",
        "Save and close the **1Top10** document."),
    # 2.7 — strip (4), move closer
    19: ("Find the SmartArt on the last page and format the SmartArt to appear as shown in the example below.\n\nNOTE: A '3D Cartoon' style was applied.",
         "Save and close the **2Tips** document."),
    # 3.5 — strip (6), move closer
    24: ("Insert a lookup function in cell F23 to display the name of the salesperson who sold the most cars for the period 2022/2023.",
         "Save and close the **3CarSales** spreadsheet."),
    # 4.5 — strip (4), move worksheet-context line for 4.6
    29: ("The total cost for a car is calculated by adding the price and the interest. However, if a buyer wants extra accessories (column G), an additional 5% is added to the total cost.\n\nInsert a formula/function in cell H10 to calculate the final total cost for Basson.",
         "Work in the **Chart** worksheet."),
    # 4.6 — strip (6), move closer
    30: ("Modify the chart to appear as the example below.\n\nNOTE: The column colours have been set to vary by point.",
         "Save and close the **4Sales** spreadsheet."),
    # 5.1.5 — strip (4), move table closer
    35: ("Insert a new field called LicenceCard above the LicenceNo field.\n\nInsert the 5Card image, in Datasheet View, for the driver Mark Lopez.",
         "Save and close the **tbl5_1** table."),
    # 5.6 — strip (5), move db closer
    40: ("Open the rpt5_6 report, based on the Pre-bookings table, in Design View and modify as follows:\n\n•  Insert a function in the group footer to indicate the total clients per Reason.\n•  Change the page orientation to landscape.\n•  Export the report as a PDF document called 5Pre-bookings to your data folder.",
         "Save and close the **rpt5_6** report.\n\nSave and close the **5Shuttle** database."),
    # 6.1.5 — strip (2), move file closer
    46: ("Modify the HTML code to display the list as shown in the example on the previous page.",
         "Save and close the **6_1Win** file."),
    # 6.2 — strip (5)+(1); move closer + ONE-mark note
    47: ("Open the incomplete 6_2Opening web page in a web browser and also in a text/HTML editor.\n\nComplete the web page to resemble the example below.",
         "Save and close the **6_2Opening** file.\n\nONE mark will be allocated for closing tags and correct nesting in both the files.   (1)"),
    # 7.1 — strip (5), move closer
    48: ("The shuttle company is upgrading their logo. Use WordArt and the images in the file to create a new logo, as shown below.\n\nNOTE:\n•  The final logo should be one image.\n•  Save the final logo as an image called 7NewLogo.",
         "Save and close the **7New** document."),
    # 7.2.3 — strip (2), remove tag-sheet dump, move closer
    52: ("Edit the worksheet as follows:\n\n• Change the settings to make sure that when the entire worksheet is printed, the information in columns A to G will appear on the first page.\n• Edit the print options to include the row and column headings.",
         "Save and close the **7Bookings** spreadsheet."),
}

with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = json.loads(p.sections)
    sec = secs[0]
    qids = sec['question_ids']
    qpost = sec.get('qpost_texts') or {}
    for idx, (newtext, post) in FIXES.items():
        qid = qids[idx]
        q = db.session.get(QuestionBankItem, qid)
        q.question_text = newtext
        if post:
            qpost[qid] = post
    sec['qpost_texts'] = qpost
    p.sections = json.dumps(secs, ensure_ascii=False)
    db.session.commit()
    print("DONE. cleaned", len(FIXES), "items; qpost_texts keys:", list(qpost.keys()))
