# Build editable Business Studies May-June 2023 papers (P1 + P2) from the
# uploaded DBE PDFs: extract questions + memo answers into the question bank
# and populate the GeneratedPaper sections JSON (same shape the CAT papers use).
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime

DB = 'instance/brandcartel.db' if os.path.exists('instance/brandcartel.db') else 'brandcartel.db'

NOISE = [
    re.compile(r'^Copyright reserved.*$', re.I),
    re.compile(r'^Business Studies/P\d.*DBE/2023.*$', re.I),
    re.compile(r'^SC/NSC.*$', re.I),
    re.compile(r'^Please turn over.*$', re.I),
]


def clean(text):
    # Normalise Wingdings PUA glyphs from PDF extraction: \uf02d is the
    # option-range dash in "(A–D)".
    text = text.replace('\uf02d', '\u2013').replace('\uf0b7', '\u2022')
    out = []
    for ln in text.splitlines():
        s = ln.rstrip()
        if any(p.match(s.strip()) for p in NOISE):
            continue
        out.append(s)
    return '\n'.join(out)


def block(text, start_pat, end_pats):
    """Text from start_pat match to the earliest end_pat match after it."""
    ms = re.search(start_pat, text, re.M)
    if not ms:
        return ''
    rest = text[ms.start():]
    cut = len(rest)
    for ep in end_pats:
        me = re.search(ep, rest[1:], re.M)
        if me and me.start() + 1 < cut:
            cut = me.start() + 1
    return rest[:cut].strip()


def sum_marks(text):
    """Sum standalone trailing (N) mark tokens; skips the (5 x 2) part."""
    return sum(int(m) for m in re.findall(r'\((\d{1,2})\)\s*$', text, re.M))


SUBQ_RE = re.compile(r'^\d+\.\d+\.\d+\s')
OPTION_RE = re.compile(r'^([A-D])\s+(\S.*)$')
BULLET_RE = re.compile(r'^\s*(?:[\u2022\uf02d\u25cf\-]|o\s)\s*')
CAPS_RE = re.compile(r"^[A-Z0-9 ()&/'\u2019.,:-]{10,}$")
PARA_START = ('Read the scenario', 'Use the table', 'NOTE:', 'Write an essay',
              'COLUMN A')


def reflow(text, matching=False):
    """Re-shape PDF-extracted text so the paper renderer keeps the layout:
    blank lines between logical paragraphs, options as `A  body` lines,
    bullets kept on their own lines."""
    paras = []      # list of paragraphs; each paragraph is a list of lines
    cur = []

    def flush():
        nonlocal cur
        if cur:
            paras.append(cur)
            cur = []

    for raw in text.splitlines():
        ln = raw.strip()
        if not ln:
            flush()
            continue
        if matching:
            # Keep the scrambled 2-column table line-per-line (legible + editable).
            flush()
            cur = [ln]
            flush()
            continue
        om = OPTION_RE.match(ln)
        is_option = bool(om) and len(om.group(2).split()) <= 14 and not ln.endswith(':')
        if SUBQ_RE.match(ln) or ln.startswith(PARA_START):
            flush()
            cur = [ln]
        elif CAPS_RE.match(ln):
            # Scenario/box titles stay on their own line.
            flush()
            paras.append([ln])
        elif is_option:
            flush()
            paras.append([f'{om.group(1)}   {om.group(2)}'])
        elif BULLET_RE.match(ln):
            flush()
            cur = ['- ' + BULLET_RE.sub('', ln)]
        else:
            if not cur and paras and OPTION_RE.match(paras[-1][0]):
                # Wrap-continuation of the previous option line (e.g. a long
                # Act name split across lines by the PDF).
                paras[-1][0] += ' ' + ln
            elif cur:
                cur.append(ln)
            else:
                cur = [ln]
    flush()
    out = []
    for p in paras:
        first = p[0]
        if first.startswith('- ') or OPTION_RE.match(first):
            out.append(' '.join([first] + [x.strip() for x in p[1:]]))
        else:
            out.append(' '.join(x.strip() for x in p))
    return '\n\n'.join(out)


def split_subqs(qtext, qn):
    """Split a QUESTION block into top-level sub-question blocks (n.1, n.2 ...)."""
    pat = re.compile(rf'^({qn}\.\d+)\s', re.M)
    marks = list(pat.finditer(qtext))
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(qtext)
        out.append((m.group(1), qtext[m.start():end].strip()))
    return out


def q_title(qb, qn):
    """QUESTION title, merging an ALL-CAPS continuation line (PDF wraps)."""
    lines = qb.splitlines()
    title = re.match(rf'QUESTION {qn}:\s*(.+)', lines[0]).group(1).strip()
    if len(lines) > 1 and not title.endswith(')') and CAPS_RE.match(lines[1].strip()):
        title += ' ' + lines[1].strip()
    return title


def split_children(lab, text):
    """Split a sub-question block into (stem, [(child_lab, child_text), ...])
    using 3-level numbers such as 2.3.1 / 1.1.4."""
    pat = re.compile(rf'^({re.escape(lab)}\.\d+)\.?\s', re.M)
    hits = list(pat.finditer(text))
    if not hits:
        return text.strip(), []
    stem = text[:hits[0].start()].strip()
    kids = []
    for i, h in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        kids.append((h.group(1), text[h.start():end].strip()))
    return stem, kids


TRAIL_MARK_RE = re.compile(r'\s*\((\d{1,2})\)\s*$')
MULT_MARK_RE = re.compile(r'\s*\(\d+\s*[x\u00d7]\s*\d+\)\s*(\(\d+\))?\s*$')


def strip_marks(text):
    """Remove trailing '(N)' / '(5 x 2) (10)' tokens (renderer prints its own)."""
    t = MULT_MARK_RE.sub('', text.rstrip())
    t = TRAIL_MARK_RE.sub('', t.rstrip())
    return t.strip()


def parse_paper(text):
    """Return dict: {'A': [(label, text, marks, qtype)], 'B': {qn: {'title':..,
    'subqs': [...]}} , 'C': {qn: {'title':.., 'text':.., 'marks': 40}}}"""
    t = clean(text)
    data = {'A': [], 'B': {}, 'C': {}}
    # ---- Section A: three objective blocks 1.1 / 1.2 / 1.3
    a_types = {'1.1': 'mcq', '1.2': 'fill_in_blank', '1.3': 'matching'}
    ends_a = [r'^1\.2\.?\s', r'^1\.3\.?\s', r'^TOTAL SECTION A']
    for lab in ('1.1', '1.2', '1.3'):
        start = rf'^{re.escape(lab)}\.?\s'
        later = [e for e in ends_a if not e.startswith('^' + re.escape(lab))]
        b = block(t, start, later)
        if b:
            data['A'].append((lab, b, 10, a_types[lab]))
    # ---- Section B: QUESTION 2..4
    for qn in (2, 3, 4):
        qb = block(t, rf'^QUESTION {qn}:',
                   [rf'^QUESTION {qn + 1}:', r'^TOTAL SECTION B', r'^SECTION C'])
        if not qb:
            continue
        title = q_title(qb, qn)
        subqs = []
        for lab, sub in split_subqs(qb, qn):
            m = sum_marks(sub)
            subqs.append((lab, sub, m))
        data['B'][qn] = {'title': title, 'subqs': subqs}
    # ---- Section C: QUESTION 5, 6 (essays)
    for qn in (5, 6):
        qb = block(t, rf'^QUESTION {qn}:',
                   [rf'^QUESTION {qn + 1}:', r'^TOTAL SECTION C', r'^GRAND TOTAL'])
        if not qb:
            continue
        title = q_title(qb, qn)
        body = re.sub(rf'^QUESTION {qn}:.*\n', '', qb, count=1).strip()
        # Drop a wrapped ALL-CAPS title continuation line from the body.
        first = body.split('\n', 1)[0].strip()
        if CAPS_RE.match(first) and first in title:
            body = body.split('\n', 1)[1].strip() if '\n' in body else ''
        data['C'][qn] = {'title': title, 'text': body, 'marks': 40}
    return data


def parse_memo(text):
    """Return dict {label: answer_text} for 1.1/1.2/1.3, n.m sub-questions and
    5/6 essays."""
    t = clean(text)
    answers = {}
    # Section A: Q1 block, split into 1.1/1.2/1.3
    q1 = block(t, r'^QUESTION 1\s*$', [r'^QUESTION 1 MARKS', r'^SECTION B', r'^QUESTION 2'])
    for lab in ('1.1', '1.2', '1.3'):
        later = [rf'^\s*1\.{int(lab[-1]) + 1}\s', r'^QUESTION', r'^SECTION']
        b = block(q1, rf'^\s*{re.escape(lab)}\s', later)
        if b:
            answers[lab] = b
    # Section B: QUESTION 2..4, split per top-level sub-question
    for qn in (2, 3, 4):
        qb = block(t, rf'^QUESTION {qn}[:\s]',
                   [rf'^QUESTION {qn} MARKS', rf'^QUESTION {qn + 1}[:\s]',
                    r'^SECTION C'])
        if not qb:
            continue
        for lab, sub in split_subqs(qb, qn):
            answers[lab] = sub
    # Section C essays
    for qn in (5, 6):
        qb = block(t, rf'^QUESTION {qn}[:\s]',
                   [rf'^QUESTION {qn + 1}[:\s]', r'^TOTAL SECTION C', r'\Z'])
        if qb:
            answers[str(qn)] = qb
    return answers


def build_paper(db, admin_id, pno, paper_txt, memo_txt):
    tag_paper = f'BSTD P{pno} May-June 2023'
    data = parse_paper(paper_txt)
    memo = parse_memo(memo_txt)

    def add_item(label, qtext, atext, marks, qtype, topic, section_tag):
        qid = str(uuid.uuid4())
        tags = (f'auto_import_v1,imported,past_paper,{tag_paper},P{pno},2023,'
                f'May-June,section_{section_tag},Q{label.split(".")[0]},{qtype}')
        db.execute(
            """insert into question_bank_items
               (id,owner_id,grade,subject,topic,subtopic,difficulty,question_type,
                question_text,answer_text,marks,tags,image_path,image_width,
                image_offset,is_shared,share_scope,created_at)
               values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (qid, admin_id, 12, 'Business Studies', topic,
             f'{tag_paper} - Q{label}', 'medium', qtype, qtext, atext, marks,
             tags, '', 0, 0, 1, 'public', datetime.now().isoformat(sep=' ')))
        return qid

    sections = []
    # ---------- Section A ----------
    a_ids, a_subitems = [], []
    for lab, text, marks, qtype in data['A']:
        # Drop the leading "1.1 " label — the renderer adds its own numbering.
        body = re.sub(rf'^{re.escape(lab)}\.?\s+', '', text)
        ans = memo.get(lab, '')
        ans = re.sub(rf'^\s*{re.escape(lab)}\s+', '', ans)
        if qtype == 'matching':
            a_ids.append(add_item(lab, reflow(body, matching=True), reflow(ans),
                                  marks, qtype, 'Objective Questions', 'A'))
            continue
        stem, kids = split_children(lab, body)
        if not kids:
            a_ids.append(add_item(lab, reflow(body), reflow(ans), marks, qtype,
                                  'Objective Questions', 'A'))
            continue
        _, akids = split_children(lab, ans)
        amap = {al: at for al, at in akids}
        each = marks // len(kids)
        a_ids.append(add_item(lab, reflow(stem), '', 0, qtype,
                              'Objective Questions', 'A'))
        for klab, ktext in kids:
            kbody = re.sub(rf'^{re.escape(klab)}\.?\s+', '', ktext)
            kans = amap.get(klab, '')
            kans = re.sub(rf'^{re.escape(klab)}\.?\s+', '', kans)
            a_subitems.append(len(a_ids))
            a_ids.append(add_item(klab, reflow(strip_marks(kbody)),
                                  reflow(strip_marks(kans)), each, qtype,
                                  'Objective Questions', 'A'))
    sections.append({
        'title': 'SECTION A (COMPULSORY)',
        'instructions': '',
        'marks': 30,
        'counted_marks': 30,
        'question_ids': a_ids,
        'splits': [0],
        'qtitles': [''],
        'qinstructions': [''],
        'qmemo_notes': [''],
        'subitems': a_subitems, 'forced_breaks': [], 'no_breaks': [],
    })
    # ---------- Section B ----------
    b_ids, b_splits, b_titles, b_subitems = [], [], [], []
    for qn in sorted(data['B']):
        info = data['B'][qn]
        b_splits.append(len(b_ids))
        b_titles.append(info['title'])
        for lab, sub, m in info['subqs']:
            body = re.sub(rf'^{re.escape(lab)}\s+', '', sub)
            ans = memo.get(lab, '')
            ans = re.sub(rf'^\s*{re.escape(lab)}\s+', '', ans)
            stem, kids = split_children(lab, body)
            if not kids:
                b_ids.append(add_item(lab, reflow(strip_marks(body)), reflow(ans),
                                      m, 'short_answer', info['title'].title(), 'B'))
                continue
            _, akids = split_children(lab, ans)
            amap = {al: at for al, at in akids}
            b_ids.append(add_item(lab, reflow(stem), '', 0, 'short_answer',
                                  info['title'].title(), 'B'))
            for klab, ktext in kids:
                kbody = re.sub(rf'^{re.escape(klab)}\.?\s+', '', ktext)
                km = sum_marks(ktext)
                kans = amap.get(klab, '')
                kans = re.sub(rf'^{re.escape(klab)}\.?\s+', '', kans)
                b_subitems.append(len(b_ids))
                b_ids.append(add_item(klab, reflow(strip_marks(kbody)),
                                      reflow(kans), km, 'short_answer',
                                      info['title'].title(), 'B'))
    sections.append({
        'title': 'SECTION B',
        'instructions': ('Answer ANY TWO questions in this section.\n\n'
                         'NOTE: Clearly indicate the QUESTION NUMBER of each question '
                         'that you choose. The answer to EACH question must start on '
                         'a NEW page.'),
        'marks': 80,
        'counted_marks': 80,
        'question_ids': b_ids,
        'splits': b_splits,
        'qtitles': b_titles,
        'qinstructions': [''] * len(b_titles),
        'qmemo_notes': [''] * len(b_titles),
        'subitems': b_subitems, 'forced_breaks': [], 'no_breaks': [],
    })
    # ---------- Section C ----------
    c_ids, c_splits, c_titles = [], [], []
    for qn in sorted(data['C']):
        info = data['C'][qn]
        c_splits.append(len(c_ids))
        c_titles.append(info['title'])
        ans = memo.get(str(qn), '')
        ans = reflow(ans)
        c_ids.append(add_item(f'{qn}.1', reflow(info['text']), ans, 40, 'paragraph',
                              info['title'].title(), 'C'))
    sections.append({
        'title': 'SECTION C',
        'instructions': ('Answer ANY ONE question in this section.\n\n'
                         'NOTE: Clearly indicate the QUESTION NUMBER of the chosen '
                         'question. The answer must start on a NEW page.'),
        'marks': 40,
        'counted_marks': 40,
        'question_ids': c_ids,
        'splits': c_splits,
        'qtitles': c_titles,
        'qinstructions': [''] * len(c_titles),
        'qmemo_notes': [''] * len(c_titles),
        'subitems': [], 'forced_breaks': [], 'no_breaks': [],
    })

    title = f'Business Studies P{pno} May-June 2023'
    instructions = (
        'This question paper consists of THREE sections and covers TWO main topics.\n'
        'SECTION A: COMPULSORY\n'
        'SECTION B: Consists of THREE questions. Answer any TWO of the three questions in this section.\n'
        'SECTION C: Consists of TWO questions. Answer any ONE of the two questions in this section.\n'
        'Read the instructions for each question carefully and take note of what is required.\n'
        'Number the answers correctly according to the numbering system used in this question paper.\n'
        'Except where other instructions are given, answers must be written in full sentences.\n'
        'Use the mark allocation and nature of each question to determine the length and depth of an answer.\n'
        'Begin the answer to EACH question on a NEW page.\n'
        'You may use a non-programmable calculator.\n'
        'Write neatly and legibly.')
    db.execute(
        """update generated_papers set sections=?, instructions=?,
           duration_minutes=120, total_marks=150, paper_number=?
           where title=?""",
        (json.dumps(sections, ensure_ascii=False), instructions, str(pno), title))
    n_items = len(a_ids) + len(b_ids) + len(c_ids)
    print(f'{title}: {n_items} bank items, sections A/B/C with '
          f'{len(a_ids)}/{len(b_ids)}/{len(c_ids)} questions')
    # Report missing memo matches
    missing = [lab for lab, *_ in data['A'] if not memo.get(lab)]
    for qn in data['B']:
        missing += [lab for lab, _, _ in data['B'][qn]['subqs'] if not memo.get(lab)]
    missing += [str(qn) for qn in data['C'] if not memo.get(str(qn))]
    if missing:
        print('  MISSING MEMO for:', missing)


def main():
    db = sqlite3.connect(DB)
    admin_id = db.execute("select id from users where username='admin'").fetchone()[0]
    # Idempotency: wipe any previous auto-import for these papers.
    db.execute("delete from question_bank_items where tags like '%BSTD P_ May-June 2023%'")
    for pno in (1, 2):
        paper_txt = open(f'_bs_dump_p{pno}.txt', encoding='utf-8').read()
        memo_txt = open(f'_bs_dump_p{pno}_mg.txt', encoding='utf-8').read()
        build_paper(db, admin_id, pno, paper_txt, memo_txt)
    db.commit()
    print('bank total (BS):', db.execute(
        "select count(*) from question_bank_items where subject='Business Studies'"
    ).fetchone()[0])


if __name__ == '__main__':
    main()
