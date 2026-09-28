import json, re
from app import app, db, GeneratedPaper, QuestionBankItem

P = 'b1721187-9537-4d66-845d-263a8d3c3d0b'
IMG = 'uploads/cat_p2_mj24/'

def strip_footer(text):
    """Remove trailing DBE footers: [NN], TOTAL SECTION X: NN, GRAND TOTAL: NN, stray year."""
    t = text
    # cut everything from the first standalone [NN] mark-total onward
    t = re.split(r'\n\s*\[\d{1,3}\]', t)[0]
    # also strip any lingering TOTAL/GRAND lines
    t = re.sub(r'\n\s*TOTAL SECTION [A-C]:\s*\d+.*$', '', t, flags=re.S)
    t = re.sub(r'\n\s*GRAND TOTAL:\s*\d+.*$', '', t, flags=re.S)
    return t.rstrip()

with app.app_context():
    p = GeneratedPaper.query.get(P)
    # --- Cover fields ---
    p.cover_subtitle   = 'Confidential'
    p.sub_header       = 'SC/NSC Confidential'
    p.cover_extra_note = 'This question paper consists of 16 pages.'

    secs = json.loads(p.sections)
    secA, secB, secC = secs[0], secs[1], secs[2]

    def item(sec, idx):
        qid = sec['question_ids'][idx]
        return QuestionBankItem.query.get(qid), qid

    # ===== SECTION A =====
    # idx9 (Q1.10) strip footer "(1)\n[10]\n2024"
    q, _ = item(secA, 9)
    q.question_text = strip_footer(q.question_text)
    # idx19 (Q2.10) marks 10 -> 1
    q, _ = item(secA, 19); q.marks = 1
    # idx24 (Q3.5) strip footer
    q, _ = item(secA, 24)
    q.question_text = strip_footer(q.question_text)

    # ===== SECTION B =====
    # Q4.10 idx15: 25->2
    q, _ = item(secB, 15); q.marks = 2
    # Q5.7 idx24: 15->2
    q, _ = item(secB, 24); q.marks = 2
    # Q6.3 stem idx27: attach report image
    q, _ = item(secB, 27)
    q.image_path = IMG + 'q6_3_report.png'
    q.image_width = 82
    q.tags = (q.tags + ',noborder').strip(',') if q.tags else 'noborder'
    # Q6.5 idx31: 10->2
    q, _ = item(secB, 31); q.marks = 2
    # Q7.4.2 idx39: 10->2
    q, _ = item(secB, 39); q.marks = 2
    # Q8.2 idx45: strip HTML CODE / WEB PAGE labels, attach combined image
    q, qid45 = item(secB, 45)
    qt = q.question_text
    qt = re.sub(r'\n\s*HTML CODE:\s*', '', qt)
    qt = re.sub(r'\n\s*WEB PAGE:\s*', '', qt)
    q.question_text = qt.rstrip()
    q.image_path = IMG + 'q8_2_combined.png'
    q.image_width = 62
    q.tags = (q.tags + ',noborder').strip(',') if q.tags else 'noborder'
    # Q8.3.2 idx48: 1->2
    q, _ = item(secB, 48); q.marks = 2
    # Q8.3.3 idx49: marks 1->3, strip Query labels + Explain + footer, attach combined image, post_text
    q, qid49 = item(secB, 49)
    q.marks = 3
    q.question_text = 'Study the screenshot of two different queries.'
    q.image_path = IMG + 'q8_3_combined.png'
    q.image_width = 60
    q.tags = (q.tags + ',noborder').strip(',') if q.tags else 'noborder'
    # post_text for the trailing Explain instruction
    qpost = secB.get('qpost_texts') or {}
    qpost[qid49] = 'Explain how the result of Query 2 will differ from Query 1 when executed.'
    secB['qpost_texts'] = qpost

    # ===== SECTION C =====
    # Q9.4.2 idx18: 25->2
    q, _ = item(secC, 18); q.marks = 2
    # Q10.5.2 idx35: 1->3, strip footer
    q, _ = item(secC, 35)
    q.marks = 3
    q.question_text = strip_footer(q.question_text)
    # Q9 / Q10 scenario intros + Q9 robot icon
    secC['qinstructions'] = [
        'The school has begun a Robotics Club. The club will host competitions, different speakers and exhibitions on robotics. You are requested to assist the teacher with admin and purchases for the Robotics Club.',
        'You have been invited to join the Historical Society.',
    ]
    secC['qimages'] = [IMG + 'q9_robot_icon.png', '']

    p.sections = json.dumps(secs, ensure_ascii=False)
    db.session.commit()
    print('cover_subtitle =', p.cover_subtitle)
    print('committed OK')
