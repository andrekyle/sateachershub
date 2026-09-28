import json
from app import app, db, QuestionBankItem, GeneratedPaper

PID = "4cc75484-e298-41f3-bd08-e3d1db11ee71"

with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = json.loads(p.sections)
    sec = secs[0]
    qids = sec['question_ids']

    # ---- Edit 1: Q6 group intro (qinstructions[5]) ----
    # Make the first NOTE bullet bold (matches PDF) and split the
    # "You are required to modify web pages..." sentence into its own
    # paragraph (blank line) so it is no longer merged into bullet 3.
    sec['qinstructions'][5] = (
        "NOTE:\n"
        "\u2022 **You may NOT use a word processing program such as Word to "
        "answer the HTML questions.**\n"
        "\u2022 An HTML tag sheet has been attached for reference.\n"
        "\u2022 All files needed to complete this question can be found in the "
        "examination folder.\n"
        "\n"
        "You are required to modify web pages about a new interactive virtual "
        "experience for tourists visiting Cape Town."
    )

    # ---- Edit 2: item 43 (6.1 stem) question_text ----
    # Remove the second NOTE block; keep only the 6.1 stem + example line.
    r43 = db.session.get(QuestionBankItem, qids[43])
    r43.question_text = (
        "Open the incomplete 6_1Interactive file in a web browser and also in a\n"
        "text/HTML editor (NOT a word processing program such as Word).\n"
        "\n"
        "Your final web page should look like the example below."
    )

    # ---- Edit 3: qpost_texts[item43] = second NOTE block (after figure) ----
    sec.setdefault('qpost_texts', {})
    sec['qpost_texts'][qids[43]] = (
        "NOTE:\n"
        "\u2022 Use the example on the previous page as a guide when answering "
        "this question.\n"
        "\u2022 Question numbers appear as comments in the coding to indicate "
        "where you should insert the answer(s). Do NOT delete these comments."
    )

    # ---- Edit 4: item 51 (6.1.8) strip baked-in trailing "(1)" ----
    r51 = db.session.get(QuestionBankItem, qids[51])
    r51.question_text = (
        "Modify the code so that the link will direct the user to the web address\n"
        "given in the data."
    )

    # ---- Edit 5: item 52 (6.2) question_text -> remove NOTE line ----
    r52 = db.session.get(QuestionBankItem, qids[52])
    r52.question_text = (
        "Open the incomplete 6_2Big6 file in a web browser and also in a text/HTML\n"
        "editor (NOT a word processing program such as Word).\n"
        "\n"
        "Modify the HTML code so that your final web page displays like the example\n"
        "below."
    )

    # ---- Edit 6: qpost_texts[item52] = NOTE (cells=50) + Save and close ----
    # The "(5)" lives here so it renders on the NOTE line after the figure
    # (matches PDF); the item's own marks div is suppressed but marks=5 still
    # counts toward the [15] total.
    sec['qpost_texts'][qids[52]] = (
        "NOTE: The size of the spacing between the cells is 50. (5)\n"
        "\n"
        "Save and close the **6_2Big6** file."
    )

    p.sections = json.dumps(secs, ensure_ascii=False)
    db.session.add(p)
    db.session.commit()
    print("committed Q6 edits")
