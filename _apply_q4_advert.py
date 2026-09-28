"""Attach the StellarX advertisement image to Section B idx0 (4.1) and trim its text."""
import json
from app import app, db, GeneratedPaper, QuestionBankItem

PID = '18cc87c0-2ee3-43fe-b74c-89aa56a3ad71'
with app.app_context():
    p = db.session.get(GeneratedPaper, PID)
    secs = p.sections if isinstance(p.sections, list) else json.loads(p.sections)
    qids = secs[1]['question_ids']
    it = db.session.get(QuestionBankItem, qids[0])
    it.question_text = 'Study the advertisement below and answer the questions that follow.'
    it.image_path = 'uploads/paper_images/p2_2025/q4_1_advert.png'
    it.image_width = 78
    it.image_offset = 0
    db.session.commit()
    print('updated idx0:')
    print('  question_text:', repr(it.question_text))
    print('  image_path:', it.image_path, '| width:', it.image_width)
