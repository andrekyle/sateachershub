# Rebuild the Business Studies memo data so the generated marking guideline
# matches the official DBE MG PDFs (flowing layout):
#   * item answer_text in flow conventions (**bold**, "- " bullets, ">> token")
#   * essay answers with sub-block headings + BREAKDOWN OF MARK ALLOCATION table
#   * per-section memo_intro / memo_breakdown / memo_front_pages
import json
import os
import re
import sqlite3

import pdfplumber

DB = 'instance/brandcartel.db' if os.path.exists('instance/brandcartel.db') else 'brandcartel.db'

TOKEN_RE = re.compile(
    r'(\(\d+\s*x\s*\d+\)\s*(?:\(\d+\))?'          # (4 x 1) (4) / (5 x 2)
    r'|Any\s*\(\d+\s*x\s*\d+\)\s*\(\d+\)'          # Any (1 x 2) (2)
    r'|Sub\s?max\s*\(\d+\)|Submax\s*\(\d+\)'
    r'|Max\s*\(\d+\)'
    r'|Type\s*\(\d+\)|Discussion\s*\(\d+\)|Motivation\s*\(\d+\)'
    r'|\[\d+\])\s*$')
NOISE = [re.compile(r'^Copyright reserved'), re.compile(r'^Business Studies/P\d'),
         re.compile(r'^SC/NSC'), re.compile(r'^Please turn over'),
         re.compile(r'^\d+\s*$'), re.compile(r'^DBE/2023')]


def mg_text(pno):
    path = f'static/uploads/Business Studies P{pno} May-June 2023 MG Eng.pdf'
    with pdfplumber.open(path) as pdf:
        t = '\n'.join(p.extract_text() or '' for p in pdf.pages)
    t = t.replace('\uf02d', '\u2013').replace('\u2212', '-')
    lines = [ln for ln in t.splitlines()
             if not any(nz.match(ln.strip()) for nz in NOISE)]
    return '\n'.join(lines)


def block(text, start_pat, end_pats):
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


def split_labeled(text, label_re):
    hits = list(re.finditer(label_re, text, re.M))
    out = []
    for i, h in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        out.append((h.group(1), text[h.start():end].strip()))
    return out


def to_flow(body, heading_bold=True):
    """Convert an MG answer block to flow-format lines."""
    lines = [l.rstrip() for l in body.splitlines()]
    out = []
    cur = None          # current logical line being assembled
    cur_kind = None     # 'b' bullet | 'p' paragraph

    def flush():
        nonlocal cur, cur_kind
        if cur is None:
            return
        t = ' '.join(cur.split())
        # peel trailing tokens (possibly several, e.g. "... Max (4)")
        while True:
            m = TOKEN_RE.search(t)
            if m and m.start() > 0:
                tail = t[m.start():].strip()
                t = t[:m.start()].rstrip()
                out.append(('tok', tail))
                continue
            break
        if t:
            out.append((cur_kind, t))
        cur = None
        cur_kind = None

    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if re.fullmatch(TOKEN_RE.pattern.rstrip('$') + r'\s*', s):
            flush()
            out.append(('tok', s.strip()))
            continue
        if s.startswith('-'):
            flush()
            cur = s[1:].strip()
            cur_kind = 'b'
        elif re.match(r'^o\s+\S', s):
            flush()
            cur = s[2:].strip()
            cur_kind = 'ob'
        elif s.upper().startswith('NOTE'):
            flush()
            cur = s
            cur_kind = 'note'
        else:
            if cur is not None:
                cur += ' ' + s
            else:
                cur = s
                cur_kind = 'p'
    flush()
    # tokens recorded mid-line above are appended AFTER the line they trailed;
    # reorder: keep as-is (order of appearance).
    res = []
    first_para = True
    for kind, t in out:
        if kind == 'tok':
            res.append('>> ' + t)
        elif kind == 'b':
            res.append('- ' + t)
        elif kind == 'ob':
            res.append('o ' + t)
        elif kind == 'note':
            res.append('**' + t + '**')
        else:
            if first_para and heading_bold:
                res.append('**' + t + '**')
            else:
                res.append(t)
        if kind == 'p':
            first_para = False
    return '\n'.join(res)


ALLOC = {
    (1, 5): [('Introduction', 2), ('Purpose of BBBEE Act', 10),
             ('Advantages of BBBEE for businesses', 14),
             ('Penalties for non-compliance with the BBBEE Act', 10),
             ('Application of the following BBBEE pillars in the workplace:<br>o&nbsp; Management control<br>o&nbsp; Ownership', 12),
             ('Conclusion', 2)],
    (1, 6): [('Introduction', 2), ('Selection procedure', 10),
             ('Role of the interviewer before the interview', 12),
             ('Legal requirements of an employment contract', 12),
             ('Purpose of induction', 12), ('Conclusion', 2)],
    (2, 5): [('Introduction', 2), ('Advantages of insurance for businesses', 12),
             ('Differences between over-insurance and under-insurance', 8),
             ('Type of benefits paid out by Unemployment Insurance Fund (UIF)', 16),
             ('Indemnification/Indemnity as a principle of insurance', 10),
             ('Conclusion', 2)],
    (2, 6): [('Introduction', 2),
             ('Responsibilities of workers in promoting human health and safety in the workplace', 10),
             ('Dealing with diversity issues in the workplace', 16),
             ('Benefits of diversity in the workplace', 10),
             ('Ways to promote cultural rights in the workplace', 10),
             ('Conclusion', 2)],
}
INSIGHT_ROWS = [('Layout', 2), ('Analysis/Interpretation', 2),
                ('Synthesis', 2), ('Originality/Examples', 2)]


def alloc_table_html(pno, qn):
    td = 'border:1px solid #000; padding:2px 8px; font-size:10.5pt; vertical-align:top;'
    tdc = td + ' text-align:center;'
    content = ALLOC[(pno, qn)]
    html = ['<table style="border-collapse:collapse; width:100%; margin:8px 0;">']
    html.append(f'<tr><th style="{tdc}">DETAILS</th><th style="{tdc}">MAXIMUM</th><th style="{tdc}">TOTAL</th></tr>')
    for i, (label, n) in enumerate(content):
        html.append(f'<tr><td style="{td}">{label}</td><td style="{tdc}">{n}</td>')
        if i == 0:
            html.append(f'<td style="{tdc} vertical-align:middle;" rowspan="{len(content)}"><b>Max<br>32</b></td>')
        html.append('</tr>')
    for i, (label, n) in enumerate(INSIGHT_ROWS):
        html.append(f'<tr><td style="{td}">{"<b>INSIGHT</b><br>" if i == 0 else ""}{label}</td><td style="{tdc}">{n}</td>')
        if i == 0:
            html.append(f'<td style="{tdc} vertical-align:middle;" rowspan="{len(INSIGHT_ROWS)}"><b>8</b></td>')
        html.append('</tr>')
    html.append(f'<tr><td style="{td}"><b>TOTAL MARKS</b></td><td style="{tdc}"></td><td style="{tdc}"><b>40</b></td></tr>')
    html.append('</table>')
    return ''.join(html)


def alloc_table(alloc_text):
    """Hand-parse the BREAKDOWN OF MARK ALLOCATION block into an HTML table."""
    # rows between DETAILS/MAXIMUM/TOTAL header and TOTAL MARKS
    body = block(alloc_text, r'^DETAILS', [r'^TOTAL MARKS'])
    lines = [l.strip() for l in body.splitlines()[1:] if l.strip() and l.strip() not in ('MAXIMUM', 'TOTAL')]
    # Assemble (label, number) pairs: numbers are standalone tokens.
    rows = []
    buf = []
    for ln in lines:
        if re.fullmatch(r'\d+', ln):
            label = ' '.join(buf).strip()
            buf = []
            if label in ('Max',):
                continue
            rows.append([label, ln])
        elif ln == 'Max':
            continue
        elif ln == 'INSIGHT':
            rows.append(['INSIGHT', ''])
        else:
            buf.append(ln)
    # classify: content rows until 'Conclusion', then INSIGHT sub-rows
    td = 'border:1px solid #000; padding:2px 8px; font-size:10.5pt;'
    tdc = td + ' text-align:center;'
    content_rows = []
    insight_rows = []
    mode = 'content'
    for label, n in rows:
        if label == 'INSIGHT':
            mode = 'insight'
            continue
        (content_rows if mode == 'content' else insight_rows).append((label, n))
    n_c = len(content_rows)
    n_i = len(insight_rows)
    html = ['<table style="border-collapse:collapse; width:100%; margin:8px 0;">']
    html.append(f'<tr><th style="{tdc}">DETAILS</th><th style="{tdc}">MAXIMUM</th><th style="{tdc}">TOTAL</th></tr>')
    for i, (label, n) in enumerate(content_rows):
        html.append(f'<tr><td style="{td}">{label}</td><td style="{tdc}">{n}</td>')
        if i == 0:
            html.append(f'<td style="{tdc} vertical-align:middle;" rowspan="{n_c}"><b>Max<br>32</b></td>')
        html.append('</tr>')
    for i, (label, n) in enumerate(insight_rows):
        html.append(f'<tr><td style="{td}">{"<b>INSIGHT</b><br>" if i == 0 else ""}{label}</td><td style="{tdc}">{n}</td>')
        if i == 0:
            html.append(f'<td style="{tdc} vertical-align:middle;" rowspan="{n_i}"><b>8</b></td>')
        html.append('</tr>')
    html.append(f'<tr><td style="{td}"><b>TOTAL MARKS</b></td><td style="{tdc}"></td><td style="{tdc}"><b>40</b></td></tr>')
    html.append('</table>')
    return ''.join(html)


def build_paper(db, pno):
    tag = f'BSTD P{pno} May-June 2023'
    t = mg_text(pno)

    def set_ans(label, ans):
        sub = f'{tag} - Q{label}'
        row = db.execute('select id from question_bank_items where subtopic=?', (sub,)).fetchone()
        if not row:
            print('  !! missing item', sub)
            return
        db.execute('update question_bank_items set answer_text=? where id=?', (ans, row[0]))

    # ---- Section A: 1.1/1.2/1.3 child answers (letters/words)
    q1 = block(t, r'^QUESTION 1\s*$', [r'^BREAKDOWN OF MARKS', r'^SECTION B'])
    for blk_lab in ('1.1', '1.2', '1.3'):
        nxt = f'1.{int(blk_lab[-1]) + 1}'
        b = block(q1, rf'^{re.escape(blk_lab)}\s', [rf'^{re.escape(nxt)}\s', r'^TOTAL SECTION A', r'^\(5 x 2\)'])
        kids = split_labeled(b, rf'^({re.escape(blk_lab)}\.\d)')
        for i, (klab, ktext) in enumerate(kids):
            ans = re.sub(rf'^{re.escape(klab)}\s*', '', ktext).strip()
            ans = ' '.join(ans.split())
            ans = re.sub(r'\(5 x 2\).*$', '', ans).strip()
            if i == len(kids) - 1:
                ans += '\n>> (5 x 2) (10)'
            set_ans(klab, ans)
        set_ans(blk_lab, '')  # stems carry no memo answer

    # ---- Section B: questions 2-4
    for qn in (2, 3, 4):
        qb = block(t, rf'^QUESTION {qn}[:\s]',
                   [rf'^QUESTION {qn} \nMARKS', rf'^QUESTION {qn}\s+MARKS', rf'^BREAKDOWN OF MARKS', rf'^QUESTION {qn + 1}[:\s]', r'^SECTION C'])
        subs = split_labeled(qb, rf'^({qn}\.\d+(?:\.\d+)?)\s')
        for lab, sub_text in subs:
            body = re.sub(rf'^{re.escape(lab)}\s*', '', sub_text)
            set_ans(lab, to_flow(body))

    # ---- Section C: essays 5, 6
    for qn in (5, 6):
        qb = block(t, rf'^QUESTION {qn}:',
                   [rf'^QUESTION {qn}:?\s*\n?\s*BREAKDOWN OF MARK', rf'^QUESTION {qn + 1}:', r'^TOTAL SECTION C', r'\Z'])
        # strip the heading line
        body = re.sub(rf'^QUESTION {qn}:[^\n]*\n(?:[A-Z ()&:,\u2013-]+\n)?', '', qb, count=1)
        subs = split_labeled(body, rf'^({qn}\.\d)\s')
        parts = []
        for lab, sub_text in subs:
            sb = re.sub(rf'^{re.escape(lab)}\s*', '', sub_text)
            # first line is the sub-heading
            flow = to_flow(sb)
            flow_lines = flow.split('\n')
            if flow_lines and flow_lines[0].startswith('**'):
                flow_lines[0] = f'**{lab} ' + flow_lines[0][2:]
            parts.append('\n'.join(flow_lines))
        essay = '\n'.join(parts)
        # collapse duplicated trailing [40] tokens
        essay = re.sub(r'(?:\n>> \[40\])+', '\n>> [40]', essay)
        if not essay.rstrip().endswith('>> [40]'):
            essay += '\n>> [40]'
        # alloc table (hardcoded from the MG PDF — the flattened text
        # extraction loses the column numbers)
        essay += f'\n**QUESTION {qn}: BREAKDOWN OF MARK ALLOCATION**\n' + alloc_table_html(pno, qn)
        essay += ('\n**LASO \u2013 For each component:**'
                  '\nAllocate 2 marks if all requirements are met.'
                  '\nAllocate 1 mark if some requirements are met.'
                  '\nAllocate 0 marks where requirements are not met at all')
        set_ans(f'{qn}.1', essay)

    # ---- Section metadata
    title = f'Business Studies P{pno} May-June 2023'
    row = db.execute('select id,sections from generated_papers where title=?', (title,)).fetchone()
    secs = json.loads(row[1])
    secs[0]['memo_breakdown'] = {'1': [['1.1', 10], ['1.2', 10], ['1.3', 10]]}
    secs[1]['memo_intro'] = 'Mark the FIRST TWO answers only.'
    secs[1].pop('memo_breakdown', None)
    secs[2]['memo_intro'] = 'Mark the FIRST answer only.'
    secs[2]['memo_breakdown'] = {}
    secs[0]['memo_front_pages'] = front_pages(pno)
    db.execute('update generated_papers set sections=? where id=?',
               (json.dumps(secs, ensure_ascii=False), row[0]))
    print(f'{title}: memo rebuilt')


def front_pages(pno):
    """The NOTES TO MARKERS front matter (MG pages 2-6), shared by P1/P2."""
    b = '<b>%s</b>'
    item = ('<div style="display:grid; grid-template-columns:52px 1fr; column-gap:8px;'
            ' margin:0 0 10px;"><div>%s</div><div style="text-align:justify;">%s</div></div>')
    sub = ('<div style="display:grid; grid-template-columns:52px 1fr; column-gap:8px;'
           ' margin:0 0 10px 52px;"><div>%s</div><div style="text-align:justify;">%s</div></div>')
    bullet = '<div style="margin:0 0 3px 24px;">\u2022&nbsp; %s</div>'
    tick = '\u221a'
    p1 = (
        '<div style="font-weight:bold; margin-bottom:8px;">NOTES TO MARKERS</div>'
        '<div style="border:1.5px solid #000; padding:6px 12px; margin-bottom:14px;">'
        '<div style="font-weight:bold;">PREAMBLE</div>'
        '<div style="margin:6px 0;">The notes to markers are provided for quality assurance purposes to ensure the following:</div>'
        + item % ('(a)', 'Fairness, consistency and reliability in the standard of marking')
        + item % ('(b)', "Facilitate the moderation of candidates' scripts at the different levels")
        + item % ('(c)', 'Streamline the marking process considering the broad spectrum of markers across the country')
        + item % ('(d)', 'Implement appropriate measures in the teaching, learning and assessment of the subject at schools/institutions of learning')
        + '</div>'
        + item % ('1.', 'For marking and moderation purposes, the following colours are recommended:'
                  '<table style="border:none; border-collapse:collapse; margin:8px 0 0;">'
                  + ''.join(f'<tr><td style="border:none; padding:1px 40px 1px 0;">{a}:</td><td style="border:none; padding:1px 0;">{c}</td></tr>'
                            for a, c in [('Marker', 'Red'), ('Senior Marker', 'Green'), ('Deputy Chief Marker', 'Brown/Blue'),
                                         ('Chief Marker', 'Pink'), ('Internal Moderator', 'Orange'), ('DBE Moderator', 'Turquoise')])
                  + '</table>')
        + item % ('2.', "Candidates' responses must be in full sentences for SECTIONS B and C. However, this would depend on the nature of the question.")
        + item % ('3.', 'A comprehensive marking guideline has been provided but this is by no means exhaustive. Due consideration should be given to an answer that is correct but:'
                  + bullet % 'Uses a different expression from that which appears in the marking guideline'
                  + bullet % 'Comes from another credible source'
                  + bullet % 'Original'
                  + bullet % 'A different approach is used'
                  + '<div style="margin-top:6px;"><b>NOTE:&nbsp; There is only ONE correct answer in SECTION A.</b></div>')
        + item % ('4.', 'Take note of other relevant answers, provided by candidates, which relate to a particular question and allocate marks accordingly. (In cases where the answer is unclear or indicates some understanding, part-marks should be awarded, for example, one mark instead of the maximum of two marks.)')
        + item % ('5.', "The word 'Sub max' is used to facilitate the allocation of marks within a question or sub-question.")
        + item % ('6.', "The purpose of circling marks (guided by 'max' in the breakdown of marks) on the right-hand side is to ensure consistency and accuracy in the marking of scripts as well as for calculation and moderation purposes.")
        + item % ('7.', "Subtotals to questions must be written in the right-hand margin. Circle the subtotals as indicated by the allocation of marks. This must be guided by 'max' in the marking guidelines. Only the total for each question should appear in the left-hand margin next to the appropriate question number.")
        + item % ('8.', 'In an indirect question, the theory as well as the response must be relevant and related to the question.')
    )
    p2 = (
        item % ('9.', "Correct numbering of answers to questions or sub questions is recommended in SECTIONS A and B. However, if the numbering is incorrect, follow the sequence of the candidate's responses. Candidates will be penalised if the latter is not clear.")
        + item % ('10.', "No additional credit must be given for repetition of facts. Indicate with an 'R'.")
        + item % ('11.', "The differentiation between 'evaluate' and 'critically evaluate' can be explained as follows:")
        + sub % ('11.1', "When 'evaluate' is used, candidates are expected to respond in either a positive/negative manner or take a neutral (positive and negative) stance, e.g., <b>Positive</b>: <i>'COIDA eliminates time and costs spent" + tick + " on lengthy civil court proceedings.'" + tick + '</i>')
        + sub % ('11.2', "When 'critically evaluate' is used, candidates are expected to respond in either a positive/negative manner or take a neutral (positive and negative) stance. In this instance candidates are also expected to support their responses with more depth, e.g., <i>'COIDA eliminates time and costs spent" + tick + " on lengthy civil court proceedings" + tick + ", because the employer will not be liable for compensation to the employee for injuries sustained during working hours as long as it can be proved that the business was not negligent.'" + tick + '</i>')
        + sub % ('<b>NOTE:</b>', "1.&nbsp; The above could apply to 'analyse' as well.<br>2.&nbsp; Note the placing of the tick (" + tick + ') in the allocation of marks.')
        + item % ('12.', 'The allocation of marks must be informed by the nature of the question, cognitive verb used, mark allocation in the marking guideline and the context of each question.<div style="margin-top:8px;">Cognitive verbs, such as:</div>')
        + sub % ('12.1', "Advise, name, state, outline, motivate, recommend, suggest, <i>(list not exhaustive)</i> do not usually require much depth in candidates' responses. Therefore, the mark allocation for each statement/answer appears at the end.")
        + sub % ('12.2', 'Define, describe, explain, discuss, elaborate, distinguish, differentiate, compare, tabulate, analyse, evaluate, critically evaluate (<i>list not exhaustive</i>) require a greater depth of understanding, application and reasoning. Therefore, the marks must be allocated more objectively to ensure that assessment is conducted according to established norms so that uniformity, consistency and fairness are achieved.')
        + item % ('13.', 'Mark only the FIRST answer where candidates offer more than one answer for SECTION B and C questions that require one answer.')
    )
    p3 = (
        item % ('14.', b % 'SECTION B')
        + sub % ('14.1', "If for example, FIVE facts are required, mark the candidate's FIRST FIVE responses and ignore the rest of the responses. Indicate by drawing a line across the unmarked portion."
                 '<div style="margin-top:6px;"><b>NOTE:</b>&nbsp; 1.&nbsp; This applies only to questions where the number of facts is specified.<br>'
                 '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.&nbsp; The above also applies to responses in SECTION C. (where applicable)</div>')
        + sub % ('14.2', 'If two facts are written in one sentence, award the candidate FULL credit. Point 14.1 above still applies.')
        + sub % ('14.3', 'If candidates are required to provide their own examples/views, brainstorm this at the marking centre and refer to the DBE internal moderator to finalise the alternative answers in consultation with the UMALUSI external moderators.')
        + sub % ('14.4', b % 'Use of the cognitive verbs and allocation of marks:')
        + sub % ('14.4.1', "If the number of facts are specified, questions that require candidates to 'describe/discuss/explain' may be marked as follows:"
                 + bullet % 'Fact&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 2 marks (or as indicated in the marking guidelines)'
                 + bullet % 'Explanation&nbsp; 1 mark (two marks will be allocated in Section C)'
                 + "<div style='margin-top:6px;'>The 'fact' and 'explanation' are given separately in the marking guideline to facilitate mark allocation.</div>")
        + sub % ('14.4.2', 'If the number of facts required is not specified, the allocation of marks must be informed by the nature of the question and the maximum mark allocated in the marking guideline.')
        + sub % ('14.5', b % 'ONE mark may be awarded for answers that are easy to recall, requires one-word answers or is quoted directly from a scenario/case study. This applies to SECTIONS B and C in particular (where applicable).')
        + item % ('15.', b % 'SECTION C')
        + sub % ('15.1', 'The breakdown of the mark allocation for the essays is as follows:'
                 '<table style="border-collapse:collapse; margin:8px 0 0; width:64%;">'
                 '<tr><td style="border:1px solid #000; padding:2px 8px;">Introduction</td>'
                 '<td style="border:1px solid #000; padding:2px 8px; text-align:center; vertical-align:middle;" rowspan="3"><b>Maximum:<br>32</b></td></tr>'
                 '<tr><td style="border:1px solid #000; padding:2px 8px;">Content</td></tr>'
                 '<tr><td style="border:1px solid #000; padding:2px 8px;">Conclusion</td></tr>'
                 '<tr><td style="border:1px solid #000; padding:2px 8px;">Insight</td><td style="border:1px solid #000; padding:2px 8px; text-align:center;"><b>8</b></td></tr>'
                 '<tr><td style="border:1px solid #000; padding:2px 8px;"><b>TOTAL</b></td><td style="border:1px solid #000; padding:2px 8px; text-align:center;"><b>40</b></td></tr>'
                 '</table>')
    )
    _td = 'border:1px solid #000; padding:3px 8px; font-size:10.5pt; vertical-align:top;'
    _guide = ('<div style="display:grid; grid-template-columns:1fr auto; column-gap:12px;">'
              '<div>%s</div><div>%s</div></div>')
    _opt = ('<div style="display:grid; grid-template-columns:64px 1fr; column-gap:6px; margin-top:4px;">'
            '<div>Option %s:</div><div><b>%s</b><br><div style="text-align:justify;">%s</div></div></div>')
    _note = ('<div style="display:grid; grid-template-columns:52px 24px 1fr; column-gap:6px; margin-top:%s;">'
             '<div><b>%s</b></div><div><b>%s</b></div><div style="text-align:justify;"><b>%s</b></div></div>')
    p4 = (
        sub % ('15.2', 'Insight consists of the following components:'
               f'<table style="border-collapse:collapse; width:100%; margin:8px 0 0;">'
               f'<tr><td style="{_td} width:22%;">Layout/Structure</td><td style="{_td}">Is there an introduction, paragraphs and a conclusion?</td><td style="{_td} text-align:center; width:7%;"><b>2</b></td></tr>'
               f'<tr><td style="{_td}">Analysis and interpretation</td><td style="{_td}"><div style="text-align:justify;">Is the candidate able to break down the question into headings/subheadings/interpret it correctly to show understanding of what is being asked?</div>'
               '<div style="margin-top:6px;">Marks to be allocated using this guide:</div>'
               + _guide % ('All headings addressed:', "1 (One 'A')")
               + _guide % ('Interpretation (16 to 32 marks):', "1 (One 'A')")
               + f'</td><td style="{_td} text-align:center;"><b>2</b></td></tr>'
               f'<tr><td style="{_td}">Synthesis</td><td style="{_td}"><div style="text-align:justify;">Are there relevant decisions/facts/responses made based on the questions?</div>'
               '<div>Marks to be allocated using this guide:</div>'
               + _opt % ('1', "Only relevant facts:&nbsp; 2 marks (No '-S')",
                         "Where a candidate answers 50% or more (two to four sub-questions) of the question with only relevant facts; no '-S' appears in the left margin. Award the maximum of TWO (2) marks for synthesis.")
               + _opt % ('2', "Some relevant facts:&nbsp; 1 mark (One '-S')",
                         "Where a candidate answers less than 50% (only one sub-question) of the question with only OR some relevant facts; one '-S' appears in the left margin. Award a maximum of ONE (1) mark for synthesis.")
               + _opt % ('3', "Some relevant facts:&nbsp; 1 mark (One '-S')",
                         "Where a candidate writes FOUR sub-questions, but one/two/three sub-question(s) with irrelevant facts; one '-S' appears in the left margin. Award a maximum of ONE (1) mark for synthesis.")
               + _opt % ('4', "No relevant facts:&nbsp; 0 marks (Two '-S')",
                         "Where a candidate answers less than 50% (only one sub-question) of the question with no relevant facts; two '-S' appear in the left margin. Award a ZERO mark for synthesis.")
               + f'</td><td style="{_td} text-align:center;"><b>2</b></td></tr>'
               f'<tr><td style="{_td}">Originality</td><td style="{_td} text-align:justify;">Is there evidence of one or two examples, not older than two (2) years, that are based on recent information, current trends and developments?</td><td style="{_td} text-align:center;"><b>2</b></td></tr>'
               f'<tr><td style="{_td} text-align:right;" colspan="2"><b>TOTAL FOR INSIGHT:</b></td><td style="{_td} text-align:center;"><b>8</b></td></tr>'
               f'<tr><td style="{_td} text-align:right;" colspan="2"><b>TOTAL MARKS FOR FACTS:</b></td><td style="{_td} text-align:center;"><b>32</b></td></tr>'
               f'<tr><td style="{_td} text-align:right;" colspan="2"><b>TOTAL MARKS FOR ESSAY (8 + 32):</b></td><td style="{_td} text-align:center;"><b>40</b></td></tr>'
               '</table>'
               + _note % ('10px', 'NOTE:', '1.', 'No marks will be awarded for contents repeated from the introduction and conclusion.')
               + _note % ('8px', '', '2.', 'The candidate forfeits marks for layout if the words INTRODUCTION and CONCLUSION are not stated.')
               + _note % ('8px', '', '3.', 'No marks will be awarded for layout, if the headings INTRODUCTION and CONCLUSION are not supported by an explanation.'))
    )
    p5 = (
        sub % ('15.3', "Indicate insight in the left-hand margin with a symbol e.g. ('L, A, -S and/or O').")
        + sub % ('15.4', 'The breakdown of marks is indicated at the end of the suggested answer/ marking guideline to each question.')
        + sub % ('15.5', 'Mark all relevant facts until the SUBMAX/MAX mark in a subsection has been attained. Write SUBMAX/MAX after maximum marks have been obtained, but continue reading for originality "O".')
        + sub % ('15.6', 'At the end of each essay indicate the allocation of marks for facts and marks for insight as follows: (L \u2013 Layout, A \u2013 Analysis, S \u2013 Synthesis, O \u2013 Originality) as in the table below.'
                 '<table style="border-collapse:collapse; margin:8px 0 0; width:56%;">'
                 '<tr><th style="border:1px solid #000; padding:2px 8px; text-align:center;">CONTENT</th><th style="border:1px solid #000; padding:2px 8px; text-align:center;">MARKS</th></tr>'
                 + ''.join(f'<tr><td style="border:1px solid #000; padding:2px 8px; text-align:center;">{a}</td><td style="border:1px solid #000; padding:2px 8px; text-align:center;">{c}</td></tr>'
                           for a, c in [('Facts', '<b>32 (max.)</b>'), ('L', '2'), ('A', '2'), ('S', '2'), ('O', '2')])
                 + '<tr><td style="border:1px solid #000; padding:2px 8px; text-align:center;"><b>TOTAL</b></td><td style="border:1px solid #000; padding:2px 8px; text-align:center;"><b>40</b></td></tr>'
                 '</table>')
        + sub % ('15.7', 'When awarding marks for facts, take note of the sub-maxima indicated, especially if candidates do not make use of the same subheadings. Remember, headings and subheadings are encouraged and contribute to insight (structuring/logical flow/sequencing) and indicate clarity of thought. (See MARK BREAKDOWN at the end of each question.)')
        + sub % ('15.8', 'If the candidate identifies/interprets the question INCORRECTLY, then he/she may still obtain marks for layout.')
        + sub % ('15.9', 'If a different approach is used by candidates, ensure that the answers are assessed according to the mark allocation/subheadings as indicated in the marking guideline.')
        + sub % ('15.10', "15.10.1&nbsp; Award TWO marks for complete sentences. Award ONE mark for phrases, incomplete sentences and vague answers.<br><br>"
                 "15.10.2&nbsp; With effect from November 2015, the TWO marks will not necessarily appear at the end of each completed sentence. The ticks (" + tick + ") will be separated and indicated next to each fact, e.g., <i>'Each team member has a chance to participate without interference from other team members" + tick + " thereby avoiding the likelihood of one person dominating the group process.'" + tick + "</i><br><br>This will be informed by the nature and context of the question, as well as the cognitive verb used.")
        + sub % ('15.11', 'With effect from November 2017, the maximum of TWO (2) marks for facts shown as headings in the marking guidelines, will not necessarily apply to each question.  This would also depend on the nature of the question.')
    )
    return [p1, p2, p3, p4, p5]


def main():
    db = sqlite3.connect(DB)
    for pno in (1, 2):
        build_paper(db, pno)
    db.commit()
    print('done')


if __name__ == '__main__':
    main()
