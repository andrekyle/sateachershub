# -*- coding: utf-8 -*-
import json, re
from app import app, db, GeneratedPaper, QuestionBankItem
PID = '2b687490-9157-4e10-b0c9-2bab1ee303fd'

SPREAD_NOTE = ("NOTE:\n"
 "\u2022 Use formulae and/or functions for ALL calculations in the spreadsheet.\n"
 "\u2022 Use absolute cell references ONLY where necessary to ensure that formulae are correct when you copy it to other cells in a spreadsheet.\n"
 "\u2022 Insert formulae and/or functions in such a manner that the correct results will still be obtained even if changes are made to the existing data.\n"
 "\u2022 Should you need to use building blocks, use the space allocated for this in the spreadsheet data file.")

HTML_NOTE = ("NOTE:\n"
 "\u2022 You may NOT use a word processing program such as Word to answer the HTML questions.\n"
 "\u2022 An HTML tag sheet has been attached for reference.\n"
 "\u2022 All files needed to complete this question can be found in the examination folder.")

QINTRO = [
 "Open the **1Health** word processing document and insert your examination number in the header or footer.",
 "Open the **2Marine** word processing document and insert your examination number in the header or footer.",
 SPREAD_NOTE + "\n\nOpen the **3Projects** spreadsheet which contains details of clean-up missions that started in 2019, including some projects planned for the future.\n\nWork in the **Sheet1** worksheet.",
 SPREAD_NOTE + "\n\nThe spreadsheet contains information about the air quality index (AQI) measured at various measuring stations in South Africa, as well as related health incidents from 2012 to 2019.\n\nOpen the **4Air** spreadsheet and work in the **Quality** worksheet.",
 "The municipality keeps track of companies contributing to the pollution problem. As part of the effort, they also investigated residents' recycling habits in terms of solving the pollution problem.\n\nOpen the **5Save** database.",
 HTML_NOTE + "\n\nA website was created to give more information about a possible future without pollution.",
 "Pollution is a concern for many companies and the responsibility to control it rests with the management of the companies.",
]

QOUTROS = [
 "Save and close the **1Health** document.",
 "Save and close the **2Marine** document.",
 "Save and close the **3Projects** spreadsheet.",
 "Save and close the **4Air** spreadsheet.",
 "Save and close the rpt5_6 report.\n\nSave and close the **5Save** database.",
 "ONE mark will be allocated for correctly closing tags and correctly nesting in both the files. (1)",
 "",
]

SCENARIO = ("Pollution is one of the biggest environmental concerns currently. Waste products may "
 "cause land, water and air pollution. A growing awareness of the negative impact of pollution "
 "encourages people to get involved in projects to stop pollution and clean up the environment.")

# chrome line patterns to strip from answer_text (full-line)
CHROME_LINE = re.compile(r'^(EXAMINATION|NUMBER|Total for QUESTION.*|TOTAL:?\s*\d+.*|Copyright reserved.*|Please turn over.*)\s*$', re.I)

def strip_answer_chrome(at):
    out = []
    for ln in (at or '').split('\n'):
        if CHROME_LINE.match(ln.strip()):
            continue
        out.append(ln)
    return '\n'.join(out).rstrip()

def strip_trailing_mark(qt):
    return re.sub(r'\s*\(\s*\d+\s*\)\s*$', '', (qt or '').rstrip()).rstrip()

def truncate_at(qt, phrase):
    idx = qt.find(phrase)
    return qt[:idx].rstrip() if idx != -1 else qt.rstrip()

with app.app_context():
    p = GeneratedPaper.query.get(PID)
    secs = json.loads(p.sections)
    s0 = secs[0]
    qids = s0['question_ids']
    def item(i): return db.session.get(QuestionBankItem, qids[i])

    # ---- explicit closer/divider truncation (before generic trailing-mark strip) ----
    qpost = dict(s0.get('qpost_texts') or {})

    # 1.10 (i9): closer -> qoutro
    item(9).question_text = truncate_at(item(9).question_text, 'Save and close')
    # 2.10 (i19)
    item(19).question_text = truncate_at(item(19).question_text, 'Save and close')
    # 3.7 (i26)
    item(26).question_text = truncate_at(item(26).question_text, 'Save and close')
    # 4.4 (i30): divider -> qpost
    item(30).question_text = truncate_at(item(30).question_text, 'Work in the Graph')
    qpost[qids[30]] = "Work in the **Graph** worksheet."
    # 4.6 (i32)
    item(32).question_text = truncate_at(item(32).question_text, 'Save and close')
    # 5.1.4 (i37): divider -> qpost
    item(37).question_text = truncate_at(item(37).question_text, 'Save and close')
    qpost[qids[37]] = "Save and close the **tbl5_1** table."
    # 5.6 (i42)
    item(42).question_text = truncate_at(item(42).question_text, 'Save and close')
    # 6.1.4 (i47): divider -> qpost
    item(47).question_text = truncate_at(item(47).question_text, 'Save and close')
    qpost[qids[47]] = "Save and close the **6_1Clean** file."
    # 7.2 (i52): divider -> qpost
    item(52).question_text = truncate_at(item(52).question_text, 'Work in the 7.3')
    qpost[qids[52]] = "Work in the **7.3** worksheet."
    # 7.3 (i53): divider -> qpost
    item(53).question_text = truncate_at(item(53).question_text, 'Save and close')
    qpost[qids[53]] = "Save and close the **7Date** spreadsheet."

    # ---- full rebuilds ----
    # 6.1 stem (i43): sentence + NOTE below image
    item(43).question_text = "Open the incomplete **6_1Clean** file in a web browser and also in a text/HTML editor."
    qpost[qids[43]] = ("NOTE:\n"
        "\u2022 Use the example on the previous page as a guide when answering this question.\n"
        "\u2022 Question numbers appear as comments in the coding to indicate where you should insert the answer(s). DO NOT delete these comments.")
    # 6.2 (i48): body only; ONE-mark line -> qoutro; marks 15 -> 6
    item(48).question_text = ("Open the incomplete **6_2Pollute** web file in a web browser and also in a text/HTML editor.\n\n"
        "Complete the web page to look exactly like the example below.\n\n"
        "Save and close the **6_2Pollute** file.")
    item(48).marks = 6
    # 7.1.2 (i51): mail-merge body; tail -> qpost
    item(51).question_text = ("Prepare the mail merge as follows:\n\n"
        "\u2022 Link the **7Letter** document with the data source, the **7Company** spreadsheet.\n"
        "\u2022 Select only the companies that have a 'high' and 'very high' level.\n"
        "\u2022 Replace the text '<Company>' and '<Level>' to display the 'company' and 'level' from the 7Company spreadsheet.\n\n"
        "Save the 7Letter document, but do NOT close it.\n\n"
        "Complete the mail merge and save the merged document as 7Merge.")
    qpost[qids[51]] = ("Close the 7Letter document.\n\n"
        "The Pollution Control Board will give certificates to companies with a consistently low level of pollution. "
        "The certificates will be presented in the month corresponding with the monitor date.\n\n"
        "Open the **7Date** spreadsheet.\n\nWork in the **Monthly** worksheet.")
    # 7.4 (i54): body only (strip input-mask/tag-sheet garbage)
    item(54).question_text = "Extract the image file from the password-protected folder called **7Picture** using the password 'November'."

    # ---- generic trailing-(N) strip on ALL question_texts ----
    for i in range(len(qids)):
        it = item(i)
        it.question_text = strip_trailing_mark(it.question_text)
        it.answer_text = strip_answer_chrome(it.answer_text)

    # ---- section-level: scenario, intros, outros, qpost, titles ----
    s0['scenario'] = SCENARIO
    s0['qinstructions'] = QINTRO
    s0['qoutros'] = QOUTROS
    s0['qtitles'] = ['WORD PROCESSING','WORD PROCESSING','SPREADSHEET','SPREADSHEET','DATABASE','WEB DESIGN (HTML)','GENERAL']
    s0['qpost_texts'] = qpost

    p.sections = json.dumps(secs, ensure_ascii=False)
    db.session.commit()
    print('OK. 6.2 marks=', item(48).marks)
    # verify totals
    splits = s0['splits'] + [len(qids)]
    for qi in range(7):
        tot = sum(item(k).marks or 0 for k in range(splits[qi], splits[qi+1]))
        print(f'Q{qi+1} sum =', tot)
