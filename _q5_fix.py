# -*- coding: utf-8 -*-
"""Fix QUESTION 5 of CAT P1 May/June 2023 to match the PDF verbatim.
Touches ONLY Q5 items / arrays / qpost_texts / qinstructions[4]."""
from app import app, db, GeneratedPaper, QuestionBankItem
import json, uuid

PID = '4cc75484-e298-41f3-bd08-e3d1db11ee71'

# Q5 item qids (current order, indices 32-41)
IDNO   = '1b785dea'  # idx32 -> becomes 5.1.1
SAFARI = '946f711e'  # idx33 -> 5.1.2
DATE   = '763c5c0a'  # idx34 -> 5.1.3
PIC    = '0a253698'  # idx35 -> 5.1.4
GRID   = 'ecea34a8'  # idx36 -> 5.1.5
Q52    = '56042ce5'  # idx37 -> 5.2
Q53    = 'b4581348'  # idx38 -> 5.3
Q54    = '6b3b3472'  # idx39 -> 5.4
Q55    = 'bce7de46'  # idx40 -> 5.5
Q56    = '963d1deb'  # idx41 -> 5.6

def full(qids, pfx):
    for q in qids:
        if q.startswith(pfx):
            return q
    raise KeyError(pfx)

with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = json.loads(p.sections)
    sec = secs[0]
    qids = sec['question_ids']

    fIDNO=full(qids,IDNO); fSAFARI=full(qids,SAFARI); fDATE=full(qids,DATE)
    fPIC=full(qids,PIC); fGRID=full(qids,GRID); fQ52=full(qids,Q52)
    fQ53=full(qids,Q53); fQ54=full(qids,Q54); fQ55=full(qids,Q55); fQ56=full(qids,Q56)

    idno_item = db.session.get(QuestionBankItem, fIDNO)

    # --- 1. Create the missing 5.1 STEM item ("Open the tbl5_1 table...") ---
    stem_id = str(uuid.uuid4())
    stem = QuestionBankItem(
        id=stem_id,
        owner_id=idno_item.owner_id,
        grade=idno_item.grade,
        subject=idno_item.subject,
        topic=idno_item.topic,
        question_type='database',
        question_text='Open the **tbl5_1** table in Design View.',
        answer_text='',
        marks=0,
        image_path='',
        image_width=0,
        tags=idno_item.tags,
    )
    db.session.add(stem)

    # --- 2. Insert stem at index 32 (start of Q5, before IDNo) ---
    insert_at = qids.index(fIDNO)   # == 32
    assert insert_at == 32, insert_at
    qids.insert(insert_at, stem_id)

    # --- 3. Recompute splits (>=32 shift +1; the Q5 start stays at 32) ---
    old_splits = sec.get('splits') or []
    new_splits = [(s + 1 if s > insert_at else s) for s in old_splits]
    sec['splits'] = new_splits

    # --- 4. Recompute subitems: shift >=32 by +1, then add IDNo (now 5.1.1) ---
    old_sub = sec.get('subitems') or []
    new_sub = sorted({(s + 1 if s >= insert_at else s) for s in old_sub} | {qids.index(fIDNO)})
    sec['subitems'] = new_sub

    # --- 5. Update each Q5 item's question_text + marks (verbatim) ---
    edits = {
        fIDNO: dict(marks=2, text=(
            "Modify the properties of the <i>IDNo</i> field as follows:\n\n"
            "\u2022  Set an appropriate field size.\n"
            "\u2022  Set the field properties so that records are uniquely identified.")),
        fSAFARI: dict(marks=2, text=(
            "Add 'Safari' as a value list option to the <i>Experience</i> field.\n\n"
            "Change the lookup properties so that tourists can choose more than one "
            "option as an experience type.")),
        fDATE: dict(marks=4, text=(
            "Change the properties of the <i>Date</i> field to only accept dates from the "
            "beginning of July 2023 to the end of August 2024. Display an appropriate "
            "message if the date entered is incorrect.")),
        fPIC: dict(marks=3, text=(
            "Change the <i>Picture</i> field as follows:\n\n"
            "\u2022  Set an appropriate data type so that a tourist can upload their ID photo.\n"
            "\u2022  Move the field to appear below the <i>IDNo</i> field.\n"
            "\u2022  Change the properties so that the heading 'IDPhoto' will display in "
            "Datasheet View, instead of the heading 'Picture'.\n\n"
            "NOTE:  Do not rename the <i>Picture</i> field.")),
        fGRID: dict(marks=2, text=(
            "Change the colour of the gridlines to black AND set the option to display "
            "only the horizontal gridlines.")),
        fQ52: dict(marks=4, text=(
            "Open the **frm5_2** form, based on the **tblActivities** table, in Design View, "
            "and modify the form as follows:\n\n"
            "\u2022  Change the 'Display when' property of the image so that the image will "
            "only display on the screen.\n"
            "\u2022  Apply conditional formatting to the <i>Duration</i> field to compare "
            "records in a yellow bar colour. Display the bar only.")),
        fQ53: dict(marks=4, text=(
            "Open the **qry5_3** query, based on the **tblActivities** table, in Design View.\n\n"
            "Display all the tours where morning activities include game drives with "
            "transport OR shark cage diving.\n\n"
            "Save and close the **qry5_3** query.")),
        fQ54: dict(marks=5, text=(
            "Create a query named **qry5_4** based on the **tblActivities** table as follows:")),
        fQ55: dict(marks=4, text=(
            "Open the **qry5_5** query, based on the **tblActivities** table, in Design View.\n\n"
            "Insert a calculated field <i>Hours</i> to determine how many hours each tour "
            "will take, based on the <i>Duration</i> field. Display only the tours that "
            "will take a day or longer.\n\n"
            "HINT:  Refer to field descriptions in the Design View of the table.\n\n"
            "Save and close the **qry5_5** query.")),
        fQ56: dict(marks=5, text=(
            "Open the report called **rpt5_6** based on the **tblActivities** table.\n\n"
            "Modify the report as shown below.")),
    }
    for qid, e in edits.items():
        it = db.session.get(QuestionBankItem, qid)
        it.question_text = e['text']
        it.marks = e['marks']

    # --- 6. qpost_texts (keyed by qid) ---
    qpt = sec.setdefault('qpost_texts', {})
    qpt[fPIC]  = "Switch to __Datasheet View__."
    qpt[fGRID] = "Save and close the **tbl5_1** table."
    qpt[fQ52]  = "Save and close the **frm5_2** form. (4)"
    qpt[fQ54]  = ("NOTE:\n"
                  "\u2022  The records in the <i>Experience</i> field\n"
                  "\u2022  The last row total is calculated in Datasheet View\n\n"
                  "Save and close the **qry5_4** query. (5)")
    qpt[fQ56]  = ("NOTE:\n"
                  "\u2022  Grouping does not split over pages.\n"
                  "\u2022  Ignore any textbox borders. (5)\n\n"
                  "Save and close the **rpt5_6** report.")

    # --- 7. Intro (qinstructions[4]) — separate paragraphs ---
    qi = sec.setdefault('qinstructions', [])
    while len(qi) <= 4:
        qi.append('')
    qi[4] = ("The **5Tours** database stores information regarding bookings for tours and "
             "activities in and around Cape Town.\n\n"
             "NOTE: Accept/Approve any messages if they appear.\n\n"
             "Open the **5Tours** database.")

    # qoutros[4] stays: "Save and close the **5Tours** database."

    p.sections = json.dumps(secs, ensure_ascii=False)
    db.session.commit()
    print('OK committed. new len qids', len(qids))
    print('splits', sec['splits'])
    print('subitems', sec['subitems'])
    print('stem_id', stem_id)
