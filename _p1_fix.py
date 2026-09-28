import json, uuid
import app as appmod

PID = "60471f83-d846-48f7-9195-629c43e3ab8f"

# ---- per-question intros (instructions) ----
NOTE_SS = ("NOTE:\n"
    "\u2022 Use formulae and/or functions for ALL calculations in the spreadsheet.\n"
    "\u2022 Use absolute cell references ONLY where necessary to ensure that formulae are correct when you copy it to other cells in a spreadsheet.\n"
    "\u2022 Insert formulae and/or functions in such a manner that the correct results will still be obtained even if changes are made to the existing data.\n"
    "\u2022 Should you need to use building blocks, use the space allocated for this in the spreadsheet data file.")

QINSTR = [
    ("Open the **1eSports** word processing document that contains information about eSports "
     "and some of the major players of this sport.\n\n"
     "Insert your examination number in the header of the document."),
    ("Open the **2Stats** word processing document that contains information about eSports "
     "statistics, tournaments, prizes and the highest-earning players.\n\n"
     "Insert your examination number in the header of the document."),
    (NOTE_SS + "\n\n"
     "Open the **3Rank** spreadsheet that contains information about tournaments and the winnings of the players.\n\n"
     "Work in the Sheet1 worksheet."),
    (NOTE_SS + "\n\n"
     "Open the **4Shop** spreadsheet that contains details of products sold during April at the Gamers Shop.\n\n"
     "Work in the April worksheet."),
    ("A table was created with all the upcoming eSports tournament events.\n\n"
     "Open the **5Games** database."),
    ("NOTE:\n"
     "\u2022 You may NOT use a word processing program such as Word to answer the HTML questions.\n"
     "\u2022 An HTML tag sheet has been attached for reference.\n"
     "\u2022 All files needed to complete this question can be found in the examination folder.\n\n"
     "Modify a web page about an eSports tournament The Rising Sun School will host."),
    "",
]

SCENARIO = ("ESports is a sports competition using video games. There are various tournaments "
            "where individuals or teams can compete for prizes or money.")

# ---- cleaned item texts keyed by QID (remove duplicate inline marks; keep outros baked) ----
CLEAN = {
 # 1.11
 "f16a0557-ee4f-47ce-a59a-67652c067b27":
   "Find the text below the heading 'Budget for 2026' and change the text into a table to appear as shown in the example below.\n\nSave and close the 1eSports document.",
 # 2.7
 "898e5d8e-a8fd-4737-90c5-2d4c1eedc40d":
   "Find the text box at the end of the document and do the following:\n\n\u2022 Insert the total number of words as a field in the format: First, Second, Third, \u2026\n\u2022 Change the direction of the text to horizontal.\n\nSave and close the 2Stats document.",
 # 3.1
 "2d0f6299-b25a-4032-9bb6-4f9ddb53cf75":
   "Rename Sheet1 to Medals and move the worksheet to appear as the last worksheet in the workbook.\n\nWork in the Players worksheet.",
 # 3.4
 "ae624d44-cc66-425a-986c-76995e632bf5":
   "Insert a formula in cell F6 to calculate what percentage Sven's total prize money is of his overall prize money.\n\nWork in the Tournament worksheet.",
 # 3.7
 "da017089-918b-4ff6-874b-d719efb79200":
   "An attempt was made to find the three-letter abbreviation of each country from the CountryCode worksheet.\n\nModify the function in cell F9 so the correct abbreviation will be shown.\n\nSave and close the 3Rank spreadsheet.",
 # 4.3
 "e5147f04-a2ea-4323-a3bd-08dcd3e6c29b":
   "The shop will send a notice to a customer with a 24-month contract.\n\nInsert a function in cell I6 to display the text 'Notice' if a customer has a 24-month contract; otherwise the cell must be left blank.\n\nWork in the Games worksheet.",
 # 4.5
 "8a3086f6-45c6-4a8b-97ee-3d21d9fbbba0":
   "Create a chart/graph to display as shown in the example below.\n\nNOTE:\n\u2022 Use the 4Screen image in your examination folder.\n\u2022 Move the chart to a new sheet called 'Price'.\n\nSave and close the 4Shop spreadsheet.",
 # 5.1.4 (Prize)
 "d3826c28-da12-4c89-a65f-61a02768d2c7":
   "Edit the Prize field so that it only accepts values above R15 000. Add any descriptive text that refers to the rule.\n\nSave and close the tbl5_1 table.",
 # 5.2
 "e751fd66-ddc7-4a53-8722-f6fc91afadf7":
   "Modify the frm5_2 form to display as shown in the example below.\n\nNOTE:\n\u2022 10% discount will be given on the registration fee for all the games listed.\n\u2022 Use the picture in the form footer.\n\nSave and close the frm5_2 form.",
 # 5.5
 "a7292bac-68f3-4244-9ee2-831abcd14c63":
   "Modify the qry5_5 query based on the tblGames table in Design View to display as shown in the example below.\n\nSave and close the qry5_5 query.",
 # 5.7
 "0d141d57-f6fb-4ae6-aa36-9db4d97c5511":
   "Create a report called rpt5_7 based on the tblGames table, as shown in the example below.\n\nNOTE: Ignore the format and border of the text box.\n\nSave and close the rpt5_7 report.\n\nSave and close the 5Games database.",
 # 6.1.6
 "c1fbb3ce-87af-45e3-92b0-7681949f6952":
   "Correct the HTML code at the end of the document so that the hyperlink will move to the web page.\n\nSave and close the 6_1Tournament file.",
 # 6.2
 "b37f023d-ee84-48e8-8a6d-ec669affb0f2":
   "Open the incomplete 6_2Entry web page in a web browser and also in a text/HTML editor (NOT a word processing program such as Word).\n\nComplete the web page to appear as shown in the example below.\n\nNOTE: The background colour should be light yellow.\n\nSave and close the 6_2Entry file.\n\nONE mark will be allocated for closing tags and correct nesting in both web pages. (1)",
 # 7.4 (strip the garbled tag-sheet dump entirely)
 "0181bc05-ac34-483c-899a-e1567c1d59c4":
   "Open the incomplete 7Results web page in a web browser and also in a text/HTML editor (NOT a word processing program such as Word).\n\nComplete the web page to appear as shown in the example below.\n\nNOTE: Add a 3 pt border around the image.",
}

# ---- marks fixes by QID ----
MARKS = {
 "e751fd66-ddc7-4a53-8722-f6fc91afadf7": 6,  # 5.2
 "474f2a75-2ee2-4945-884d-cd68cd5ea216": 4,  # 5.3
 "b37f023d-ee84-48e8-8a6d-ec669affb0f2": 4,  # 6.2
}

# ---- example images by QID: (path under static/, image_width %) ----
IMGS = {
 "7b51f188-a5f7-4524-82c1-d9b87df50eaf": ("uploads/cat_p1_mj25/q1_8_smartart.png", 78),   # 1.8
 "f16a0557-ee4f-47ce-a59a-67652c067b27": ("uploads/cat_p1_mj25/q1_11_table.png", 60),     # 1.11
 "af122592-78b8-4462-a265-f5e9e3237c14": ("uploads/cat_p1_mj25/q2_4.png", 38),            # 2.4
 "180e3f3a-d81d-48b6-9934-23882f4b242a": ("uploads/cat_p1_mj25/q3_2_headings.png", 80),   # 3.2
 "8a3086f6-45c6-4a8b-97ee-3d21d9fbbba0": ("uploads/cat_p1_mj25/q4_5_chart.png", 82),      # 4.5
 "001d6bb5-efe0-499c-acf4-a8c57c293d4a": ("uploads/cat_p1_mj25/q5_1_3_location.png", 16), # 5.1.3
 "e751fd66-ddc7-4a53-8722-f6fc91afadf7": ("uploads/cat_p1_mj25/q5_2_form.png", 80),       # 5.2
 "a7292bac-68f3-4244-9ee2-831abcd14c63": ("uploads/cat_p1_mj25/q5_5_query.png", 42),      # 5.5
 "0d141d57-f6fb-4ae6-aa36-9db4d97c5511": ("uploads/cat_p1_mj25/q5_7_report.png", 85),     # 5.7
 "036e32d6-dff4-48e7-9062-c20c1026d454": ("uploads/cat_p1_mj25/q6_1_web.png", 78),        # 6.1
 "b37f023d-ee84-48e8-8a6d-ec669affb0f2": ("uploads/cat_p1_mj25/q6_2_web.png", 60),        # 6.2
 "0181bc05-ac34-483c-899a-e1567c1d59c4": ("uploads/cat_p1_mj25/q7_4_web.png", 42),        # 7.4
}

TOURN_QID = "23c80a80-4dfd-4ce0-9f31-50c28c11d60c"  # 5.1.1 Tournament (insert stem before this)

with appmod.app.app_context():
    db = appmod.db
    p = appmod.GeneratedPaper.query.get(PID)
    secs = json.loads(p.sections or "[]")
    sec = secs[0]
    qids = sec["question_ids"]
    items = {q.id: q for q in appmod.QuestionBankItem.query.filter(appmod.QuestionBankItem.id.in_(qids)).all()}

    # 1. scenario + qinstructions + qoutros
    sec["scenario"] = SCENARIO
    sec["qinstructions"] = QINSTR
    sec["qoutros"] = ["", "", "", "", "", "",
        "Save and close the 7Results file.\n\nHTML TAG SHEET\n\nINPUT MASK CHARACTER SHEET"]

    # 2. clean texts
    for qid, txt in CLEAN.items():
        items[qid].question_text = txt

    # 3. marks
    for qid, m in MARKS.items():
        items[qid].marks = m

    # 4. images
    for qid, (path, w) in IMGS.items():
        items[qid].image_path = path
        items[qid].image_width = w

    # 5. insert 5.1 stem
    ref = items[TOURN_QID]
    stem = appmod.QuestionBankItem(
        id=str(uuid.uuid4()), owner_id=p.owner_id, grade=ref.grade, subject=ref.subject,
        topic=ref.topic, subtopic=getattr(ref, "subtopic", None),
        question_type="short_answer", marks=0,
        question_text="Open the tbl5_1 table in Design View.",
        answer_text="", image_path="", image_width=0)
    db.session.add(stem)
    pos = qids.index(TOURN_QID)
    qids.insert(pos, stem.id)
    sec["splits"] = [s + 1 if s > pos else s for s in sec.get("splits", [])]
    new_sub = [s + 1 if s >= pos else s for s in sec.get("subitems", [])]
    new_sub.append(pos + 1)  # Tournament (now 5.1.1) at pos+1
    sec["subitems"] = sorted(set(new_sub))

    # 6. total marks
    p.total_marks = 150

    sec["question_ids"] = qids
    secs[0] = sec
    p.sections = json.dumps(secs, ensure_ascii=False)
    db.session.commit()

    # verify totals
    items2 = {q.id: q for q in appmod.QuestionBankItem.query.filter(appmod.QuestionBankItem.id.in_(qids)).all()}
    splits = sec["splits"]
    print("splits=", splits)
    print("subitems=", sec["subitems"])
    bounds = splits + [len(qids)]
    grand = 0
    for gi in range(len(splits)):
        a, b = bounds[gi], bounds[gi+1]
        tot = sum(items2[qids[j]].marks or 0 for j in range(a, b))
        grand += tot
        print(f"  Q{gi+1}: items {a}-{b-1} sum={tot}")
    print("GRAND (item sum) =", grand)
    print("total_marks field =", p.total_marks)
    print("Committed.")
