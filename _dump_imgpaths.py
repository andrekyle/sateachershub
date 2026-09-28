"""Print image_path/image_width for items that already have images (Q1.5, Q1.10)."""
import json
from app import app, db, GeneratedPaper, QuestionBankItem

PAPER_ID = '18cc87c0-2ee3-43fe-b74c-89aa56a3ad71'

with app.app_context():
    paper = db.session.get(GeneratedPaper, PAPER_ID)
    secs = json.loads(paper.sections)
    for sec in secs:
        for qid in sec.get('question_ids', []):
            item = db.session.get(QuestionBankItem, qid)
            if item and item.image_path:
                print('id=%s' % qid)
                print('   image_path=%r' % item.image_path)
                print('   image_width=%r image_offset=%r' % (item.image_width, getattr(item, 'image_offset', None)))
                print('   text=%r' % (item.question_text or '')[:80])
                print('-' * 40)
