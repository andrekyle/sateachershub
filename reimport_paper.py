"""In-place re-import of a generated paper from its source PDF.

Usage:
    python reimport_paper.py <paper_id> <pdf_path>

Effect:
    * Re-runs `_parse_past_paper_pdf` + `_extract_past_paper_cover`
      on the given PDF.
    * Deletes the QuestionBankItems currently referenced by the paper.
    * Wipes the paper's static/uploads/paper_images/<id>/ directory.
    * Rebuilds sections + question items using the same logic as the
      teacher_paper_use route.
    * Re-runs extract_paper_images on the result.

Paper id, owner, title, exam_date, share_scope are preserved.
"""
import json
import os
import shutil
import sys

from app import (app, db, GeneratedPaper, QuestionBankItem,
                 _parse_past_paper_pdf, _extract_past_paper_cover)
from extract_paper_images import extract as extract_paper_images


def reimport(paper_id, pdf_path):
    with app.app_context():
        paper = GeneratedPaper.query.get(paper_id)
        if not paper:
            raise SystemExit(f'No paper {paper_id!r}')
        if not os.path.exists(pdf_path):
            raise SystemExit(f'PDF not found: {pdf_path}')

        # ---- Wipe old images directory ----
        img_dir = os.path.join('static', 'uploads', 'paper_images', paper_id)
        if os.path.isdir(img_dir):
            shutil.rmtree(img_dir)
            print(f'Removed old images: {img_dir}')

        # ---- Collect old question ids and delete them ----
        old_qids = []
        try:
            old_sections = json.loads(paper.sections or '[]')
            for s in old_sections:
                old_qids.extend(s.get('question_ids', []))
        except Exception:
            old_sections = []
        if old_qids:
            QuestionBankItem.query.filter(
                QuestionBankItem.id.in_(old_qids)).delete(
                synchronize_session=False)
            print(f'Deleted {len(old_qids)} old question item(s)')

        # ---- Re-parse the PDF ----
        parsed_sections = _parse_past_paper_pdf(pdf_path, strict=True)
        cover_meta = _extract_past_paper_cover(pdf_path) or {}

        # ---- Update paper-level fields from the cover ----
        paper.duration_minutes = cover_meta.get('duration_minutes') or paper.duration_minutes or 180
        paper.total_marks = cover_meta.get('total_marks') or paper.total_marks or 150
        paper.instructions = cover_meta.get('instructions') or ''
        paper.data_files = cover_meta.get('data_files') or ''
        if cover_meta.get('paper_number'):
            paper.paper_number = cover_meta['paper_number']
        paper.cover_extra_note = ''

        # ---- Rebuild sections + QuestionBankItems ----
        sections_payload = []
        total_marks = 0
        for sec in parsed_sections:
            qids = []
            for q in sec.get('questions', []):
                qtext = (q.get('text') or '')
                if not qtext.strip():
                    continue
                qmarks = int(q.get('marks') or 0)
                total_marks += qmarks
                tags = ['imported', 'past_paper', 'raw_pdf', 'reimport']
                item = QuestionBankItem(
                    owner_id=paper.owner_id,
                    grade=paper.grade or 12,
                    subject=paper.subject,
                    topic=sec.get('title') or '',
                    subtopic=q.get('number') or '',
                    difficulty='medium',
                    question_type='structured',
                    question_text=qtext,
                    answer_text='',
                    marks=qmarks,
                    tags=','.join(tags),
                    share_scope='private',
                )
                db.session.add(item)
                db.session.flush()
                qids.append(item.id)
            if qids:
                sections_payload.append({
                    'title': sec.get('title') or 'Section',
                    'instructions': sec.get('instructions') or '',
                    'question_ids': qids,
                    'splits': list(range(len(qids))),
                })

        # ---- Scenario block (between cover instructions & QUESTION 1) ----
        if sections_payload:
            try:
                import pdfplumber as _pp
                import re as _re
                with _pp.open(pdf_path) as _pdf:
                    for _pg in _pdf.pages[:8]:
                        _t = _pg.extract_text() or ''
                        m = _re.search(
                            r'(?is)\bSCENARIO\b\s*\n(.*?)(?=\n\s*(?:QUESTION\s+\d|SECTION\s+[A-Z]\b))',
                            _t)
                        if m:
                            sections_payload[0]['scenario'] = _re.sub(
                                r'\s+', ' ', m.group(1)).strip()
                            break
            except Exception:
                pass

        paper.sections = json.dumps(sections_payload)
        if not cover_meta.get('total_marks') and total_marks > 0:
            paper.total_marks = total_marks
        db.session.commit()
        print(f'Rebuilt {sum(len(s["question_ids"]) for s in sections_payload)} '
              f'question(s) across {len(sections_payload)} section(s).')

        # ---- Re-extract figure images ----
        qmap = {}
        qn = 0
        for s in sections_payload:
            for qid in s['question_ids']:
                qn += 1
                qmap[qn] = qid
        saved, skipped = extract_paper_images(pdf_path, paper_id, qmap)
        print(f'Saved {len(saved)} image(s); skipped {len(skipped)}.')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    reimport(sys.argv[1], sys.argv[2])
