"""Detect MATCHING/MCQ/TRUE-FALSE sections per paper using the parent
question's body (where the Column A/Column B / 'choose the letter' intro
lives) and re-tag every sub-item in that question with the correct type.
"""
from __future__ import annotations
import os, re
from app import app, db, QuestionBankItem
from extract_all_questions import (
    extract_pdf_text, clean_text, split_into_sections,
    split_questions_in_section, parse_paper_label,
)

UPLOADS = os.path.join('static', 'uploads')

def detect_overrides():
    out = {}
    for name in os.listdir(UPLOADS):
        path = os.path.join(UPLOADS, name)
        if not os.path.isfile(path) or not name.lower().endswith('.pdf'):
            continue
        info = parse_paper_label(name)
        if not info or info['is_memo']:
            continue
        try:
            raw = extract_pdf_text(path)
        except Exception as e:
            print(f'SKIP {name}: {e}')
            continue
        c = clean_text(raw)
        st = {}
        for letter, lines in split_into_sections(c):
            for parent_no, hdr, body in split_questions_in_section(lines):
                full = ((hdr or '') + '\n' + '\n'.join(body)).lower()
                if re.search(r'column\s*a.*column\s*b', full, re.S):
                    st[parent_no] = 'matching'
                elif re.search(r'various options are given', full):
                    st[parent_no] = 'mcq'
                elif re.search(r'true\s+or\s+false', full):
                    st[parent_no] = 'true_false'
        if st:
            out[info['label']] = st
    return out


def main():
    with app.app_context():
        overrides = detect_overrides()
        print('Overrides found:')
        for lbl in sorted(overrides):
            print(f'  {lbl}: {overrides[lbl]}')

        m = q = tf = 0
        items = QuestionBankItem.query.filter(
            QuestionBankItem.tags.like('%auto_import_v1%')
        ).all()
        for it in items:
            sub = (it.subtopic or '')
            if ' - Q' not in sub:
                continue
            label, qn = sub.rsplit(' - Q', 1)
            label = label.strip(); qn = qn.strip()
            parent = qn.split('.')[0]
            forced = overrides.get(label, {}).get(parent)
            if not forced or it.question_type == forced:
                continue
            old = it.question_type
            it.question_type = forced
            # marks: matching items are 1 mark each
            if forced in ('matching', 'mcq', 'true_false') and (it.marks or 0) > 3:
                it.marks = 1
            tags = [t.strip() for t in (it.tags or '').split(',') if t.strip()]
            if old in tags:
                tags.remove(old)
            if forced not in tags:
                tags.append(forced)
            it.tags = ','.join(tags)
            if forced == 'matching': m += 1
            elif forced == 'mcq': q += 1
            elif forced == 'true_false': tf += 1
        db.session.commit()
        print(f'Re-tagged: matching={m}, mcq={q}, true_false={tf}')


if __name__ == '__main__':
    main()
