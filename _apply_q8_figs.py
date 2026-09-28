"""Attach the three Q8 figures and restructure body/post_text for P2 2025.

- 8.4 (def41448): linked-object figure; question moved to post_text.
- 8.6 (62956d2e): VLOOKUP Function Arguments figure; question moved to post_text.
- 8.7 (60dfc377): combined HTML code | Web page figure; strip text tail.
"""
import json
from app import app, db, GeneratedPaper, QuestionBankItem

PAPER_ID = '18cc87c0-2ee3-43fe-b74c-89aa56a3ad71'

Q84 = 'def41448-70a8-4af7-8993-363d0fa6f960'
Q86 = '62956d2e-a2a9-4ad0-ad89-f7910bc52a17'
Q87 = '60dfc377-29f7-4e3d-99e8-bee8ce901402'

with app.app_context():
    # --- 8.4 linked object ---
    i84 = db.session.get(QuestionBankItem, Q84)
    i84.question_text = 'The linked object below was created in a word processing document.'
    i84.image_path = 'uploads/paper_images/p2_2025/q8_4_linked_object.png'
    i84.image_width = 38
    i84.image_offset = 0

    # --- 8.6 VLOOKUP dialog ---
    i86 = db.session.get(QuestionBankItem, Q86)
    i86.question_text = 'In the VLOOKUP function, the argument Range_lookup can accept True or False.'
    i86.image_path = 'uploads/paper_images/p2_2025/q8_6_vlookup.png'
    i86.image_width = 58
    i86.image_offset = 0

    # --- 8.7 HTML/Web table ---
    i87 = db.session.get(QuestionBankItem, Q87)
    i87.question_text = ('Study the incomplete HTML code on the left and the '
                         'corresponding web page on the right in the example below.')
    i87.image_path = 'uploads/paper_images/p2_2025/q8_7_html_web.png'
    i87.image_width = 78
    i87.image_offset = 0

    # --- post_text for 8.4 and 8.6 (renders below the figure) ---
    paper = db.session.get(GeneratedPaper, PAPER_ID)
    secs = json.loads(paper.sections)
    secB = secs[1]
    qpost = secB.get('qpost_texts')
    if not isinstance(qpost, dict):
        qpost = {}
    qpost[Q84] = 'Give TWO reasons why you would use linked objects.'
    qpost[Q86] = 'Explain when True and False would be used in a Range_lookup.'
    secB['qpost_texts'] = qpost
    paper.sections = json.dumps(secs)

    db.session.commit()
    print('Applied Q8 figures + post_text.')
    for qid in (Q84, Q86, Q87):
        it = db.session.get(QuestionBankItem, qid)
        print('  %s -> img=%r w=%s' % (qid[:8], it.image_path, it.image_width))
    print('  qpost_texts keys:', list(secB['qpost_texts'].keys()))
