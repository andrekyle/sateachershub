"""Re-extract MATCHING questions properly using pdfplumber word coordinates.
Column A ends ~x=315; option letters start at ~x=320; terms ~x=355.
"""
from __future__ import annotations
import os, re
import pdfplumber
from app import app, db, QuestionBankItem
from extract_all_questions import parse_paper_label

UPLOADS = os.path.join('static', 'uploads')
INTRO = 'Match the following description with the correct term from the list:'


def _group_lines(words, ytol=4):
    lines = []
    cur = []
    last_top = None
    for w in sorted(words, key=lambda w: (round(w['top']), w['x0'])):
        if last_top is None or abs(w['top'] - last_top) < ytol:
            cur.append(w)
            if last_top is None:
                last_top = w['top']
        else:
            lines.append(cur)
            cur = [w]
            last_top = w['top']
    if cur:
        lines.append(cur)
    return lines


def _detect_split_x(words):
    """Find the option-letter column by clustering single-cap-letter word x0 positions.
    In DBE matching tables the letters (A,B,C,...) all sit at the same x.
    Restrict to words AFTER the COLUMN A/B header row and BEFORE the totals line."""
    # Find header y
    header_y = None
    for i, w in enumerate(words):
        if w['text'].upper() == 'COLUMN' and i + 1 < len(words):
            nxt = words[i+1]
            if nxt['text'].upper() == 'B' and abs(nxt['top'] - w['top']) < 3:
                # Only the table-header row (not the intro). Header B is rightmost.
                if header_y is None or nxt['top'] > header_y:
                    header_y = w['top']
    if header_y is None:
        return None
    # Collect single uppercase letters that appear after header_y
    from collections import Counter
    letter_re = re.compile(r'^[A-Z]$')
    xs = []
    for w in words:
        if w['top'] <= header_y + 5:
            continue
        if letter_re.match(w['text']):
            xs.append(round(w['x0']))
    if not xs:
        return None
    most_common_x, count = Counter(xs).most_common(1)[0]
    if count < 3:
        return None
    return most_common_x - 5


def _extract_one_table(page):
    words = page.extract_words()
    if not words:
        return {}, {}
    split_x = _detect_split_x(words)
    if split_x is None:
        return {}, {}

    lines = _group_lines(words)
    sub_re = re.compile(r'^\d+\.\d+$')
    letter_re = re.compile(r'^[A-Z]$')

    descs = {}
    options = {}
    current_sub = None
    last_letter = None
    in_body = False

    for line in lines:
        left_words = [w for w in line if w['x0'] < split_x]
        right_words = [w for w in line if w['x0'] >= split_x]

        if not in_body:
            if left_words and sub_re.match(left_words[0]['text']):
                in_body = True
            else:
                continue

        line_text = ' '.join(w['text'] for w in line)
        if 'Copyright' in line_text or 'turn-over' in line_text or 'turn over' in line_text:
            break
        if re.search(r'\(\d+\s*x\s*1\)\s*\[\d+\]', line_text):
            continue

        if left_words:
            txt = ' '.join(w['text'] for w in left_words).strip()
            m_sub = re.match(r'^(\d+\.\d+)\s+(.*)$', txt)
            if m_sub:
                current_sub = m_sub.group(1)
                descs[current_sub] = m_sub.group(2).strip()
            elif current_sub:
                add = txt.strip()
                if add:
                    descs[current_sub] = (descs[current_sub] + ' ' + add).strip()

        if right_words:
            first = right_words[0]
            if letter_re.match(first['text']):
                letter = first['text']
                term = ' '.join(w['text'] for w in right_words[1:]).strip()
                options[letter] = term
                last_letter = letter
            elif last_letter:
                add = ' '.join(w['text'] for w in right_words).strip()
                if add:
                    options[last_letter] = (options[last_letter] + ' ' + add).strip()

    return descs, options


def extract_paper(pdf_path):
    info = parse_paper_label(pdf_path)
    if not info or info['is_memo']:
        return []
    out = []
    with pdfplumber.open(pdf_path) as pdf:
        merged_by_parent = {}
        for page in pdf.pages:
            text = page.extract_text() or ''
            if 'COLUMN A' not in text.upper() or 'COLUMN B' not in text.upper():
                continue
            descs, opts = _extract_one_table(page)
            if not descs or not opts:
                continue
            parent = next(iter(descs)).split('.')[0]
            if parent not in merged_by_parent:
                merged_by_parent[parent] = (dict(descs), dict(opts))
            else:
                d, o = merged_by_parent[parent]
                d.update(descs); o.update(opts)
                merged_by_parent[parent] = (d, o)
        for parent, (d, o) in merged_by_parent.items():
            out.append((parent, d, o))
    return out


def main():
    with app.app_context():
        updates = 0
        for name in sorted(os.listdir(UPLOADS)):
            path = os.path.join(UPLOADS, name)
            if not os.path.isfile(path) or not name.lower().endswith('.pdf'):
                continue
            info = parse_paper_label(name)
            if not info or info['is_memo']:
                continue
            try:
                runs = extract_paper(path)
            except Exception as e:
                print(f'SKIP {name}: {e}')
                continue
            if not runs:
                continue
            for parent, descs, opts in runs:
                opt_letters = sorted(opts.keys())
                opts_lines = [f'{L}) {opts[L]}' for L in opt_letters if opts.get(L, '').strip()]
                opts_tail = 'Options:\n' + '\n'.join(opts_lines)
                sub_keys = sorted(descs.keys(), key=lambda s: [int(x) for x in s.split('.')])
                first_sub = sub_keys[0] if sub_keys else None
                print(f'{info["label"]} Q{parent}: {len(sub_keys)} descriptions, {len(opts_lines)} options')
                for sub_no in sub_keys:
                    item = (QuestionBankItem.query
                            .filter(QuestionBankItem.subtopic == f'{info["label"]} - Q{sub_no}')
                            .first())
                    if not item:
                        continue
                    desc = descs[sub_no].strip()
                    body = f'{INTRO}\n{desc}'
                    if sub_no == first_sub:
                        body = body + '\n\n' + opts_tail
                    item.question_text = body
                    item.question_type = 'matching'
                    item.marks = 1
                    tags = [t.strip() for t in (item.tags or '').split(',') if t.strip()]
                    for t_ in ('short_answer', 'mcq', 'list', 'explain', 'true_false'):
                        if t_ in tags:
                            tags.remove(t_)
                    if 'matching' not in tags:
                        tags.append('matching')
                    item.tags = ','.join(tags)
                    updates += 1
        db.session.commit()
        print(f'\nUpdated {updates} matching items.')


if __name__ == '__main__':
    main()
