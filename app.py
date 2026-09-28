from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify, abort, Response, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import uuid
import json
import re
import types
import csv
import io

from dotenv import load_dotenv
if os.path.exists('.env.development.local'):
    load_dotenv('.env.development.local')
elif os.path.exists('.env'):
    load_dotenv('.env')

from config import Config
from exam_guidelines import (
    CAPS_PAPER_TEMPLATES, CAPS_GUIDELINES, flatten_template
)

# =====================================================================
#  SHORT ANSWER GRADER  — expert-teacher-level scoring algorithm
# =====================================================================
_SA_STOP = {
    'a','an','the','is','are','was','were','be','been','being','have','has',
    'had','do','does','did','will','would','could','should','may','might',
    'must','shall','can','of','in','to','for','on','at','by','with','from',
    'as','that','this','these','those','it','its','they','them','and','or',
    'but','so','yet','i','you','he','she','we','my','your','his','her','our',
    'what','which','who','when','where','how','also','just','then','than',
}
_SA_NEGATIONS = {
    'not','never','no','neither','nor','nothing','nobody','nowhere','without',
    'lack','lacking','absent','absence','cannot','cant',
}

# Synonym map — each key maps to a set of equivalent words
# Covers common academic + CS/computer science vocabulary
_SA_SYNONYMS = {
    # CPU / Processor
    'cpu':{'processor','microprocessor'}, 'processor':{'cpu','microprocessor'},
    'microprocessor':{'cpu','processor'},
    # Memory / Storage
    'ram':{'memory'}, 'memory':{'ram'},
    'store':{'hold','contain','save','keep','retain','record'},
    'stores':{'holds','contains','saves','keeps','retains'},
    'storing':{'holding','containing','saving','keeping'},
    'stored':{'held','contained','saved','kept','recorded'},
    'hold':{'store','contain','keep','retain'}, 'holds':{'stores','contains','keeps'},
    'holding':{'storing','containing'},
    'storage':{'memory','retention','repository'},
    # Temporary / volatile
    'temporary':{'volatile','transient','short-term','momentary'},
    'temporarily':{'volatile','transiently','short-term'},
    'volatile':{'temporary','temporarily','transient'},
    # Active / current
    'active':{'current','running','present','ongoing'},
    'actively':{'currently','presently'},
    'currently':{'actively','presently','now'},
    'current':{'active','present','ongoing'},
    # Speed
    'fast':{'quick','rapid','speedy','swift'}, 'quick':{'fast','rapid','speedy'},
    'quickly':{'rapidly','swiftly','fast'}, 'rapidly':{'quickly','fast'},
    # Data / Information
    'data':{'information','info','content'}, 'information':{'data','info'},
    # Allow / enable
    'allow':{'enable','permit','let'}, 'allows':{'enables','permits'},
    'enables':{'allows','permits'}, 'enable':{'allow','permit'},
    # Use / utilize
    'use':{'utilize','employ','access'}, 'uses':{'utilizes','employs'},
    'using':{'utilizing','employing','accessing'},
    'used':{'utilized','employed','accessed'},
    # Permanent / persistent
    'permanent':{'persistent','non-volatile','long-term','fixed'},
    'permanently':{'persistently','non-volatile'},
    # Read / access
    'read':{'access','retrieve','fetch'}, 'reads':{'accesses','retrieves'},
    'access':{'read','retrieve','fetch'}, 'accesses':{'reads','retrieves'},
}

def _stem(word):
    """Lightweight suffix stripping — returns the root form."""
    for sfx in ('tion','sion','ness','ment','ity','ous','ive','ful','less',
                'able','ible','ance','ence','ing','er','ed','ly','al','es','s'):
        if word.endswith(sfx) and len(word) - len(sfx) >= 3:
            return word[:-len(sfx)]
    return word

def _expand(tokens):
    """Return an expanded set of tokens including stems and synonyms."""
    expanded = set(tokens)
    for t in tokens:
        # Add synonyms of the exact token
        for syn in _SA_SYNONYMS.get(t, set()):
            expanded.add(syn)
        # Add stem
        s = _stem(t)
        expanded.add(s)
        # Add synonyms of the stem
        for syn in _SA_SYNONYMS.get(s, set()):
            expanded.add(syn)
    return expanded

def _sa_normalize(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s'-]", ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def _sa_tokens(text):
    return [w for w in _sa_normalize(text).split()
            if w not in _SA_STOP and len(w) > 1]

def _lev_ratio(a, b):
    """Character-level Levenshtein similarity ratio."""
    if a == b:
        return 1.0
    la, lb = len(a), len(b)
    if la == 0 or lb == 0:
        return 0.0
    dp = list(range(lb + 1))
    for i, ca in enumerate(a):
        prev, dp[0] = dp[0], i + 1
        for j, cb in enumerate(b):
            prev, dp[j+1] = dp[j+1], min(prev + (0 if ca == cb else 1),
                                          dp[j] + 1, dp[j+1] + 1)
    return 1.0 - dp[lb] / max(la, lb)

def _kw_match(keyword, norm_user_text):
    """Check if a keyword appears in user text (exact or near-match)."""
    kw = _sa_normalize(keyword)
    if kw in norm_user_text:
        return True
    for w in norm_user_text.split():
        if len(w) >= 3 and _lev_ratio(kw, w) >= 0.88:
            return True
    # Also check expanded synonyms of keyword in user text
    for syn in _SA_SYNONYMS.get(kw, set()):
        if syn in norm_user_text:
            return True
    return False

def grade_short_answer(user_answer, model_answer, keywords=None, min_ratio=0.6):
    """
    Expert-teacher-level short answer grader.

    Scoring (weighted composite):
      40% — Jaccard similarity on expanded+stemmed content-word sets
      30% — Teacher keyword coverage  (if keywords provided)
      20% — Full-string Levenshtein similarity
      10% — Token sequence / LCS ordering bonus

    Expansions applied: synonym dictionary, lightweight suffix stemming,
    Levenshtein fuzzy matching for typos.
    Negation mismatch is penalised heavily (—0.35).

    Returns (is_correct: bool, score_ratio: float 0-1, feedback: str)
    """
    if not user_answer or not user_answer.strip():
        return False, 0.0, 'No answer provided.'

    norm_user  = _sa_normalize(user_answer)
    norm_model = _sa_normalize(model_answer)

    # -- Exact match after normalisation -------------------------
    if norm_user == norm_model:
        return True, 1.0, 'Correct.'

    user_toks  = _sa_tokens(user_answer)
    model_toks = _sa_tokens(model_answer)

    # -- Negation mismatch detection ------------------------------
    all_user_words  = set(_sa_normalize(user_answer).split())
    all_model_words = set(_sa_normalize(model_answer).split())
    user_negs  = bool(all_user_words  & _SA_NEGATIONS)
    model_negs = bool(all_model_words & _SA_NEGATIONS)
    negation_penalty = 0.35 if user_negs != model_negs else 1.0

    # -- Jaccard on expanded+stemmed token sets -------------------
    user_exp  = _expand(set(user_toks))
    model_exp = _expand(set(model_toks))
    if user_exp or model_exp:
        jac = len(user_exp & model_exp) / len(user_exp | model_exp)
    else:
        jac = 1.0

    # -- Keyword coverage -----------------------------------------
    if keywords:
        matched_kws = sum(1 for kw in keywords if _kw_match(kw, norm_user))
        kw_score = matched_kws / len(keywords)
        w_jac, w_kw, w_lev, w_ord = 0.40, 0.30, 0.20, 0.10
    else:
        kw_score = 0.0
        w_jac, w_kw, w_lev, w_ord = 0.55, 0.00, 0.30, 0.15

    # -- Levenshtein on full normalised strings -------------------
    lev = _lev_ratio(norm_user, norm_model)

    # -- Token ordering bonus (LCS ratio) -------------------------
    def lcs_ratio(a, b):
        m, n = len(a), len(b)
        if not m or not n:
            return 0.0
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                dp[i][j] = dp[i-1][j-1] + 1 if a[i-1] == b[j-1] else max(dp[i-1][j], dp[i][j-1])
        return dp[m][n] / max(m, n)

    ord_score = lcs_ratio(user_toks, model_toks)

    composite = (jac * w_jac + kw_score * w_kw + lev * w_lev + ord_score * w_ord) * negation_penalty

    is_correct = composite >= min_ratio

    if composite >= 0.90:
        feedback = 'Excellent answer.'
    elif composite >= min_ratio:
        feedback = 'Correct.'
    elif composite >= min_ratio * 0.70:
        feedback = 'Partially correct — some key ideas are missing or misworded.'
    else:
        feedback = 'Incorrect.'

    return is_correct, round(composite, 3), feedback


# -- App setup ----------------------------------------------------------
app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

def gen_id():
    return str(uuid.uuid4())

# =====================================================================
#  MODELS
# =====================================================================

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50), default='')
    last_name = db.Column(db.String(50), default='')
    is_admin = db.Column(db.Boolean, default=False)
    is_teacher = db.Column(db.Boolean, default=False)
    is_hod = db.Column(db.Boolean, default=False)
    is_super_admin = db.Column(db.Boolean, default=False)
    is_blocked = db.Column(db.Boolean, default=False)
    grade = db.Column(db.Integer, nullable=True)
    profile_pic = db.Column(db.String(400), default='')
    # Educator-team fields ------------------------------------------------
    school_name = db.Column(db.String(200), default='')
    school_district = db.Column(db.String(200), default='')
    province = db.Column(db.String(50), default='')
    town = db.Column(db.String(120), default='')
    suburb = db.Column(db.String(120), default='')
    # Comma-separated list of subjects the teacher teaches (max 4 enforced at signup)
    subjects = db.Column(db.String(400), default='')
    # FK to the HOD this teacher belongs to (null for HODs themselves and
    # for teachers not yet linked to any HOD).
    hod_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    # An individual paid teacher subscription must be active for an HOD to
    # add the teacher to their team. Toggled by an admin (no billing yet).
    subscription_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)
    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

class Grade(db.Model):
    __tablename__ = 'grades'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    number = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, default='')


# =====================================================================
#  TEACHER MODELS
# =====================================================================
class TeacherDocument(db.Model):
    """Past papers, data files and memos uploaded for teachers to download."""
    __tablename__ = 'teacher_documents'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    grade = db.Column(db.Integer, nullable=True)             # 10/11/12 or null = general
    subject = db.Column(db.String(100), default='CAT')       # CAT / IT / etc
    paper_year = db.Column(db.Integer, nullable=True)
    paper_type = db.Column(db.String(40), default='past_paper')  # past_paper | memo | data_files | other
    paper_number = db.Column(db.String(10), default='')      # '1' or '2' (optional)
    file_path = db.Column(db.String(400), nullable=False)    # relative to static/
    file_size = db.Column(db.Integer, default=0)
    uploaded_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    download_count = db.Column(db.Integer, default=0)


class QuestionBankItem(db.Model):
    """Reusable bank of questions teachers can pull into generated papers."""
    __tablename__ = 'question_bank_items'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    owner_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    grade = db.Column(db.Integer, default=12)
    subject = db.Column(db.String(120), default='')         # e.g. "Mathematics"
    topic = db.Column(db.String(120), default='')           # e.g. "Spreadsheets"
    subtopic = db.Column(db.String(120), default='')        # e.g. "VLOOKUP"
    difficulty = db.Column(db.String(20), default='medium') # easy | medium | hard
    question_type = db.Column(db.String(40), default='short_answer')  # short_answer | mcq | structured | practical
    question_text = db.Column(db.Text, nullable=False)
    answer_text = db.Column(db.Text, default='')            # memo / model answer
    marks = db.Column(db.Integer, default=1)
    tags = db.Column(db.String(300), default='')            # comma list
    image_path = db.Column(db.String(400), default='')      # optional figure (relative to static/)
    image_width = db.Column(db.Integer, default=0)          # rendered figure width as percent (10-100); 0 = default
    image_offset = db.Column(db.Integer, default=0)         # horizontal offset as percent of parent (-50..+50); 0 = default left-align
    is_shared = db.Column(db.Boolean, default=False)        # legacy: True == public (mirrors share_scope='public')
    # Visibility scope: 'private' (owner only), 'school' (owner + same-school teachers),
    # 'public' (all teachers/HODs). Defaults to private.
    share_scope = db.Column(db.String(20), default='private')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class GeneratedPaper(db.Model):
    """A composed exam paper (with header info and selected questions)."""
    __tablename__ = 'generated_papers'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    owner_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), default='Examination Paper')
    school_name = db.Column(db.String(200), default='')
    subject = db.Column(db.String(100), default='Computer Applications Technology')
    grade = db.Column(db.Integer, default=12)
    exam_date = db.Column(db.Date, nullable=True)
    duration_minutes = db.Column(db.Integer, default=180)
    total_marks = db.Column(db.Integer, default=150)
    examiner = db.Column(db.String(120), default='')
    moderator = db.Column(db.String(120), default='')
    instructions = db.Column(db.Text, default='')
    # JSON-encoded list of {name, type} objects describing the data
    # files that accompany the paper (e.g. CAT P1 "list of files in the
    # folder" page that follows the INSTRUCTIONS page in the official
    # DBE PDF). Empty string when not applicable.
    data_files = db.Column(db.Text, default='')
    logo_path = db.Column(db.String(400), default='')       # relative to static/
    # Customisable cover / header / footer strings (DBE defaults applied in template if blank)
    paper_number = db.Column(db.String(10), default='')           # e.g. '1' or '2'  (auto from title if blank)
    cover_authority = db.Column(db.Text, default='')              # default: "SENIOR CERTIFICATE EXAMINATIONS/\nNATIONAL SENIOR CERTIFICATE EXAMINATIONS"
    cover_subtitle = db.Column(db.String(200), default='')        # default: "Confidential" (paper) or "MARKING GUIDELINES" (memo)
    header_left = db.Column(db.String(200), default='')           # default: "<Subject>/P<n>   <page>   DBE/<Month> <Year>"
    header_right = db.Column(db.String(200), default='')          # blank by default
    sub_header = db.Column(db.String(200), default='')            # default: "SC/NSC Confidential" / "SC/NSC — Marking Guidelines"
    footer_left = db.Column(db.String(200), default='Copyright reserved')
    footer_center = db.Column(db.String(200), default='')
    footer_right = db.Column(db.String(200), default='Please turn over')
    memo_title = db.Column(db.String(120), default='MARKING GUIDELINES')
    cover_extra_note = db.Column(db.Text, default='')             # extra free-text on cover (e.g. info-sheet note)
    sections = db.Column(db.Text, default='[]')             # JSON: [{title, instructions, question_ids:[...]}]
    # ---- Versioned snapshots (three-set workflow) ---------------------
    # Captured at workflow transitions so the owner can compare/accept.
    #   sections_original  = snapshot of `sections` taken when paper is
    #                        flagged for moderation (pre-moderator edits).
    #   sections_moderated = snapshot of `sections` taken at moderator
    #                        sign-off (includes mod_* flags = green tags).
    #   sections_final     = snapshot the teacher accepted (copy of
    #                        sections_moderated at the moment of accept).
    sections_original  = db.Column(db.Text, default='')
    sections_moderated = db.Column(db.Text, default='')
    sections_final     = db.Column(db.Text, default='')
    # JSON list of prior `sections` snapshots (most-recent last). Pushed
    # before each insert/replace/delete edit in the preview, so the
    # teacher can press Undo to roll back. Capped at ~20 entries.
    sections_undo_stack = db.Column(db.Text, default='')
    # Snapshot of the top-level paper fields (title, duration, marks,
    # instructions, etc.) taken at flag time. Used to diff against the
    # moderator's current values and produce the "old → new" highlight.
    header_original    = db.Column(db.Text, default='')
    # JSON map: {field: {'old': ..., 'new': ...}} for top-level fields the
    # moderator changed. Drives the strikethrough+green render.
    moderator_overrides = db.Column(db.Text, default='')
    # ---- Moderation workflow (HOD sign-off) ----------------------------
    # 'draft' (default), 'flagged' (sent to HOD for review),
    # 'signed_off' (approved, may be printed), 'rejected' (sent back).
    moderation_status = db.Column(db.String(20), default='draft')
    moderator_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    moderator_notes = db.Column(db.Text, default='')
    flagged_at = db.Column(db.DateTime, nullable=True)
    signed_off_at = db.Column(db.DateTime, nullable=True)
    # Visibility scope, mirrors QuestionBankItem.share_scope:
    #   'private' (default)  - only the owner (and admins/moderator) can see it
    #   'school'             - colleagues at the same school can see it
    #   'public'             - any teacher/HOD can see it
    share_scope = db.Column(db.String(20), default='private')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # JSON map keyed by a stable element path → {html: '...', deleted: bool}.
    # Populated by the in-preview WYSIWYG editor (Bold, Italics, font-size,
    # delete-line) and reapplied client-side on every render so the user's
    # hand-edits survive page reloads.
    preview_overrides = db.Column(db.Text, default='')
    # Unified UNDO history for the in-preview editor. JSON list (most-recent
    # last) of typed records describing how to revert the LAST edit of ANY
    # kind: text override, figure width/offset/crop/replace, page-break, or a
    # structural insert. Each record stores the PRIOR state so a single Undo
    # rolls it back. Capped at ~60 entries.
    edit_history = db.Column(db.Text, default='')
    # True for the seeded/imported official DBE library papers (2021-2025
    # past papers). These are protected from deletion so the shared
    # library can't be wiped. Papers created via "Add new paper" default
    # to False and can be deleted by their owner.
    is_library = db.Column(db.Boolean, default=False)


class TeacherSchedule(db.Model):
    """Year planner / schedule entries for teachers."""
    __tablename__ = 'teacher_schedules'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    owner_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    grade = db.Column(db.Integer, nullable=True)
    kind = db.Column(db.String(30), default='lesson')       # lesson | quiz | exam | event | task
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    term = db.Column(db.Integer, nullable=True)             # 1-4
    color = db.Column(db.String(20), default='#0078D4')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class InstructionTemplate(db.Model):
    """Reusable instructions a teacher can save and pick when building a paper."""
    __tablename__ = 'instruction_templates'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    owner_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, uid)

@app.template_filter('from_json')
def from_json_filter(s):
    try: return json.loads(s)
    except: return s

@app.template_filter('regex_replace')
def regex_replace_filter(s, pattern, repl=''):
    """Jinja filter: re.sub(pattern, repl, s)."""
    import re as _re
    if s is None:
        return ''
    try:
        return _re.sub(pattern, repl, str(s))
    except _re.error:
        return s

@app.template_filter('regex_search')
def regex_search_filter(s, pattern):
    """Jinja filter: re.search(pattern, s) -> list[str] of (full match, *groups) or None."""
    import re as _re
    if s is None:
        return None
    try:
        m = _re.search(pattern, str(s))
        if not m:
            return None
        return [m.group(0)] + list(m.groups())
    except _re.error:
        return None

@app.template_filter('bullets_to_html')
def _bullets_to_html_decorated(s):
    """Render text via `bullets_to_html_filter`, but preserve raw
    `<table>...</table>` blocks verbatim (so authors can embed example
    tables inside question bodies / outros) and post-process inline
    `**bold**` markers."""
    import re as _re
    from markupsafe import Markup as _Mk
    if s is None:
        return _Mk('')
    src = str(s)
    # ── Plain-text authoring conventions (editor-friendly) ────────────────
    # [BOX] … [/BOX] paragraphs render as a DBE bordered scenario box. The
    # first line renders centred+bold when it is an ALL-CAPS title. This
    # keeps the editor textarea free of raw HTML.
    from markupsafe import escape as _esc
    def _box_repl(_m):
        centred = bool((_m.group(1) or '').strip())
        inner = _m.group(2).strip()
        paras = [p.strip() for p in _re.split(r'\n\s*\n', inner) if p.strip()]
        rows = ''
        for _i, _p in enumerate(paras):
            one = ' '.join(_p.split())
            is_title = (_i == 0 and len(paras) > 1 and one == one.upper()
                        and len(one) < 70)
            if is_title:
                style = ('border:none; padding:2px 12px; text-align:center; '
                         'font-weight:bold; padding-top:6px;')
            else:
                align = 'center' if centred else 'justify'
                style = (f'border:none; padding:2px 12px; text-align:{align};'
                         + (' padding-bottom:8px;' if _i == len(paras) - 1 else ''))
            rows += f'<tr><td style="{style}">{_esc(one)}</td></tr>'
        width = '88%' if centred else '100%'
        margin = '10px auto 4px' if centred else '6px 0'
        return (f'<table style="border:1.5px solid #000; '
                f'border-collapse:collapse; width:{width}; margin:{margin};">'
                + rows + '</table>')
    src = _re.sub(r'\[BOX( centre| center)?\]([\s\S]*?)\[/BOX\]', _box_repl, src,
                  flags=_re.IGNORECASE)
    # Nested bullet lists: "- item" with "o sub-item" lines render as a
    # disc list with circle sub-items.
    def _nested_block(_m):
        lines = [l for l in _m.group(0).splitlines() if l.strip()]
        html = '<ul style="margin:6px 0 0 26px; padding:0; list-style:disc;">'
        li_open = False
        sub_open = False
        for ln in lines:
            t = ln.strip()
            if t.startswith('- '):
                if sub_open:
                    html += '</ul>'
                    sub_open = False
                if li_open:
                    html += '</li>'
                html += f'<li style="margin:2px 0;">{_esc(t[2:])}'
                li_open = True
            elif t.startswith('o ') and li_open:
                if not sub_open:
                    html += ('<ul style="margin:2px 0 0 22px; padding:0; '
                             'list-style:circle;">')
                    sub_open = True
                html += f'<li style="margin:2px 0;">{_esc(t[2:])}</li>'
        if sub_open:
            html += '</ul>'
        if li_open:
            html += '</li>'
        return html + '</ul>'
    # Only convert bullet runs that CONTAIN an "o " sub-line (plain "- "
    # lists keep the legacy hanging-bullet renderer).
    src = _re.sub(
        r'(?:^[ \t]*- [^\n]*\n?(?:[ \t]*(?:- |o )[^\n]*\n?)*)',
        lambda m: (_nested_block(m) if _re.search(r'^[ \t]*o ', m.group(0), _re.M)
                   else m.group(0)),
        src, flags=_re.M)
    # Pull out raw <table>…</table> and <ul>…</ul> blocks before the
    # (escape-heavy) bullets renderer mangles them.
    _placeholders = []
    def _stash(_m):
        _placeholders.append(_m.group(0))
        return f"\x00TBL{len(_placeholders)-1}\x00"
    src_stashed = _re.sub(
        r'<table\b[\s\S]*?</table>', _stash, src, flags=_re.IGNORECASE)
    src_stashed = _re.sub(
        r'<ul\b[\s\S]*</ul>', _stash, src_stashed, flags=_re.IGNORECASE)
    out = bullets_to_html_filter(src_stashed)
    s2 = str(out)
    # Restore tables.
    for i, tbl in enumerate(_placeholders):
        s2 = s2.replace(f"\x00TBL{i}\x00", tbl)
    # Inline bold: **text** -> <strong>text</strong>
    try:
        s2 = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s2, flags=_re.DOTALL)
    except Exception:
        pass
    return _Mk(s2)


@app.template_filter('memo_flow_body')
def memo_flow_body_filter(s):
    """Render a Business Studies-style flowing marking-guideline answer.

    Line conventions (kept readable in the editor):
      **text**        bold (headings, NOTE lines)
      - text          hanging hyphen bullet (DBE style)
      o text          hollow sub-bullet, indented
      >> token        right-aligned bold mark token, e.g. ">> (4 x 1) (4)"
      raw <table>     rendered verbatim
    """
    import re as _re
    from markupsafe import Markup, escape
    if not s:
        return Markup('')
    text = str(s).replace('\r', '')
    stash = []
    def _st(m):
        stash.append(m.group(0))
        return f'\x00T{len(stash)-1}\x00'
    text = _re.sub(r'<table\b[\s\S]*?</table>', _st, text, flags=_re.I)
    out = []
    for raw in text.split('\n'):
        ln = raw.strip()
        if not ln:
            continue
        if ln.startswith('\x00T'):
            out.append(ln)
            continue
        def _fmt(t):
            e = str(escape(t))
            e = _re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', e, flags=_re.S)
            return e
        if ln.startswith('>>'):
            out.append('<div class="fm-token">' + _fmt(ln[2:].strip()) + '</div>')
        elif ln.startswith('- '):
            out.append('<div class="fm-bullet"><span>-</span><span>'
                       + _fmt(ln[2:].strip()) + '</span></div>')
        elif ln.startswith('o '):
            out.append('<div class="fm-bullet fm-sub"><span>o</span><span>'
                       + _fmt(ln[2:].strip()) + '</span></div>')
        else:
            out.append('<div class="fm-p">' + _fmt(ln) + '</div>')
    html = ''.join(out)
    for i, tbl in enumerate(stash):
        html = html.replace(f'\x00T{i}\x00', tbl)
    return Markup(html)


@app.template_filter('inline_bold')
def inline_bold_filter(s):
    """Escape HTML, then convert **text** into <strong>text</strong>.

    Used by the instructions page so authors can mark inline bold spans
    (e.g. **MUST BE COMPLETED**, **CAT P1 June 2025 DATA.exe**) without
    enabling raw HTML in untrusted content.
    """
    from markupsafe import escape, Markup
    import re as _re
    if s is None:
        return Markup('')
    esc = str(escape(s))
    esc = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', esc, flags=_re.DOTALL)
    # Allow a small whitelist of inline bold/italic tags that authors may
    # have embedded directly in instruction text. Un-escape only these so
    # other HTML (script/img/etc.) remains escaped.
    for _t in ('b', 'strong', 'i', 'em'):
        esc = esc.replace(f'&lt;{_t}&gt;', f'<{_t}>').replace(f'&lt;/{_t}&gt;', f'</{_t}>')
    # Webdings glyph token: [wd:NNN] -> <span class="wd">CHR(NNN)</span>.
    # Used to embed small symbol-font glyphs (e.g. character code 209) in
    # question text rendered as the actual Webdings symbol.
    esc = _re.sub(
        r'\[wd:(\d{1,3})\]',
        lambda m: f'<span class="wd">{chr(int(m.group(1)))}</span>',
        esc,
    )
    return Markup(esc)


def _render_dual_column_compare(text, escape, Markup, _re):
    """Render an advertisement-style two-column comparison as a bordered table.

    DBE often gives a "Study the advertisement of two different X" question
    where the body is a comparison between LAPTOP A and LAPTOP B (or
    SMARTPHONE A / B, etc.). PDF extraction flattens this into one blob:

        Study the advertisement of two different laptops below and answer
        the questions that follow.

                 LAPTOP A                      LAPTOP B

         •  Upgradeable to Windows 11  •  Windows 11
         •  Office 365                 •  Office 365
         ...

    Return rendered HTML if the pattern is detected, else ``None``.
    """
    if not text or '\u2022' not in text and '\n' not in text:
        return None
    lines = [ln.rstrip() for ln in str(text).replace('\r', '').split('\n')]
    # Trim outer blank lines.
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return None
    # Find a header line: a single non-bullet line containing two ALL-CAPS
    # short phrases separated by 3+ spaces.
    bullet_glyph_re = _re.compile(r'[\u2022\u25cf\u25aa\u25e6]')
    header_re = _re.compile(
        r'^\s*([A-Z][A-Z0-9 \-]{1,30}[A-Z0-9])\s{3,}([A-Z][A-Z0-9 \-]{1,30}[A-Z0-9])\s*$'
    )
    header_idx = -1
    left_label = right_label = ''
    intro_lines = []
    for i, ln in enumerate(lines):
        if bullet_glyph_re.search(ln):
            return None  # bullet before any header — not the right shape
        m = header_re.match(ln)
        if m:
            header_idx = i
            left_label = m.group(1).strip()
            right_label = m.group(2).strip()
            intro_lines = lines[:i]
            break
        intro_lines.append(ln)
    if header_idx < 0:
        return None
    # Now read rows: each line after the header must split into exactly two
    # bullet items (split on the SECOND bullet marker).
    row_lines = [ln for ln in lines[header_idx + 1:] if ln.strip()]
    if len(row_lines) < 2:
        return None
    bullets_re = _re.compile(r'[\u2022\u25cf\u25aa\u25e6]\s*')
    rows = []
    for ln in row_lines:
        parts = bullets_re.split(ln)
        # parts[0] is text before the first bullet (whitespace); we want
        # parts[1] and parts[2] (left and right bullet bodies).
        cleaned = [p.strip() for p in parts if p.strip()]
        if len(cleaned) != 2:
            return None
        rows.append((cleaned[0], cleaned[1]))
    # Build HTML.
    parts = []
    intro = ' '.join(l.strip() for l in intro_lines if l.strip())
    if intro:
        parts.append('<span class="ln">' + str(escape(intro)) + '</span>')
    parts.append('<table class="cmp-tbl"><thead><tr>')
    parts.append('<th>' + str(escape(left_label)) + '</th>')
    parts.append('<th>' + str(escape(right_label)) + '</th>')
    parts.append('</tr></thead><tbody>')
    for left, right in rows:
        parts.append(
            '<tr><td><span class="cmp-bullet">\u2022</span>'
            + str(escape(left)) + '</td>'
            + '<td><span class="cmp-bullet">\u2022</span>'
            + str(escape(right)) + '</td></tr>'
        )
    parts.append('</tbody></table>')
    return Markup(''.join(parts))


def _render_matching_items(text, escape, Markup, _re):
    """Render DBE-style MATCHING ITEMS questions as two side-by-side columns.

    PDF extraction interleaves the two columns onto the same physical lines
    with inconsistent spacing, e.g.:

        2.1    A wired internet connection   A   WiMAX
        2.2    A device that connects computers in B information overload
               a network to the internet
                                             C   section break
        2.3    Splits the pages in a word processing
               document to be formatted differently D drone

    Strategy: walk line-by-line tracking the next expected left number
    ("2.1", "2.2", ...) and the next expected right letter ("A", "B", ...,
    "T"). On each line, anything before the next expected right letter (when
    encountered as a stand-alone token) belongs to the current left item;
    anything after it starts the next right-column option.
    """
    # Trailing marks indicator like "(10 x 1)" or "(5 x 2) (10)"
    trailing_re = _re.compile(r'^\s*\(\s*\d+\s*[x×]\s*\d+\s*\)(?:\s*\(\d+\))?\s*$')
    # Bare header line: only contains "COLUMN", "A", "B", whitespace
    header_only_re = _re.compile(r'^\s*COLUMN\s+A\s+COLUMN\s+B\s*$', _re.IGNORECASE)
    header_a_re = _re.compile(r'^\s*COLUMN\s+A\s*$', _re.IGNORECASE)
    header_b_re = _re.compile(r'^\s*COLUMN\s+B\s*$', _re.IGNORECASE)
    left_start_re = _re.compile(r'^(\d+(?:\.\d+)+)\s+(.*)$')

    # Derive the expected left-item numbering from the text itself so both
    # 2-level (CAT: 2.1..2.10) and 3-level (Business Studies: 1.3.1..1.3.5)
    # papers parse. The first line-leading number AFTER the headers is the
    # base; successors share its prefix.
    _base = None
    _seen_header = False
    for _raw in text.split('\n'):
        _s = _raw.strip()
        if header_only_re.match(_s) or header_a_re.match(_s) or header_b_re.match(_s):
            _seen_header = True
            continue
        _m = left_start_re.match(_s)
        if _m and _seen_header:
            _base = _m.group(1)
            break
    if _base is None:
        _base = '2.1'
    _parts = _base.split('.')
    _prefix = '.'.join(_parts[:-1])
    _start = int(_parts[-1])
    expected_lefts = [f'{_prefix}.{_start + i}' for i in range(12)]
    left_idx = 0          # index into expected_lefts of the NEXT left item
    next_right_ord = ord('A')
    max_right_ord = ord('T')

    intro_lines = []
    left_items = []   # list of [num, desc]
    right_items = []  # list of (letter, body)
    trailing = ''
    in_table = False
    # Skip the "MATCHING ITEMS" question heading if present at the top — it's
    # the section title, not body content.
    matching_heading_re = _re.compile(r'^\s*MATCHING\s+ITEMS\s*$', _re.IGNORECASE)

    def _next_right():
        return chr(next_right_ord) if next_right_ord <= max_right_ord else None

    for raw in text.split('\n'):
        ln = raw.replace('\t', '    ')
        stripped = ln.strip()
        if not stripped:
            continue
        if trailing_re.match(stripped):
            trailing = stripped
            continue
        if matching_heading_re.match(stripped):
            continue
        if header_only_re.match(stripped) or header_a_re.match(stripped) or header_b_re.match(stripped):
            in_table = True
            continue
        # Intro paragraphs come before any numbered item
        if not in_table:
            m_left_check = left_start_re.match(stripped)
            if not m_left_check or m_left_check.group(1) != expected_lefts[0]:
                intro_lines.append(stripped)
                continue
        in_table = True

        rest = stripped
        # Detect leading "N.M" left-item marker
        m_left = left_start_re.match(rest)
        if m_left and left_idx < len(expected_lefts) and m_left.group(1) == expected_lefts[left_idx]:
            left_items.append([m_left.group(1), ''])
            left_idx += 1
            rest = m_left.group(2)

        # Find the LAST occurrence of the next expected right letter as a
        # stand-alone token. The right column is physically to the RIGHT of
        # left text, so when the same letter appears multiple times on a
        # line (e.g. "A wired internet connection   A   WiMAX") the
        # right-column marker is the rightmost one. Then continue scanning
        # the right-side chunk for further option markers in order.
        left_buf_parts = []
        tokens = rest.split()
        nr = _next_right()
        split_idx = -1
        if nr:
            for i in range(len(tokens) - 1, -1, -1):
                if tokens[i] == nr:
                    split_idx = i
                    break
        if split_idx < 0:
            left_buf_parts = tokens
        else:
            left_buf_parts = tokens[:split_idx]
            j = split_idx
            while j < len(tokens):
                cur_letter = tokens[j]
                next_ord = ord(cur_letter) + 1
                next_letter = chr(next_ord) if next_ord <= max_right_ord else None
                end_idx = len(tokens)
                if next_letter:
                    for k in range(len(tokens) - 1, j, -1):
                        if tokens[k] == next_letter:
                            end_idx = k
                            break
                body = ' '.join(tokens[j + 1:end_idx]).strip()
                if body:
                    right_items.append((cur_letter, body))
                    next_right_ord = ord(cur_letter) + 1
                j = end_idx

        if left_buf_parts and left_items:
            text_part = ' '.join(left_buf_parts)
            if left_items[-1][1]:
                left_items[-1][1] += ' ' + text_part
            else:
                left_items[-1][1] = text_part
        elif left_buf_parts and not left_items:
            # Stray text before any left item — treat as intro
            intro_lines.append(' '.join(left_buf_parts))

    # Build HTML — emit a real <table class="match-tbl"> identical in
    # structure to the one rendered by paper_print.html for properly
    # split match_table runs, so styling (borders, columns, header row)
    # is uniform across both code paths.
    intro_html = ''
    if intro_lines:
        intro_html = f'<div class="mi-intro">{escape(" ".join(intro_lines))}</div>'

    rows_n = len(left_items)
    opts_n = len(right_items)

    body_rows = []
    if rows_n > 0 and opts_n >= rows_n:
        # Distribute Column B options across Column A rows. Each Column A
        # cell spans `span` Column B rows (typically 2 when opts_n == 2 *
        # rows_n, as in DBE Q2 with 10 questions and 20 options A–T). Any
        # extra options that don't fit cleanly land in a final merged
        # blank Column A cell.
        span = opts_n // rows_n
        remainder = opts_n - span * rows_n
        opt_idx = 0
        for r in range(rows_n):
            for s in range(span):
                cells = ['<tr>']
                if s == 0:
                    num, desc = left_items[r]
                    cells.append(f'<td class="ma-num" rowspan="{span}">{escape(num)}</td>')
                    cells.append(f'<td class="ma-desc" rowspan="{span}">{escape(desc)}</td>')
                if opt_idx < opts_n:
                    letter, body = right_items[opt_idx]
                    cells.append(f'<td class="mb-letter">{escape(letter)}</td>')
                    cells.append(f'<td class="mb-term">{escape(body)}</td>')
                    opt_idx += 1
                else:
                    cells.append('<td class="mb-letter"></td><td class="mb-term"></td>')
                cells.append('</tr>')
                body_rows.append(''.join(cells))
        # Tail options with no matching Column A row — single merged blank
        if remainder > 0:
            for i in range(remainder):
                cells = ['<tr>']
                if i == 0:
                    cells.append(f'<td class="ma-blank" colspan="2" rowspan="{remainder}"></td>')
                letter, body = right_items[opt_idx]
                cells.append(f'<td class="mb-letter">{escape(letter)}</td>')
                cells.append(f'<td class="mb-term">{escape(body)}</td>')
                opt_idx += 1
                cells.append('</tr>')
                body_rows.append(''.join(cells))
    else:
        # Fallback: pair-by-row, with leftover rows on whichever side is longer.
        max_rows = rows_n if rows_n > opts_n else opts_n
        for r in range(max_rows):
            cells = ['<tr>']
            if r < rows_n:
                num, desc = left_items[r]
                cells.append(f'<td class="ma-num">{escape(num)}</td>')
                cells.append(f'<td class="ma-desc">{escape(desc)}</td>')
            else:
                cells.append('<td class="ma-num"></td><td class="ma-desc"></td>')
            if r < opts_n:
                letter, body = right_items[r]
                cells.append(f'<td class="mb-letter">{escape(letter)}</td>')
                cells.append(f'<td class="mb-term">{escape(body)}</td>')
            else:
                cells.append('<td class="mb-letter"></td><td class="mb-term"></td>')
            cells.append('</tr>')
            body_rows.append(''.join(cells))

    trailing_html = ''
    if trailing:
        trailing_html = f'<div class="match-marks">{escape(trailing)}</div>'

    html = (
        f'{intro_html}'
        f'<div class="match-block">'
        f'<table class="match-tbl">'
        f'<thead><tr>'
        f'<th colspan="2">COLUMN A</th>'
        f'<th colspan="2">COLUMN B</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        f'</table>'
        f'{trailing_html}'
        f'</div>'
    )
    return Markup(html)


def bullets_to_html_filter(s):
    """Render multi-line DBE-style instruction text as a clean block.

    - Bullet glyphs (•, *, -, o) become hanging-indent grid rows whose
      wrapped lines align under the bullet text, not the bullet glyph.
    - Soft-wrapped continuation lines from the PDF are merged into their
      bullet/paragraph with a single space (so "are\\n   correct" reads as
      "are correct").
    - Blank lines in the source create a paragraph gap, except when the
      next non-blank line is a lowercase wrap-continuation of the
      preceding bullet (PDF columns sometimes inject a stray blank).
    - Leading "NOTE:" / "HINT:" / "TIP:" labels render bold.
    """
    from markupsafe import Markup, escape
    import re as _re
    if not s:
        return Markup('')
    text = str(s).replace('\r', '')

    # ── Matching-items renderer (DBE Q2 style) ────────────────────────────
    # Only activate when the text is clearly a DBE-style matching-items
    # question (contains both COLUMN A / COLUMN B headers AND the (N x 1)
    # mark indicator). Plain spreadsheet questions that just mention
    # "column A" should NOT trigger this.
    _u = ' '.join(text.upper().split())
    if (
        'COLUMN A' in _u and 'COLUMN B' in _u
        and _re.search(r'\(\s*\d+\s*[X×]\s*\d+\s*\)', _u)
        and _re.search(r'\b\d+(?:\.\d+)+\b', _u)
    ):
        return _render_matching_items(text, escape, Markup, _re)

    # ── Dual-column comparison table (e.g. "LAPTOP A | LAPTOP B" ad) ──────
    # Detect when the text has a centred two-label header (two ALL-CAPS short
    # phrases separated by 3+ spaces) followed by lines that each contain
    # exactly two bullet markers. Render as a 2-col bordered comparison
    # table with the labels in the head row.
    _dc = _render_dual_column_compare(text, escape, Markup, _re)
    if _dc is not None:
        return _dc

    bullet_re = _re.compile(
        r'^\s*(?:[\u2022\u25cf\u25aa\u25e6\*\-\u2013\u2014]|o(?=\s))\s+(.*)$'
    )
    # MCQ-style option lines: "A   Backup", "B  e-Filing", etc.
    # Captures the letter and the option body so we can render aligned columns.
    # We require multiple spaces (≥2) or a delimiter (.|)) after the letter so
    # ordinary stems beginning with "A computer..." don't get mis-detected as
    # an option.
    mcq_re = _re.compile(r'^\s*([A-D])(?:\s{2,}|[\.\)]\s+)(.+?)\s*$')
    # Inline split: when PDF extraction joins multiple options onto one line
    # ("B  Processing  C  Communication  D  Storage"), break before B/C/D so each
    # becomes its own option line. Require ≥2 spaces around the marker so we
    # don't split mid-sentence.
    mcq_inline_split_re = _re.compile(r'(?<=\s)(?=[B-D]\s{2,}\S)')
    lines = text.split('\n')
    # Pre-process: if a line begins with "A ..." and contains additional
    # " B  ", " C  ", " D  " markers, split it into separate lines.
    expanded = []
    for ln in lines:
        if mcq_re.match(ln):
            parts_split = mcq_inline_split_re.split(ln)
            if len(parts_split) > 1 and all(mcq_re.match(p) for p in parts_split):
                indent = ln[:len(ln) - len(ln.lstrip())]
                expanded.append(parts_split[0])
                for p in parts_split[1:]:
                    expanded.append(indent + p.lstrip())
                continue
        expanded.append(ln)
    lines = expanded
    # Only enable mcq parsing if at least two distinct option letters appear
    # at line starts (so a normal stem starting with "A computer" isn't
    # misclassified when there are no real B/C/D siblings).
    _seen_letters = set()
    for ln in lines:
        m_chk = mcq_re.match(ln)
        if m_chk:
            _seen_letters.add(m_chk.group(1))
    mcq_enabled = len(_seen_letters) >= 2
    blocks = []  # ('bullet', body) | ('para', body) | ('break',)

    def _peek_nonblank(idx):
        j = idx
        while j < len(lines) and lines[j].strip() == '':
            j += 1
        return (j, lines[j] if j < len(lines) else None)

    i = 0
    while i < len(lines):
        ln = lines[i]
        m = bullet_re.match(ln)
        mcq_m = None if (m or not mcq_enabled) else mcq_re.match(ln)
        if m:
            body = m.group(1).strip()
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt.strip() == '':
                    # Look ahead — only merge across the blank if the next
                    # non-blank line is clearly a wrap-continuation
                    # (lowercase first char) and not another bullet.
                    k, peek = _peek_nonblank(j + 1)
                    if peek is None:
                        break
                    if bullet_re.match(peek) or (mcq_enabled and mcq_re.match(peek)):
                        break
                    first = peek.lstrip()[:1]
                    if first and first.islower():
                        body += ' ' + peek.strip()
                        j = k + 1
                        continue
                    break
                if bullet_re.match(nxt) or (mcq_enabled and mcq_re.match(nxt)):
                    break
                body += ' ' + nxt.strip()
                j += 1
            blocks.append(('bullet', body))
            i = j
        elif mcq_m:
            letter = mcq_m.group(1)
            body = mcq_m.group(2).strip()
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt.strip() == '' or bullet_re.match(nxt) or (mcq_enabled and mcq_re.match(nxt)):
                    break
                body += ' ' + nxt.strip()
                j += 1
            blocks.append(('mcq', letter, body))
            i = j
        elif ln.strip() == '':
            blocks.append(('break',))
            i += 1
        else:
            para = ln.strip()
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt.strip() == '' or bullet_re.match(nxt) or (mcq_enabled and mcq_re.match(nxt)):
                    break
                para += ' ' + nxt.strip()
                j += 1
            blocks.append(('para', para))
            i = j

    # Trim leading/trailing/consecutive breaks.
    out = []
    for b in blocks:
        if b[0] == 'break':
            if out and out[-1][0] != 'break':
                out.append(b)
        else:
            out.append(b)
    while out and out[-1][0] == 'break':
        out.pop()

    # Dedupe repeated NOTE/HINT/TIP/NB blocks. Auto-filled instructions
    # plus PDF-imported text can contain the same NOTE block twice (once
    # at the end of the preset and once peeled off the trailing question
    # body); render each unique NOTE run only once.
    #
    # ALSO: auto-strip the standard DBE TF NOTE block — i.e. a NOTE run
    # whose bullets contain "Do NOT simply use the word 'NOT'" and/or the
    # "FALSE … written/provided as an answer" guidance — when the
    # surrounding paragraph already contains the TRUE/FALSE intro
    # ("indicate … true or false"). This keeps the q-intro from showing
    # the same instruction twice (once inline + once as a NOTE block).
    _note_lead_re = _re.compile(r'^\s*(NOTES?:|HINT:|TIP:|NB:)', _re.IGNORECASE)
    _tf_intro_re = _re.compile(r'true\s+or\s+false', _re.IGNORECASE)
    _tf_dup_bullet_re = _re.compile(
        r"do\s+not\s+simply\s+use|only\s+false\s+is\s+(?:written|provided)",
        _re.IGNORECASE,
    )
    # Detect whether any non-NOTE paragraph already carries the TF intro.
    _has_tf_intro_inline = any(
        b[0] in ('para',) and not _note_lead_re.match(b[1] or '')
        and _tf_intro_re.search(b[1] or '')
        for b in out
    )
    _seen_note_runs = set()
    _deduped = []
    _i = 0
    while _i < len(out):
        _b = out[_i]
        if _b[0] == 'para' and _note_lead_re.match(_b[1] or ''):
            _j = _i + 1
            _run = [_b]
            while _j < len(out) and out[_j][0] in ('bullet', 'break'):
                _run.append(out[_j])
                _j += 1
            # Strip trailing breaks from the run before keying / emitting.
            while _run and _run[-1][0] == 'break':
                _run.pop()
            # Auto-suppress the TF NOTE if the inline intro is already there.
            if _has_tf_intro_inline and any(
                x[0] == 'bullet' and _tf_dup_bullet_re.search(x[1] or '')
                for x in _run
            ):
                # Drop the trailing break that originally separated this
                # NOTE from the following content too.
                while _i + (_j - _i) < len(out) and out[_j][0] == 'break':
                    _j += 1
                _i = _j
                continue
            _key = tuple(
                (x[0],) + tuple(s.strip().lower() for s in x[1:])
                for x in _run
            )
            if _key in _seen_note_runs:
                _i = _j
                continue
            _seen_note_runs.add(_key)
            # Re-insert a single break before the NOTE if the previous kept
            # block isn't already a break (keeps visual spacing).
            if _deduped and _deduped[-1][0] != 'break':
                _deduped.append(('break',))
            _deduped.extend(_run)
            _i = _j
        else:
            _deduped.append(_b)
            _i += 1
    # Collapse any consecutive breaks introduced by dedup, and trim trailing.
    _collapsed = []
    for _b in _deduped:
        if _b[0] == 'break' and _collapsed and _collapsed[-1][0] == 'break':
            continue
        _collapsed.append(_b)
    while _collapsed and _collapsed[-1][0] == 'break':
        _collapsed.pop()
    out = _collapsed

    label_re = _re.compile(r'^(NOTES?:|HINT:|TIP:|NB:)')
    trail_marks_re = _re.compile(r'\s*\((\d{1,3})\)\s*$')
    # Inline-underline marker: __word or phrase__ → <u>…</u>. Applied
    # AFTER HTML-escaping so it's safe (the underscores survive escape).
    _u_marker_re = _re.compile(r'__([^_\n]{1,80}?)__')
    # Inline Webdings-cat marker (DBE Q1.11 May/June 2024): [[CAT]] →
    # small inline SVG silhouette so we render the same glyph the PDF
    # shows (Webdings character code 246) without depending on the
    # Webdings font being installed.
    _cat_svg = (
        '<img class="inline-webdings" '
        'src="/static/images/memo/webdings_cat.svg" '
        'alt="cat" style="height:1em;vertical-align:-0.18em;">'
    )
    # Inline Webdings-car marker (DBE Q2.4 November 2023): [[CAR]] →
    # small inline SVG sedan so we render the same glyph the PDF shows
    # (Webdings character code 142) without depending on the font.
    _car_svg = (
        '<img class="inline-webdings" '
        'src="/static/images/memo/webdings_car.svg" '
        'alt="car" style="height:0.9em;vertical-align:-0.1em;">'
    )
    # Inline 2-column contact-number / format table marker
    # (DBE Q4.4 May/June 2024): [[CONTACT_TBL]] → small bordered
    # table with two rows of phone numbers.
    _contact_tbl_html = (
        '<table class="inline-contact-tbl">'
        '<thead><tr><th>Contact number</th><th>Format</th></tr></thead>'
        '<tbody>'
        '<tr><td>0871522635</td><td>+27&nbsp;&nbsp;871522635</td></tr>'
        '<tr><td>0729237425</td><td>+27&nbsp;&nbsp;729237425</td></tr>'
        '</tbody></table>'
    )
    # Facilities-symbols legend (DBE CAT P1 May/June 2023 Q4): the bordered
    # icon table printed under the Q4 intro. Rendered from the cropped PDF
    # figure so the exact paw/spa/gym/Wi-Fi/pool glyphs match the original
    # verbatim (the previous Webdings glyphs did not render correctly).
    _q4_facilities_html = (
        '<span class="inline-facilities-img" '
        'style="display:block;margin:8px 0 4px;">'
        '<img src="/static/uploads/cat_p1_mj23/q4_facilities_v2.png" '
        'alt="Facilities symbols legend" '
        'style="display:block;width:64%;height:auto;">'
        '</span>'
    )
    # Registration entry form box (DBE Q10.1 November 2023) — numbered
    # fields with blank fill-lines plus a small Grade table for item 5.
    _entry_form_html = (
        '<span class="entry-form">'
        '<ol class="entry-form-list">'
        '<li>Team name <span class="ef-blank" style="width:240px"></span></li>'
        '<li>Car weight<span class="ef-blank" style="width:320px"></span></li>'
        '<li>Number of drivers <span class="ef-blank" style="width:230px"></span></li>'
        '<li>Do you have a disabled team member? Yes/No</li>'
        '<li><table class="ef-grade-tbl">'
        '<tr><td>Grade</td><td>8</td><td>9</td><td>10</td><td>11</td><td>12</td></tr>'
        '<tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>'
        '</table></li>'
        '</ol>'
        '</span>'
    )
    # Questionnaire-suitability table (DBE CAT P2 May/June 2022 Q6.1) — a
    # 4-column table with numbered headers and two prefilled question rows;
    # columns 3 and 4 are left blank for the candidate to complete.
    _q61_table_html = (
        '<table class="q61-tbl">'
        '<thead><tr>'
        '<th><span class="q61-num">1</span>Question<br>number</th>'
        '<th><span class="q61-num">2</span>Question</th>'
        '<th><span class="q61-num">3</span>Suitable/<br>Unsuitable</th>'
        '<th><span class="q61-num">4</span>Motivation</th>'
        '</tr></thead>'
        '<tbody>'
        '<tr><td>Question 1</td><td>What are the benefits of cloud computing?</td><td></td><td></td></tr>'
        '<tr><td>Question 2</td><td>Do you store your data in the cloud?</td><td></td><td></td></tr>'
        '</tbody></table>'
    )
    # News-article extract box (DBE CAT P2 May/June 2022 Q6.2) — the framed
    # source extract candidates evaluate for trustworthiness/accuracy.
    _q62_extract_html = (
        '<span class="extract-frame">'
        '<span class="ex-line">Cape Town University Press</span>'
        '<span class="ex-line">Giant Elon Musk rocket is about to CRASH into the Moon after '
        "'7 years of chaos'</span>"
        '<span class="ex-line">Harry Pettit, Deputy Technology and Science Editor</span>'
        '<span class="ex-line">14:15, 25 Jan 2022&nbsp;&nbsp;&nbsp;&nbsp;Updated: 17:01, 25 Jan 2022</span>'
        '<span class="ex-line">A FOUR-TONNE chunk of a SpaceX is on a collision course with the Moon, '
        'according to online space junk trackers.</span>'
        '<span class="ex-line">The out-of-control booster was launched from Florida in February 2015 '
        "as part of the rocket firm's first interplanetary mission.</span>"
        '</span>'
    )
    # Database-design table (DBE CAT P2 May/June 2022 Q8.3) — 3-column
    # table listing field name / data type / optional description for the
    # student-record table candidates study.
    _q83_table_html = (
        '<table class="q83-tbl">'
        '<thead><tr>'
        '<th>Field Name</th><th>Data Type</th><th>Description (Optional)</th>'
        '</tr></thead>'
        '<tbody>'
        '<tr><td>sName</td><td>Short Text</td><td>Name of student</td></tr>'
        '<tr><td>sSurname</td><td>Short Text</td><td>Surname of student</td></tr>'
        '<tr><td>SA_ID</td><td>Short Text</td><td>South African ID</td></tr>'
        '<tr><td>Gender</td><td>Short Text</td><td>Male or Female</td></tr>'
        '<tr><td>Age</td><td>Number</td><td>Age in current year</td></tr>'
        '<tr><td>School</td><td>Short Text</td><td>Name of school</td></tr>'
        '</tbody></table>'
    )
    # HTML-editor code box (DBE CAT P2 May/June 2022 Q8.7) — the source
    # markup candidates illustrate the rendered output for. Tags are
    # pre-escaped (&lt;/&gt;) because _apply_inline injects this AFTER the
    # HTML-escape pass, so literal angle brackets must already be entities.
    _q87_code_html = (
        '<span class="code-box">'
        '&lt;html&gt;<br>'
        '&lt;body&gt;<br>'
        '<br>'
        '&lt;h1&gt;Shopping List&lt;/h1&gt;<br>'
        '<br>'
        '&lt;ul&gt;<br>'
        '&lt;li&gt;Butter&lt;/li&gt;<br>'
        '&lt;li&gt;Eggs&lt;/li&gt;<br>'
        '&lt;li&gt;Flour&lt;/li&gt;<br>'
        '&lt;/ul&gt;<br>'
        '<br>'
        '&lt;ol start="20"&gt;<br>'
        '&lt;li&gt;Soap&lt;/li&gt;<br>'
        '&lt;li&gt;Shampoo&lt;/li&gt;<br>'
        '&lt;li&gt;Toothpaste&lt;/li&gt;<br>'
        '&lt;/ol&gt;<br>'
        '<br>'
        '&lt;/body&gt;<br>'
        '&lt;/html&gt;'
        '</span>'
    )
    # Computer-specifications table (DBE CAT P2 May/June 2022 Q9.1.1):
    # a 2-column table with a header spanning both columns; the missing
    # entries (a)/(b)/(c) are shown as the candidate must complete them.
    _q911_spec_html = (
        '<table class="q911-tbl">'
        '<tr><th colspan="2">Computer Specifications</th></tr>'
        '<tr><td>Monitor</td><td>17" LCD display</td></tr>'
        '<tr><td>(a) …</td><td>Celeron</td></tr>'
        '<tr><td>Storage device</td><td>(b) …</td></tr>'
        '<tr><td>(c) …</td><td>802.11</td></tr>'
        '</table>'
    )
    # HTML-editor code box with indentation (DBE CAT P2 May/June 2022
    # Q10.10). Tags are PRE-ESCAPED (&lt;/&gt;) because markers inject
    # AFTER the HTML-escape pass; leading indentation uses &nbsp; because
    # the .code-box CSS collapses ordinary whitespace. The closing
    # <title> (not </title>) is a deliberate verbatim error from the paper.
    def _ind(n):
        return '&nbsp;' * n
    _q1010_code_html = (
        '<span class="code-box">'
        '&lt;html&gt;<br>'
        '&lt;title&gt;Online Courses&lt;title&gt;<br>'
        + _ind(4) + '&lt;body&gt;<br>'
        + _ind(8) + '&lt;img src="online.jpg"/&gt;<br>'
        + _ind(8) + '&lt;h1&gt;Select a course&lt;/h1&gt;<br>'
        + _ind(8) + '&lt;table border="1"&gt;<br>'
        + _ind(11) + '&lt;tr&gt;<br>'
        + _ind(14) + '&lt;td&gt;Options&lt;/td&gt;<br>'
        + _ind(11) + '&lt;/tr&gt;<br>'
        + _ind(11) + '&lt;tr&gt;<br>'
        + _ind(14) + '&lt;td&gt;Blue&lt;/td&gt;<br>'
        + _ind(14) + '&lt;td&gt;Green&lt;/td&gt;<br>'
        + _ind(11) + '&lt;/tr&gt;<br>'
        + _ind(9) + '&lt;/table&gt;<br>'
        + _ind(8) + '&lt;/body&gt;<br>'
        '&lt;/html&gt;'
        '</span>'
    )

    # SOHO hardware/software specifications comparison table (DBE CAT P2
    # May/June 2021 Q4.1) — the header "SPECIFICATIONS TO CHOOSE BETWEEN"
    # spans the first two option columns; CHOICE and REASON follow. The
    # example row is prefilled; the candidate completes the 4.1.1–4.1.4 cells.
    _q41_table_html = (
        '<table class="q41-tbl">'
        '<thead><tr>'
        '<th colspan="2">SPECIFICATIONS TO<br>CHOOSE BETWEEN</th>'
        '<th>CHOICE</th><th>REASON</th>'
        '</tr></thead>'
        '<tbody>'
        '<tr><td>e.g.<br>19" 4:3 monitor</td><td>e.g.<br>24" 16:9 monitor</td>'
        '<td>e.g.<br>24" 16:9 monitor</td><td>e.g.<br>Physically larger</td></tr>'
        '<tr><td>SSD</td><td>HDD</td><td>4.1.1</td>'
        '<td>Cheaper per GB of storage space</td></tr>'
        '<tr><td>2 GB RAM</td><td>16 GB RAM</td><td>16 GB RAM</td><td>4.1.2</td></tr>'
        '<tr><td>Windows 7 Professional Edition</td>'
        '<td>Windows 10 Professional Edition</td><td>4.1.3</td><td>4.1.4</td></tr>'
        '</tbody></table>'
    )

    # HTML-editor code box (DBE CAT P2 May/June 2021 Q8.9) — the source
    # markup candidates draw the rendered table for. Tags PRE-ESCAPED
    # (&lt;/&gt;) because markers inject AFTER the HTML-escape pass; indent
    # via &nbsp; (the .code-box CSS collapses ordinary whitespace).
    _q89_code_html = (
        '<span class="code-box">'
        '&lt;table border="1"&gt;<br>'
        + '&nbsp;' * 8 + '&lt;tr&gt;<br>'
        + '&nbsp;' * 16 + '&lt;td colspan="2"&gt;DESCRIPTION&lt;/td&gt;<br>'
        + '&nbsp;' * 8 + '&lt;/tr&gt;<br>'
        + '&nbsp;' * 8 + '&lt;tr&gt;<br>'
        + '&nbsp;' * 16 + '&lt;td&gt;Item 2&lt;/td&gt;<br>'
        + '&nbsp;' * 16 + '&lt;td&gt;Item 1&lt;/td&gt;<br>'
        + '&nbsp;' * 8 + '&lt;/tr&gt;<br>'
        + '&lt;/table&gt;'
        '</span>'
    )

    def _apply_inline(esc):
        out = _u_marker_re.sub(r'<u>\1</u>', esc)
        out = out.replace('[[CAT]]', _cat_svg)
        out = out.replace('[[CAR]]', _car_svg)
        out = out.replace('[[CONTACT_TBL]]', _contact_tbl_html)
        out = out.replace('[[Q4FACILITIES]]', _q4_facilities_html)
        # Bordered URL box (DBE Q9.3.3 May/June 2024): [[URLBOX]]…[[/URLBOX]]
        # with [[BR]] forcing the internal line wraps shown in the PDF.
        out = out.replace('[[URLBOX]]', '<span class="url-frame">')
        out = out.replace('[[/URLBOX]]', '</span>')
        # Bordered specification box (DBE Q9.1 November 2023):
        # [[SPECBOX]]heading[[SPECHEAD]]body…[[/SPECBOX]] with [[BR]] line
        # breaks inside the body. Renders a centred bold heading over a
        # left-aligned list of component lines.
        out = out.replace('[[SPECBOX]]', '<span class="spec-frame"><span class="spec-head">')
        out = out.replace('[[SPECHEAD]]', '</span><span class="spec-body">')
        out = out.replace('[[/SPECBOX]]', '</span></span>')
        # Centred mini box for a single short value (DBE Q10.5 "30/5 Mbps").
        out = out.replace('[[CBOX]]', '<span class="cbox-wrap"><span class="cbox">')
        out = out.replace('[[/CBOX]]', '</span></span>')
        # Registration entry form box (DBE Q10.1 November 2023).
        out = out.replace('[[ENTRYFORM]]', _entry_form_html)
        # Questionnaire table + news-article extract box
        # (DBE CAT P2 May/June 2022 Q6.1 / Q6.2).
        out = out.replace('[[Q61TABLE]]', _q61_table_html)
        out = out.replace('[[Q62EXTRACT]]', _q62_extract_html)
        # SOHO specifications comparison table (DBE CAT P2 May/June 2021 Q4.1).
        out = out.replace('[[Q41TABLE]]', _q41_table_html)
        # HTML-editor code box (DBE CAT P2 May/June 2021 Q8.9).
        out = out.replace('[[Q89CODE]]', _q89_code_html)
        # Database-design table (DBE CAT P2 May/June 2022 Q8.3).
        out = out.replace('[[Q83TABLE]]', _q83_table_html)
        out = out.replace('[[Q87CODE]]', _q87_code_html)
        # Computer-specifications table (DBE CAT P2 May/June 2022 Q9.1.1).
        out = out.replace('[[Q911SPEC]]', _q911_spec_html)
        # HTML-editor code box w/ indentation (DBE CAT P2 May/June 2022 Q10.10).
        out = out.replace('[[Q1010CODE]]', _q1010_code_html)
        out = out.replace('[[BR]]', '<br>')
        # Inline bold span: **text**
        import re as __re
        out = __re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', out, flags=__re.DOTALL)
        # Webdings glyph token: [wd:NNN]
        out = __re.sub(
            r'\[wd:(\d{1,3})\]',
            lambda m: f'<span class="wd">{chr(int(m.group(1)))}</span>',
            out,
        )
        # Whitelist <b>/<strong>/<i>/<em> that authors embedded directly.
        for _t in ('b', 'strong', 'i', 'em'):
            out = out.replace(f'&lt;{_t}&gt;', f'<{_t}>').replace(f'&lt;/{_t}&gt;', f'</{_t}>')
        # Auto-bold DBE-standard tokens so generated papers match the
        # official PDF styling (which always bolds these):
        #   • exam data-file names ......... 1App, 1Courses, 6_1Home, 6_2Popular
        #   • database object names ........ tbl5_1, frm5_2, qry5_3, rpt5_7, tblStudents
        #   • spreadsheet cell/column/row/step references
        # Each pattern uses a (?<![\w>]) lookbehind so it only fires at a
        # token start and never re-wraps text already inside a <strong> tag.
        def _autobold(_m):
            return '<strong>' + _m.group(0) + '</strong>'
        out = __re.sub(r'(?<![\w>])\d(?:_\d)?[A-Z][a-z][A-Za-z0-9_]*', _autobold, out)
        out = __re.sub(r'(?<![\w>])(?:tbl|frm|qry|rpt)[A-Za-z0-9_]+', _autobold, out)
        out = __re.sub(r'(?<![\w>])cell\s+[A-Z]{1,3}\s?\d{1,3}\b', _autobold, out)
        out = __re.sub(r'(?<![\w>])column\s+[A-Z]\b', _autobold, out)
        out = __re.sub(r'(?<![\w>])row\s+\d{1,3}\b', _autobold, out)
        out = __re.sub(r'(?<![\w>])Step\s+\d+\s*:', _autobold, out)
        return out

    def _split_marks(body):
        """Return (body_without_trailing_marks, marks_html_or_empty)."""
        m = trail_marks_re.search(body)
        if not m:
            return body, ''
        cleaned = body[:m.start()].rstrip()
        return cleaned, '<span class="ln-marks">(' + m.group(1) + ')</span>'

    parts = []
    for b in out:
        if b[0] == 'break':
            parts.append('<span class="ln-break"></span>')
        elif b[0] == 'bullet':
            body, marks_html = _split_marks(b[1])
            parts.append(
                '<span class="bullet"><span></span><span>'
                + marks_html
                + _apply_inline(str(escape(body)))
                + '</span></span>'
            )
        elif b[0] == 'mcq':
            letter = b[1]
            body, marks_html = _split_marks(b[2])
            parts.append(
                '<span class="mcq-opt"><span class="mcq-letter">'
                + str(escape(letter))
                + '</span><span class="mcq-body">'
                + marks_html
                + _apply_inline(str(escape(body)))
                + '</span></span>'
            )
        else:
            body, marks_html = _split_marks(b[1])
            esc = str(escape(body))
            esc = label_re.sub(lambda mm: '<strong>' + mm.group(1) + '</strong>', esc)
            esc = _apply_inline(esc)
            parts.append('<span class="ln">' + marks_html + esc + '</span>')
    return Markup(''.join(parts))

@app.template_filter('memo_ticks')
def memo_ticks_filter(s):
    """Escape user content, dedent each line, strip trailing (N) mark notation,
    then replace ? with an inline-SVG tick so it renders reliably in PDFs
    even when the system font lacks U+2713."""
    from markupsafe import escape, Markup
    import re as _re
    if not s:
        return Markup('')
    # If the answer already contains an HTML table, treat the whole answer
    # as raw HTML (memo authors can hand-craft comparison/grid tables for
    # questions like "Difference between queries" where bullet-style ticks
    # are insufficient).
    _s_str = str(s)
    import re as _re2
    if _re2.search(r'<table[\s>]', _s_str, _re2.IGNORECASE):
        return Markup(_s_str)
    # Dedent every line (template indentation leaks into pre-line content)
    lines = [ln.strip() for ln in _s_str.splitlines()]
    # Remove trailing parenthetical mark like "(2)" on its own line — marks col already shows it
    while lines and _re.fullmatch(r'\(\d+\)', lines[-1] or ''):
        lines.pop()
    # Drop empty trailing lines
    while lines and not lines[-1]:
        lines.pop()
    # Merge soft-wrapped continuations: a line that doesn't start with a list
    # marker, tick, bullet or sentence-end punctuation gets joined onto the
    # previous line. (DBE imports often hard-wrap mid-item at print width.)
    _re_marker = _re.compile(r'^\s*(?:\(\d+\)|\d+[.)]|[\u2022\u2013\u2014-])\s')
    _re_tickline = _re.compile(r'^\s*[\u2713\u2714\uf0fb\uf0fc]')
    merged = []
    for ln in lines:
        # Treat a short line ending in ':' (e.g. "Physical health:",
        # "Mental and emotional health:") as a subgroup label — never
        # merge it onto the previous list item.
        _is_sublabel = bool(ln) and ln.rstrip().endswith(':') and len(ln) < 80
        if (merged
                and ln
                and not _is_sublabel
                and not _re_marker.match(ln)
                and not _re_tickline.match(ln)
                and not ln.lower().startswith(('any ', 'accept', 'max', 'note', 'example', 'reason', '(any', '(accept', '(max'))
                and _re_marker.match(merged[-1])):
            merged[-1] = merged[-1].rstrip() + ' ' + ln.lstrip()
        else:
            merged.append(ln)
    lines = merged
    cleaned = '\n'.join(lines)
    escaped = str(escape(cleaned))
    # Allow a small whitelist of inline formatting tags to survive escaping
    # so memo authors can mark up specific words/phrases (e.g. underlined
    # "one-word synonym", italic emphasis). Closing tags too.
    for _tag in ('u', 'i', 'b', 'em', 'strong', 'sub', 'sup'):
        escaped = escaped.replace('&lt;' + _tag + '&gt;', '<' + _tag + '>')
        escaped = escaped.replace('&lt;/' + _tag + '&gt;', '</' + _tag + '>')
    # Hanging indent: lines starting with "(N)" / "N)" / "N." get a left-padded
    # block so wrapped lines align under the first word, not under the marker.
    def _wrap_hang(line):
        m = _re.match(r'^(\(\d+\)|\d+[.)])\s+(.*)$', line)
        if not m:
            # Subgroup label: bold, slight top margin so it visually
            # separates from the preceding enumerated block.
            _t = line.strip()
            if _t.endswith(':') and len(_t) < 80 and not _t.startswith('('):
                return ('<strong class="sublabel" '
                        'style="display:inline-block; margin-top:6px;">'
                        + _t + '</strong>')
            # Bold standalone Excel formula lines (e.g. "=MAX(H11:H65)-LARGE(H11:H65,2)")
            # and bare "OR" / "AND" connectors that DBE places between
            # alternate formulas in the marking guide. Insert <wbr> break
            # opportunities after delimiters so long spaceless formulas wrap
            # at "(", "," and ")" boundaries instead of chopping function
            # names mid-word (e.g. "LEFT" splitting into "LEF" + "T").
            if _t.startswith('=') and len(_t) < 200:
                _ft = (_t.replace('(', '(<wbr>')
                          .replace(',', ',<wbr>')
                          .replace(')', ')<wbr>'))
                return '<strong>' + _ft + '</strong>'
            if _t in ('OR', 'AND'):
                return '<strong>' + _t + '</strong>'
            # Inline "Label: value" — bold the label only (DBE memo
            # pattern: "Concept: …", "Relevance: …", "Reason: …",
            # "Example: …", etc.). Stops at first colon followed by
            # whitespace and a non-empty value. Label must look like a
            # short capitalised word/phrase (≤40 chars, no digits in
            # body, no parentheses).
            _lm = _re.match(
                r'^([A-Z][A-Za-z][A-Za-z /]{0,40}):(\s+)(\S.*)$', line)
            if _lm and not _lm.group(3).startswith(
                    ('&lt;', '&#', '&quot;')):
                return ('<strong>' + _lm.group(1) + ':</strong>'
                        + _lm.group(2) + _lm.group(3))
            return line
        marker, rest = m.group(1), m.group(2)
        return ('<span class="li-num">' + marker + '</span>'
                '<span class="li-txt">' + rest + '</span>')
    escaped_lines = [_wrap_hang(ln) for ln in escaped.split('\n')]
    escaped = '\n'.join(escaped_lines)
    tick_svg = (
        '<svg class="tick" viewBox="0 0 16 16" width="13" height="13" '
        'aria-hidden="true" style="vertical-align:-2px; display:inline-block;">'
        '<path d="M1.8 8.4 L4.5 8.0 L6.8 11.6 L13.0 1.6 L14.6 2.6 L7.6 14.0 L5.6 13.2 Z" '
        'fill="currentColor" stroke="currentColor" stroke-width="0.4" '
        'stroke-linejoin="round"/></svg>'
    )
    # Common tick glyphs: U+2713 (?), U+2714 (?), and U+F0FC (Wingdings —?tick
    # — frequently leaks in from Word / PDF imports as a private-use codepoint).
    for _ch in ('\u2713', '\u2714', '\uf0fc', '\uf0fb'):
        escaped = escaped.replace(_ch, tick_svg)
    # Re-inject ticks on "(Any N)" lines. The MG importer strips raw
    # tick glyphs because they pollute label/answer matching, but the
    # printed memo MUST show one tick per mark in front of the tail
    # token ("✓ (Any one)", "✓✓ (Any two)", "✓✓✓ (Any three)" etc.).
    _NUM_TICKS = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4,
        'five': 5, 'six': 6, 'seven': 7, 'eight': 8,
    }
    def _inject_any_ticks(_line):
        _m = _re.match(
            r'^(\s*)\((Any|Accept any)\s+(\w+)([^)]*)\)\s*$',
            _line, _re.IGNORECASE)
        if not _m:
            return _line
        _word = _m.group(3).lower()
        _n = _NUM_TICKS.get(_word)
        if not _n:
            try:
                _n = int(_word)
            except ValueError:
                _n = 1
        return (_m.group(1)
                + (tick_svg * _n) + ' '
                + '(' + _m.group(2) + ' ' + _m.group(3) + _m.group(4) + ')')
    escaped = '\n'.join(_inject_any_ticks(ln) for ln in escaped.split('\n'))
    # Right-align any line that consists of marking-tail notation
    # (leading ticks +/- "(Any N)" / "(Accept —)") so it sits in the
    # bottom-right of the answer cell, DBE-style.
    out_lines = []
    _re_tail = _re.compile(
        r'^\s*(?:%s\s*)+(?:\([^)]+\))?\s*$' % _re.escape(tick_svg)
    )
    _re_anyparen = _re.compile(
        r'^\s*(?:%s\s*)*\((?:any\s+\w+|accept[^)]*|max[^)]*)\)\s*$' % _re.escape(tick_svg),
        _re.IGNORECASE,
    )
    for ln in escaped.split('\n'):
        if _re_tail.match(ln) or _re_anyparen.match(ln):
            out_lines.append('<span class="memo-tail">' + ln.strip() + '</span>')
        else:
            out_lines.append(ln)
    # Detect runs of "left | right" lines and replace them with a 2-column
    # comparison table (DBE compare-and-contrast pattern).
    final_lines = []
    i = 0
    while i < len(out_lines):
        ln = out_lines[i]
        # A table line must contain " | " AND not be wrapped in memo-tail / li-num spans.
        if (' | ' in ln
                and '<span class="memo-tail">' not in ln
                and '<span class="li-num">' not in ln):
            # Find the run.
            j = i
            while (j < len(out_lines)
                   and ' | ' in out_lines[j]
                   and '<span class="memo-tail">' not in out_lines[j]
                   and '<span class="li-num">' not in out_lines[j]):
                j += 1
            run = out_lines[i:j]
            if len(run) >= 2:
                rows_html = []
                for k, rln in enumerate(run):
                    parts = [p.strip() for p in rln.split(' | ', 1)]
                    if len(parts) != 2:
                        parts = [rln, '']
                    tag = 'th' if k == 0 else 'td'
                    rows_html.append(
                        '<tr><{0}>{1}</{0}><{0}>{2}</{0}></tr>'.format(tag, parts[0], parts[1])
                    )
                final_lines.append(
                    '<table class="memo-cmp"><tbody>' + ''.join(rows_html) + '</tbody></table>'
                )
                i = j
                continue
        final_lines.append(ln)
        i += 1
    out_lines = final_lines
    # Join with explicit <br> so block-level memo-tail spans don't get a
    # phantom blank line from CSS white-space: pre-line.
    html = '<br>'.join(out_lines)
    # Collapse a trailing <br> just before a memo-tail block (the block
    # element already starts a new line).
    html = _re.sub(r'<br>\s*(<span class="memo-tail">)', r'\1', html)
    # Strip <br> immediately around inline tables.
    html = _re.sub(r'<br>\s*(<table class="memo-cmp">)', r'\1', html)
    html = _re.sub(r'(</table>)\s*<br>', r'\1', html)
    # Inline Webdings-cat marker (DBE Q1.11 May/June 2024): [[CAT]] →
    # small inline SVG silhouette (survives HTML-escape since brackets
    # aren't escaped). Renders the Webdings character code 246 glyph the
    # PDF shows without depending on the Webdings font being installed.
    if '[[CAT]]' in html:
        html = html.replace(
            '[[CAT]]',
            '<img class="inline-webdings" '
            'src="/static/images/memo/webdings_cat.svg" '
            'alt="cat" style="height:1em;vertical-align:-0.18em;">'
        )
    if '[[CAR]]' in html:
        html = html.replace(
            '[[CAR]]',
            '<img class="inline-webdings" '
            'src="/static/images/memo/webdings_car.svg" '
            'alt="car" style="height:0.9em;vertical-align:-0.1em;">'
        )
    return Markup(html)

@app.context_processor
def inject_globals():
    return {'now': datetime.utcnow(), 'app_name': 'South African Teachers Hub'}

# =====================================================================
#  AUTH ROUTES
# =====================================================================
@app.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        user = User.query.filter((User.username==username)|(User.email==username)).first()
        if user and user.check_password(password):
            if getattr(user, 'is_blocked', False):
                flash('This account has been blocked. Contact an administrator.', 'danger')
                return render_template('login.html')
            login_user(user)
            flash('Welcome back!','success')
            return redirect(request.args.get('next') or url_for('index'))
        flash('Invalid username or password.','danger')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        email = request.form.get('email','').strip()
        password = request.form.get('password','')
        confirm_password = request.form.get('confirm_password','')
        if password != confirm_password:
            flash('Passwords do not match.','danger'); return render_template('register.html')
        role = (request.form.get('role','') or '').strip().lower()
        first_name = request.form.get('first_name','').strip()
        last_name = request.form.get('last_name','').strip()
        school_name = request.form.get('school_name','').strip()
        school_district = request.form.get('school_district','').strip()
        province = request.form.get('province','').strip()
        town = request.form.get('town','').strip()
        suburb = request.form.get('suburb','').strip()
        subjects_list = [s.strip() for s in request.form.getlist('subjects') if s.strip()]
        if len(subjects_list) > 4:
            flash('Please select no more than 4 subjects.','danger'); return render_template('register.html')
        if not subjects_list:
            flash('Please select at least one subject you teach.','danger'); return render_template('register.html')
        subjects_csv = ','.join(subjects_list)
        if role not in ('teacher','hod'):
            flash('Please select a valid role (Teacher or HOD).','danger'); return render_template('register.html')
        if User.query.filter_by(username=username).first():
            flash('Username already taken.','danger'); return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('Email already registered.','danger'); return render_template('register.html')
        user = User(username=username, email=email, first_name=first_name, last_name=last_name,
                    school_name=school_name, school_district=school_district, province=province,
                    town=town, suburb=suburb, subjects=subjects_csv,
                    is_teacher=True, is_hod=(role == 'hod'))
        user.set_password(password)
        db.session.add(user); db.session.commit()
        login_user(user)
        flash('Educator account created!','success')
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user(); flash('Logged out.','info'); return redirect(url_for('index'))

# =====================================================================
#  MAIN ROUTES
# =====================================================================
@app.route('/')
def index():
    grades = Grade.query.order_by(Grade.number).all()
    return render_template('index.html', grades=grades)

@app.route('/our-mission')
def our_mission():
    return render_template('our_mission.html')

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/terms-of-service')
def terms_of_service():
    return render_template('terms_of_service.html')

@app.route('/popi-compliance')
def popi_compliance():
    return render_template('popi_compliance.html')

@app.route('/cookie-settings')
def cookie_settings():
    return render_template('cookie_settings.html')

@app.route('/acceptable-use')
def acceptable_use():
    return render_template('acceptable_use.html')

@app.route('/blooms-taxonomy')
def blooms_taxonomy():
    return render_template('blooms_taxonomy.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Teacher-only deployment: route everyone to the appropriate workspace
    # (admins/teachers go to the teacher dashboard; anyone else goes home).
    if current_user.is_admin or current_user.is_teacher:
        return redirect(url_for('teacher_dashboard'))
    return redirect(url_for('index'))

# =====================================================================
#  TEACHER ROUTES
# =====================================================================
from werkzeug.utils import secure_filename

TEACHER_DOC_EXTS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                    'zip', 'rar', '7z', 'mdb', 'accdb', 'csv', 'txt'}
TEACHER_LOGO_EXTS = {'png', 'jpg', 'jpeg', 'svg', 'webp', 'jfif', 'gif', 'bmp', 'avif'}


def teacher_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login', next=request.path))
        # HODs are teachers too — they may not always have is_teacher=True
        # in older rows, so accept them explicitly here.
        if not (current_user.is_teacher or current_user.is_hod or current_user.is_admin):
            abort(403)
        return f(*args, **kwargs)
    return decorated


# Maximum teachers an HOD can add to their moderation team.
HOD_TEAM_LIMIT = 7


def hod_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login', next=request.path))
        if not (current_user.is_hod or current_user.is_admin):
            abort(403)
        return f(*args, **kwargs)
    return decorated


def _ext(fname):
    return fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''


def _save_upload(file_storage, subdir, allowed):
    if not file_storage or not file_storage.filename:
        return None, 0
    ext = _ext(file_storage.filename)
    if ext not in allowed:
        return None, 0
    name = secure_filename(file_storage.filename)
    base, _ = os.path.splitext(name)
    unique = f"{base}_{uuid.uuid4().hex[:8]}.{ext}"
    folder = os.path.join('static', 'uploads', subdir)
    os.makedirs(folder, exist_ok=True)
    abs_path = os.path.join(folder, unique)
    file_storage.save(abs_path)
    rel = f"uploads/{subdir}/{unique}"
    return rel, os.path.getsize(abs_path)


@app.route('/teacher')
@teacher_required
def teacher_dashboard():
    docs = TeacherDocument.query.order_by(TeacherDocument.uploaded_at.desc()).limit(6).all()
    docs_count = TeacherDocument.query.count()
    bank_count = QuestionBankItem.query.filter_by(owner_id=current_user.id).count()
    paper_count = GeneratedPaper.query.filter_by(owner_id=current_user.id).count()
    mod_count = GeneratedPaper.query.filter_by(owner_id=current_user.id, moderation_status='flagged').count()
    upcoming = (TeacherSchedule.query
                .filter_by(owner_id=current_user.id)
                .filter(TeacherSchedule.start_date >= datetime.utcnow().date())
                .order_by(TeacherSchedule.start_date).limit(5).all())
    upcoming_count = (TeacherSchedule.query
                .filter_by(owner_id=current_user.id)
                .filter(TeacherSchedule.start_date >= datetime.utcnow().date())
                .count())
    return render_template('teacher/dashboard.html',
        docs=docs, docs_count=docs_count, bank_count=bank_count, paper_count=paper_count,
        mod_count=mod_count, upcoming=upcoming, upcoming_count=upcoming_count)


@app.route('/teacher/profile')
@teacher_required
def teacher_profile():
    """Display all profile information collected at sign-up."""
    subjects_list = [s.strip() for s in (current_user.subjects or '').split(',') if s.strip()]
    role_label = 'Head of Department (HOD)' if current_user.is_hod else ('Administrator' if current_user.is_admin else 'Teacher')
    PROVINCES = ['Eastern Cape','Free State','Gauteng','KwaZulu-Natal','Limpopo',
                 'Mpumalanga','Northern Cape','North West','Western Cape']
    ALL_SUBJECTS = sorted([
        'Computer Applications Technology','Information Technology',
        'Mathematics','Mathematical Literacy',
        'Physical Sciences','Life Sciences','Natural Sciences',
        'English HL','English FAL','Afrikaans HL','Afrikaans FAL',
        'isiZulu','isiXhosa','Sesotho','Setswana',
        'History','Geography','Accounting','Business Studies','Economics',
        'EMS','Life Orientation','Technology','Creative Arts',
        'Visual Arts','Dramatic Arts','Music','Religion Studies',
        'Tourism','Hospitality Studies','Consumer Studies',
        'Engineering Graphics & Design','Agricultural Sciences',
        'Agricultural Management Practices'
    ], key=str.lower)
    return render_template('teacher/profile.html',
                           subjects_list=subjects_list,
                           role_label=role_label,
                           provinces=PROVINCES,
                           all_subjects=ALL_SUBJECTS)


@app.route('/teacher/profile/update', methods=['POST'])
@teacher_required
def teacher_profile_update():
    """Allow a teacher to edit any of the personal/school/subject fields shown on their profile."""
    first_name      = request.form.get('first_name','').strip()
    last_name       = request.form.get('last_name','').strip()
    username        = request.form.get('username','').strip()
    email           = request.form.get('email','').strip().lower()
    school_name     = request.form.get('school_name','').strip()
    school_district = request.form.get('school_district','').strip()
    province        = request.form.get('province','').strip()
    town            = request.form.get('town','').strip()
    suburb          = request.form.get('suburb','').strip()
    subjects_list   = [s.strip() for s in request.form.getlist('subjects') if s.strip()]

    if not username:
        flash('Username is required.', 'danger')
        return redirect(url_for('teacher_profile'))
    if not email or '@' not in email:
        flash('A valid email address is required.', 'danger')
        return redirect(url_for('teacher_profile'))
    if len(subjects_list) > 4:
        flash('Please select no more than 4 subjects.', 'danger')
        return redirect(url_for('teacher_profile'))

    # Uniqueness checks (only if changed)
    if username != current_user.username:
        if User.query.filter(User.username == username, User.id != current_user.id).first():
            flash('That username is already taken.', 'danger')
            return redirect(url_for('teacher_profile'))
    if email != (current_user.email or '').lower():
        if User.query.filter(User.email == email, User.id != current_user.id).first():
            flash('That email is already in use.', 'danger')
            return redirect(url_for('teacher_profile'))

    current_user.first_name      = first_name
    current_user.last_name       = last_name
    current_user.username        = username
    current_user.email           = email
    current_user.school_name     = school_name
    current_user.school_district = school_district
    current_user.province        = province
    current_user.town            = town
    current_user.suburb          = suburb
    current_user.subjects        = ','.join(subjects_list)

    try:
        db.session.commit()
        flash('Profile updated.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Could not save changes ({}).'.format(type(e).__name__), 'danger')

    return redirect(url_for('teacher_profile'))


@app.route('/teacher/profile/avatar', methods=['POST'])
@teacher_required
def teacher_profile_avatar():
    """Teacher/HOD uploads or replaces their profile picture."""
    f = request.files.get('avatar')
    if not f or not f.filename:
        flash('Please choose an image to upload.', 'danger')
        return redirect(url_for('teacher_profile'))
    rel, _size = _save_upload(f, 'avatars', TEACHER_LOGO_EXTS)
    if not rel:
        flash('Unsupported image type. Use PNG, JPG, GIF, WEBP or SVG.', 'danger')
        return redirect(url_for('teacher_profile'))
    # Best-effort cleanup of the previous avatar
    old = (current_user.profile_pic or '').strip()
    if old:
        try:
            old_abs = os.path.join('static', old)
            if os.path.exists(old_abs):
                os.remove(old_abs)
        except Exception:
            pass
    current_user.profile_pic = rel
    db.session.commit()
    flash('Profile picture updated.', 'success')
    return redirect(url_for('teacher_profile'))


@app.route('/teacher/profile/avatar/remove', methods=['POST'])
@teacher_required
def teacher_profile_avatar_remove():
    old = (current_user.profile_pic or '').strip()
    if old:
        try:
            old_abs = os.path.join('static', old)
            if os.path.exists(old_abs):
                os.remove(old_abs)
        except Exception:
            pass
    current_user.profile_pic = ''
    db.session.commit()
    flash('Profile picture removed.', 'success')
    return redirect(url_for('teacher_profile'))


# ---------- HOD team management ----------------------------------------
@app.route('/teacher/team')
@teacher_required
def teacher_team():
    """Show team membership.

    HODs see their roster (with capacity) and a form to add teachers.
    Teachers see who their HOD is (if any).
    """
    members = []
    hod = None
    if current_user.is_hod:
        members = (User.query
                   .filter_by(hod_id=current_user.id)
                   .order_by(User.first_name, User.last_name)
                   .all())
    elif current_user.hod_id:
        hod = db.session.get(User, current_user.hod_id)
    return render_template('teacher/team.html',
                           members=members,
                           hod=hod,
                           team_limit=HOD_TEAM_LIMIT)


@app.route('/teacher/team/add', methods=['POST'])
@hod_required
def teacher_team_add():
    identifier = (request.form.get('identifier') or '').strip()
    if not identifier:
        flash('Enter a teacher username or email.', 'danger')
        return redirect(url_for('teacher_team'))

    current_count = User.query.filter_by(hod_id=current_user.id).count()
    if current_count >= HOD_TEAM_LIMIT:
        flash(f'Team is full (max {HOD_TEAM_LIMIT} teachers).', 'danger')
        return redirect(url_for('teacher_team'))

    teacher = (User.query
               .filter((User.username == identifier) | (User.email == identifier))
               .first())
    if not teacher:
        flash('No user found with that username or email.', 'danger')
        return redirect(url_for('teacher_team'))
    if teacher.id == current_user.id:
        flash('You cannot add yourself to your own team.', 'danger')
        return redirect(url_for('teacher_team'))
    if not teacher.is_teacher or teacher.is_hod:
        flash('Only teacher accounts (not HODs) can be added to a team.', 'danger')
        return redirect(url_for('teacher_team'))
    if teacher.hod_id:
        if teacher.hod_id == current_user.id:
            flash(f'{teacher.full_name} is already on your team.', 'info')
        else:
            flash(f'{teacher.full_name} is already on another HOD\'s team.', 'danger')
        return redirect(url_for('teacher_team'))
    if not teacher.subscription_active:
        flash(f'{teacher.full_name} does not have an active subscription. '
              'Ask an admin to activate it first.', 'danger')
        return redirect(url_for('teacher_team'))

    teacher.hod_id = current_user.id
    if current_user.school_name and not teacher.school_name:
        teacher.school_name = current_user.school_name
    db.session.commit()
    flash(f'{teacher.full_name} added to your team.', 'success')
    return redirect(url_for('teacher_team'))


@app.route('/teacher/team/remove/<user_id>', methods=['POST'])
@hod_required
def teacher_team_remove(user_id):
    teacher = db.session.get(User, user_id)
    if not teacher or teacher.hod_id != current_user.id:
        flash('Teacher is not on your team.', 'danger')
        return redirect(url_for('teacher_team'))
    teacher.hod_id = None
    db.session.commit()
    flash(f'{teacher.full_name} removed from your team.', 'success')
    return redirect(url_for('teacher_team'))


# ---------- Paper moderation workflow ----------------------------------
@app.route('/teacher/generator/<paper_id>/flag', methods=['POST'])
@teacher_required
def teacher_paper_flag(paper_id):
    """Teacher submits a draft paper to their HOD for moderation."""
    paper = GeneratedPaper.query.get_or_404(paper_id)
    if paper.owner_id != current_user.id and not current_user.is_admin:
        abort(403)
    if not current_user.hod_id and not current_user.is_admin:
        flash('You are not part of an HOD team. Ask your HOD to add you first.',
              'danger')
        return redirect(url_for('teacher_papers_generated'))
    if paper.moderation_status == 'signed_off':
        flash('Paper is already signed off.', 'info')
        return redirect(url_for('teacher_papers_generated'))
    paper.moderation_status = 'flagged'
    paper.moderator_id = current_user.hod_id or paper.moderator_id
    paper.moderator_notes = ''
    paper.flagged_at = datetime.utcnow()
    paper.signed_off_at = None
    # Snapshot the pre-moderation paper as the "Original" version. Always
    # overwrite so the original reflects whatever the teacher last saved
    # before flagging. Snapshot both sections AND the top-level header
    # fields so the moderator's later diff can show old → new for any
    # field they change. Strip any leftover moderator overlays from a
    # previous round so the Original is always clean (no green text).
    # Also embed the current question text/marks per question so later
    # edits to the global question bank don't retro-actively change the
    # "Original" view of this paper.
    paper.sections_original = _snapshot_questions_in_sections(
        _strip_mod_tags(paper.sections or '[]')
    )
    paper.header_original = json.dumps(_paper_header_snapshot(paper))
    paper.moderator_overrides = ''
    db.session.commit()
    flash('Paper flagged for moderation.', 'success')
    return redirect(url_for('teacher_papers_generated'))


@app.route('/teacher/moderation')
@hod_required
def teacher_moderation_queue():
    """List papers awaiting this HOD's review (or all for admins)."""
    if current_user.is_admin and not current_user.is_hod:
        papers = (GeneratedPaper.query
                  .filter(GeneratedPaper.moderation_status.in_(['flagged', 'rejected', 'signed_off', 'accepted']))
                  .order_by(GeneratedPaper.flagged_at.desc().nullslast())
                  .all())
    else:
        papers = (GeneratedPaper.query
                  .filter_by(moderator_id=current_user.id)
                  .filter(GeneratedPaper.moderation_status.in_(['flagged', 'rejected', 'signed_off', 'accepted']))
                  .order_by(GeneratedPaper.flagged_at.desc().nullslast())
                  .all())
    # Attach owner name for display
    owner_ids = {p.owner_id for p in papers}
    owners = {u.id: u for u in User.query.filter(User.id.in_(owner_ids)).all()} if owner_ids else {}
    return render_template('teacher/moderation_queue.html',
                           papers=papers, owners=owners)


def _can_moderate(paper):
    if not current_user.is_authenticated:
        return False
    if current_user.is_admin:
        return True
    return current_user.is_hod and paper.moderator_id == current_user.id


def _safe_loads_dict(s):
    try:
        v = json.loads(s or '{}')
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


# Top-level paper fields the moderator can change and that we want to
# show as strikethrough-old + green-new in the printed paper.
_PAPER_HEADER_FIELDS = (
    'title', 'school_name', 'subject', 'grade', 'exam_date',
    'duration_minutes', 'total_marks', 'examiner', 'moderator',
    'instructions', 'paper_number', 'cover_authority', 'cover_subtitle',
    'cover_extra_note', 'header_left', 'header_right', 'sub_header',
    'footer_left', 'footer_center', 'footer_right', 'memo_title',
)


def _paper_header_snapshot(paper):
    """Return a JSON-serializable dict of the top-level paper fields."""
    snap = {}
    for f in _PAPER_HEADER_FIELDS:
        v = getattr(paper, f, '')
        if hasattr(v, 'isoformat'):  # date / datetime
            v = v.isoformat()
        snap[f] = v if v is not None else ''
    return snap


def _format_duration(mins):
    try:
        m = int(mins or 0)
    except Exception:
        return str(mins or '')
    h, mm = divmod(m, 60)
    parts = []
    if h: parts.append(f"{h} Hour" + ('s' if h != 1 else ''))
    if mm: parts.append(f"{mm} Min" + ('s' if mm != 1 else ''))
    return ' '.join(parts) or '0 Mins'


def _format_header_field(field, value):
    """Pretty-print a header field for display in the paper. Mirrors the
    formatting used by the print template so the diff old/new look identical."""
    if value in (None, ''):
        return ''
    if field == 'duration_minutes':
        return _format_duration(value)
    if field == 'exam_date':
        try:
            from datetime import date as _date, datetime as _dt
            if isinstance(value, str):
                v = _dt.fromisoformat(value).date() if 'T' in value or len(value) > 10 else _date.fromisoformat(value)
            else:
                v = value
            return v.strftime('%d %B %Y')
        except Exception:
            return str(value)
    return str(value)


def _word_diff_html(old_text, new_text):
    """Return an HTML string showing only the actually-changed runs of
    text wrapped in <span class="mod-old">…</span> (deletions) and
    <span class="mod-edited">…</span> (insertions). Unchanged runs are
    HTML-escaped plain text. Tokenisation is word-level (preserving
    whitespace tokens) so single-character edits inside a sentence don't
    paint the whole sentence green.
    """
    import difflib, re, html as _html
    from markupsafe import Markup
    old_text = old_text or ''
    new_text = new_text or ''
    if old_text == new_text:
        return Markup(_html.escape(new_text))
    # Tokenise into runs of \w+, whitespace, or single non-word chars.
    tokenize = lambda s: re.findall(r'\w+|\s+|[^\w\s]', s, flags=re.UNICODE)
    a = tokenize(old_text)
    b = tokenize(new_text)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            out.append(_html.escape(''.join(b[j1:j2])))
        elif tag == 'delete':
            out.append('<span class="mod-old">' + _html.escape(''.join(a[i1:i2])) + '</span>')
        elif tag == 'insert':
            out.append('<span class="mod-edited">' + _html.escape(''.join(b[j1:j2])) + '</span>')
        elif tag == 'replace':
            out.append('<span class="mod-old">' + _html.escape(''.join(a[i1:i2])) + '</span>')
            out.append('<span class="mod-edited">' + _html.escape(''.join(b[j1:j2])) + '</span>')
    return Markup(''.join(out))


def _compute_paper_overrides(paper):
    """Compare current paper header fields against ``header_original``.
    Returns a dict {field: {'old': pretty_old, 'new': pretty_new,
    'old_raw': raw_old, 'new_raw': raw_new}} for any field that differs.
    Empty dict if no original snapshot exists."""
    try:
        orig = json.loads(paper.header_original or '{}')
    except Exception:
        orig = {}
    if not orig:
        return {}
    cur = _paper_header_snapshot(paper)
    out = {}
    for f in _PAPER_HEADER_FIELDS:
        ov = orig.get(f, '')
        nv = cur.get(f, '')
        if (ov or '') != (nv or ''):
            out[f] = {
                'old':     _format_header_field(f, ov),
                'new':     _format_header_field(f, nv),
                'old_raw': ov,
                'new_raw': nv,
            }
    return out


# Section-level keys added by `_tag_moderator_section_edits` to drive the
# strikethrough-old + green-new render. They must be stripped from any
# snapshot that is meant to represent a "clean" version (Original sent
# for moderation, Final accepted by the teacher) so those views never
# display the green moderator deltas.
_MOD_SECTION_KEYS = (
    'mod_title', 'mod_old_title',
    'mod_instr', 'mod_old_instr',
    'mod_qtitles', 'mod_old_qtitles',
    'mod_qinstr', 'mod_old_qinstr',
    'mod_questions',
)


def _strip_mod_tags(sections_json):
    """Return ``sections_json`` with every ``mod_*`` overlay removed so the
    payload represents a plain (un-moderated) version of the paper."""
    try:
        sections = json.loads(sections_json or '[]')
    except Exception:
        return sections_json or '[]'
    if not isinstance(sections, list):
        return sections_json or '[]'
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        for k in _MOD_SECTION_KEYS:
            sec.pop(k, None)
    return json.dumps(sections)


def _snapshot_questions_in_sections(sections_json):
    """Embed a ``question_snapshots`` map into every section so the printed
    snapshot is independent of any later edits to the global question
    bank.

    Each section gains:
        sec['question_snapshots'] = {
            qid: {'question_text': str, 'answer_text': str,
                  'marks': int, 'image_path': str},
            ...
        }
    """
    try:
        sections = json.loads(sections_json or '[]')
    except Exception:
        return sections_json or '[]'
    if not isinstance(sections, list):
        return sections_json or '[]'
    # Collect every qid we need so we can fetch them in one query.
    all_qids = set()
    for sec in sections:
        if isinstance(sec, dict):
            for qid in (sec.get('question_ids') or []):
                if qid:
                    all_qids.add(qid)
    qmap = {}
    if all_qids:
        rows = QuestionBankItem.query.filter(QuestionBankItem.id.in_(all_qids)).all()
        for q in rows:
            qmap[q.id] = {
                'question_text': q.question_text or '',
                'answer_text': q.answer_text or '',
                'marks': int(q.marks or 0),
                'image_path': q.image_path or '',
            }
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        snaps = {}
        for qid in (sec.get('question_ids') or []):
            if qid in qmap:
                snaps[qid] = qmap[qid]
        sec['question_snapshots'] = snaps
    return json.dumps(sections)


def _tag_moderator_section_edits(original_json, new_json):
    """Compare ``new_json`` against the pre-moderation ``original_json``
    snapshot and tag every changed/added field with both a sticky boolean
    flag (``mod_*``) and the previous value (``mod_old_*``) so the print
    template can render strikethrough-old + green-new.
    Flags added (always recomputed against the original):
        sec.mod_title         (bool)
        sec.mod_old_title     (str)
        sec.mod_instr         (bool)
        sec.mod_old_instr     (str)
        sec.mod_qtitles       (list[bool])
        sec.mod_old_qtitles   (list[str])
        sec.mod_qinstr        (list[bool])
        sec.mod_old_qinstr    (list[str])
        sec.mod_questions     (list[str]) — question_ids added by moderator
    """
    try:
        new_sections = json.loads(new_json or '[]')
    except Exception:
        return new_json
    try:
        orig_sections = json.loads(original_json or '[]')
    except Exception:
        orig_sections = []
    if not isinstance(new_sections, list):
        return new_json

    for si, sec in enumerate(new_sections):
        if not isinstance(sec, dict):
            continue
        osec = orig_sections[si] if si < len(orig_sections) and isinstance(orig_sections[si], dict) else {}

        # Section title --------------------------------------------------
        nt = sec.get('title') or ''
        ot = osec.get('title') or ''
        if nt != ot:
            sec['mod_title'] = True
            sec['mod_old_title'] = ot
        else:
            sec.pop('mod_title', None)
            sec.pop('mod_old_title', None)

        # Section-level instructions ------------------------------------
        ni = sec.get('instructions') or ''
        oi = osec.get('instructions') or ''
        if ni != oi:
            sec['mod_instr'] = True
            sec['mod_old_instr'] = oi
        else:
            sec.pop('mod_instr', None)
            sec.pop('mod_old_instr', None)

        # Per-Question titles -------------------------------------------
        new_qt = sec.get('qtitles') or []
        old_qt = osec.get('qtitles') or []
        mqt, mqt_old = [], []
        for gi, t in enumerate(new_qt):
            ot2 = old_qt[gi] if gi < len(old_qt) else ''
            if (t or '') != (ot2 or ''):
                mqt.append(True); mqt_old.append(ot2 or '')
            else:
                mqt.append(False); mqt_old.append('')
        if any(mqt):
            sec['mod_qtitles'] = mqt
            sec['mod_old_qtitles'] = mqt_old
        else:
            sec.pop('mod_qtitles', None)
            sec.pop('mod_old_qtitles', None)

        # Per-Question instructions -------------------------------------
        new_qi = sec.get('qinstructions') or []
        old_qi = osec.get('qinstructions') or []
        mqi, mqi_old = [], []
        for gi, t in enumerate(new_qi):
            ot2 = old_qi[gi] if gi < len(old_qi) else ''
            if (t or '') != (ot2 or ''):
                mqi.append(True); mqi_old.append(ot2 or '')
            else:
                mqi.append(False); mqi_old.append('')
        if any(mqi):
            sec['mod_qinstr'] = mqi
            sec['mod_old_qinstr'] = mqi_old
        else:
            sec.pop('mod_qinstr', None)
            sec.pop('mod_old_qinstr', None)

        # Newly added bank questions ------------------------------------
        old_qids = set(osec.get('question_ids') or [])
        added = [qid for qid in (sec.get('question_ids') or [])
                 if qid not in old_qids]
        if added:
            sec['mod_questions'] = added
        else:
            sec.pop('mod_questions', None)

    return json.dumps(new_sections)


@app.route('/teacher/moderation/<paper_id>/sign-off', methods=['POST'])
@hod_required
def teacher_paper_sign_off(paper_id):
    paper = GeneratedPaper.query.get_or_404(paper_id)
    if not _can_moderate(paper):
        abort(403)
    notes = (request.form.get('notes') or '').strip()
    paper.moderation_status = 'signed_off'
    paper.moderator_notes = notes
    paper.signed_off_at = datetime.utcnow()
    if not paper.moderator:
        paper.moderator = current_user.full_name
    # Snapshot the moderator's version (still carries the green mod_* flags).
    # Embed question text snapshots too so the Moderated view stays stable
    # even if the underlying bank items are edited again later.
    paper.sections_moderated = _snapshot_questions_in_sections(paper.sections or '[]')
    db.session.commit()
    flash('Paper signed off — it can now be printed.', 'success')
    return redirect(url_for('teacher_moderation_queue'))


@app.route('/teacher/moderation/<paper_id>/reject', methods=['POST'])
@hod_required
def teacher_paper_reject(paper_id):
    paper = GeneratedPaper.query.get_or_404(paper_id)
    if not _can_moderate(paper):
        abort(403)
    notes = (request.form.get('notes') or '').strip()
    if not notes:
        flash('Please add notes explaining what needs to change.', 'danger')
        return redirect(url_for('teacher_moderation_queue'))
    paper.moderation_status = 'rejected'
    paper.moderator_notes = notes
    paper.signed_off_at = None
    db.session.commit()
    flash('Paper sent back to the teacher with your notes.', 'success')
    return redirect(url_for('teacher_moderation_queue'))


@app.route('/teacher/paper/<paper_id>/accept-moderation', methods=['POST'])
@teacher_required
def teacher_paper_accept_moderation(paper_id):
    """Owner accepts the moderator's signed-off version. Snapshots the
    moderated sections into ``sections_final`` and promotes them to be the
    new live ``sections`` so the teacher can keep iterating from there."""
    paper = GeneratedPaper.query.get_or_404(paper_id)
    if paper.owner_id != current_user.id and not current_user.is_admin:
        abort(403)
    if (paper.moderation_status or '') != 'signed_off':
        flash('There is no signed-off moderator version to accept.', 'warning')
        return redirect(url_for('teacher_papers_generated'))
    if not (paper.sections_moderated or '').strip():
        flash('Moderator version is empty — nothing to accept.', 'warning')
        return redirect(url_for('teacher_papers_generated'))
    # The accepted Final is a clean copy of the moderator's version with
    # all green-overlay markers stripped — it represents the plain paper
    # the teacher signed off on, with no "old vs new" annotations. We
    # also re-snapshot question content from the (now moderator-edited)
    # bank so the Final view is frozen at accept time.
    clean_final = _snapshot_questions_in_sections(
        _strip_mod_tags(paper.sections_moderated)
    )
    paper.sections_final = clean_final
    paper.sections = clean_final
    # Apply the moderator's top-level field changes (duration, title, etc.)
    # to the live paper. The override map stores both the pretty and raw
    # value for each field; copy the raw value back onto the paper.
    try:
        ov = json.loads(paper.moderator_overrides or '{}')
    except Exception:
        ov = {}
    for f, info in (ov or {}).items():
        if f not in _PAPER_HEADER_FIELDS:
            continue
        new_raw = info.get('new_raw', info.get('new', ''))
        if f == 'exam_date':
            try:
                from datetime import date as _date
                if isinstance(new_raw, str) and new_raw:
                    paper.exam_date = _date.fromisoformat(new_raw[:10])
                elif not new_raw:
                    paper.exam_date = None
            except Exception:
                pass
        elif f in ('duration_minutes', 'total_marks', 'grade'):
            try:
                setattr(paper, f, int(new_raw or 0))
            except Exception:
                pass
        else:
            setattr(paper, f, new_raw or '')
    # Clear the override map — overrides are now baked in.
    paper.moderator_overrides = ''
    paper.moderation_status = 'accepted'
    db.session.commit()
    flash('Moderator changes accepted. The final version is now your live paper.', 'success')
    return redirect(url_for('teacher_papers_generated'))


@app.route('/teacher/formal-assessment')
@teacher_required
def teacher_formal_assessment():
    from formal_assessment_data import FORMAL_ASSESSMENT
    # Build the canonical subject list (sorted, with CAT first as the default).
    all_subjects = sorted(FORMAL_ASSESSMENT.keys())
    requested = (request.args.get('subject') or '').strip()
    # Backward-compatibility: legacy short codes from the previous 2-subject UI.
    legacy_codes = {'CAT': 'Computer Applications Technology',
                    'IT': 'Information Technology'}
    if requested in legacy_codes:
        requested = legacy_codes[requested]
    if requested not in FORMAL_ASSESSMENT:
        requested = 'Computer Applications Technology'
    entry = FORMAL_ASSESSMENT[requested]
    return render_template('teacher/formal_assessment.html',
                           subject=requested,
                           subject_label=entry['label'],
                           subject_data=entry,
                           all_subjects=all_subjects)


# ---------- Past papers / documents -------------------------------------
@app.route('/teacher/papers')
@teacher_required
def teacher_papers():
    subject = request.args.get('subject', '').strip()
    grade = request.args.get('grade', type=int)
    ptype = request.args.get('type', '')
    year  = request.args.get('year', type=int)
    pnum  = request.args.get('paper', '').strip()
    # Map full subject names back to legacy short codes used in some uploaded
    # documents so the filter matches both representations.
    _subject_aliases = {
        'Computer Applications Technology': ['Computer Applications Technology', 'CAT'],
        'Information Technology': ['Information Technology', 'IT'],
    }
    q = TeacherDocument.query
    if subject:
        aliases = _subject_aliases.get(subject, [subject])
        q = q.filter(TeacherDocument.subject.in_(aliases))
    if grade:
        q = q.filter_by(grade=grade)
    if ptype:
        q = q.filter_by(paper_type=ptype)
    if year:
        q = q.filter_by(paper_year=year)
    if pnum:
        q = q.filter_by(paper_number=pnum)
    docs = q.order_by(TeacherDocument.paper_year.desc().nullslast(),
                      TeacherDocument.uploaded_at.desc()).all()
    # Distinct year list for the dropdown (newest first, exclude None)
    years = [y for (y,) in db.session.query(TeacherDocument.paper_year)
                              .filter(TeacherDocument.paper_year.isnot(None))
                              .distinct()
                              .order_by(TeacherDocument.paper_year.desc()).all()]
    # Distinct subjects in the archive (alpha), with curated CAPS fallback.
    # Expand legacy short codes (CAT, IT) to their full CAPS subject names.
    _abbr_to_full = {'CAT': 'Computer Applications Technology', 'IT': 'Information Technology'}
    db_subjects = [s for (s,) in db.session.query(TeacherDocument.subject)
                                .filter(TeacherDocument.subject.isnot(None),
                                        TeacherDocument.subject != '')
                                .distinct().all()]
    db_subjects = [_abbr_to_full.get(s, s) for s in db_subjects]
    caps_subjects = [
        'Accounting', 'Afrikaans FAL', 'Afrikaans Home Language',
        'Agricultural Sciences', 'Business Studies',
        'Computer Applications Technology', 'Consumer Studies',
        'Dramatic Arts', 'Economics', 'Engineering Graphics & Design',
        'English FAL', 'English Home Language', 'Geography', 'History',
        'Hospitality Studies', 'Information Technology', 'Life Orientation',
        'Life Sciences', 'Mathematical Literacy', 'Mathematics',
        'Music', 'Physical Sciences', 'Religion Studies',
        'Tourism', 'Visual Arts',
    ]
    subjects = sorted(set(db_subjects) | set(caps_subjects))
    return render_template('teacher/papers.html', docs=docs, grade=grade,
                           ptype=ptype, year=year, pnum=pnum, years=years,
                           subject=subject, subjects=subjects)


@app.route('/teacher/papers/upload', methods=['GET', 'POST'])
@teacher_required
def teacher_paper_upload():
    if request.method == 'POST':
        f = request.files.get('file')
        rel, size = _save_upload(f, 'papers', TEACHER_DOC_EXTS)
        if not rel:
            flash('Please choose a valid file (PDF, Word, Excel, ZIP, etc.).', 'danger')
            return redirect(url_for('teacher_paper_upload'))
        doc = TeacherDocument(
            title=request.form.get('title', '').strip() or f.filename,
            description=request.form.get('description', '').strip(),
            grade=request.form.get('grade', type=int),
            subject=request.form.get('subject', 'CAT').strip() or 'CAT',
            paper_year=request.form.get('paper_year', type=int),
            paper_type=request.form.get('paper_type', 'past_paper'),
            paper_number=request.form.get('paper_number', '').strip(),
            file_path=rel, file_size=size, uploaded_by=current_user.id,
        )
        db.session.add(doc); db.session.commit()
        flash('Document uploaded.', 'success')
        return redirect(url_for('teacher_papers'))
    return render_template('teacher/paper_upload.html')


@app.route('/teacher/papers/<doc_id>/download')
@teacher_required
def teacher_paper_download(doc_id):
    from flask import send_from_directory
    doc = TeacherDocument.query.get_or_404(doc_id)
    doc.download_count = (doc.download_count or 0) + 1
    db.session.commit()
    folder = os.path.join('static', os.path.dirname(doc.file_path))
    return send_from_directory(folder, os.path.basename(doc.file_path),
                               as_attachment=True,
                               download_name=os.path.basename(doc.file_path))


@app.route('/teacher/papers/<doc_id>/delete', methods=['POST'])
@teacher_required
def teacher_paper_delete(doc_id):
    doc = TeacherDocument.query.get_or_404(doc_id)
    if doc.uploaded_by != current_user.id and not current_user.is_admin:
        abort(403)
    try:
        os.remove(os.path.join('static', doc.file_path))
    except OSError:
        pass
    db.session.delete(doc); db.session.commit()
    flash('Document deleted.', 'info')
    return redirect(url_for('teacher_papers'))


@app.route('/teacher/papers/<doc_id>/use', methods=['POST'])
@teacher_required
def teacher_paper_use(doc_id):
    """Take an uploaded past paper, extract its sections + questions from
    the PDF, create a fresh draft GeneratedPaper in the teacher's
    workspace, and load every question into the generator as editable
    QuestionBankItems. Falls back to a metadata-only draft if the file
    can't be parsed (e.g. scanned PDF, ZIP, Word doc)."""
    doc = TeacherDocument.query.get_or_404(doc_id)
    # Subject visibility: same rule as the rest of the teacher app.
    subj_set = _visible_subject_set()
    if subj_set is not None and (doc.subject or '') not in subj_set:
        abort(403)
    # Map legacy short subject codes to their full CAPS names so the new
    # GeneratedPaper carries the canonical subject string.
    _abbr_to_full = {'CAT': 'Computer Applications Technology',
                     'IT': 'Information Technology'}
    subj = _abbr_to_full.get((doc.subject or '').strip(),
                             (doc.subject or 'Computer Applications Technology').strip())
    title_src = (doc.title or 'Examination Paper').strip()
    new_title = title_src if title_src.lower().startswith('copy of ') else f'Copy of {title_src}'

    # ---- Try to parse the PDF into sections + questions ---------------
    parsed_sections = []
    parse_warning = ''
    cover_meta = {}
    pdf_path = os.path.join('static', doc.file_path or '')
    if doc.file_path and pdf_path.lower().endswith('.pdf') and os.path.exists(pdf_path):
        try:
            parsed_sections = _parse_past_paper_pdf(pdf_path, strict=True)
        except Exception as e:
            parse_warning = f'PDF could not be parsed ({e}). Created a blank draft instead.'
        try:
            cover_meta = _extract_past_paper_cover(pdf_path) or {}
        except Exception:
            cover_meta = {}
    elif not pdf_path.lower().endswith('.pdf'):
        parse_warning = 'Only PDF past papers can be auto-loaded; created a blank draft.'

    # Pick a sensible default exam date — prefer year+month from the PDF
    # cover, fall back to the document's recorded paper_year, mid-November.
    exam_dt = None
    _yr = cover_meta.get('year') or doc.paper_year
    _month_map = {'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5,
                  'JUN': 6, 'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10,
                  'NOV': 11, 'DEC': 12}
    _month_num = 11
    _mraw = (cover_meta.get('month') or '').upper()
    if _mraw:
        # MAY/JUNE -> use the first month so the cover reads "May".
        first = _mraw.split('/')[0][:3]
        _month_num = _month_map.get(first, 11)
    if _yr:
        try:
            from datetime import date as _date
            exam_dt = _date(int(_yr), _month_num, 15)
        except Exception:
            exam_dt = None

    # ---- Persist the new GeneratedPaper -------------------------------
    new_paper = GeneratedPaper(
        owner_id=current_user.id,
        title=new_title,
        subject=subj,
        grade=doc.grade or 12,
        exam_date=exam_dt,
        paper_number=(cover_meta.get('paper_number')
                      or (doc.paper_number or '').strip()),
        duration_minutes=cover_meta.get('duration_minutes') or 180,
        total_marks=cover_meta.get('total_marks') or 150,
        instructions=cover_meta.get('instructions') or '',
        data_files=cover_meta.get('data_files') or '',
        # Leave cover_extra_note blank so the rendered cover matches the
        # authentic DBE layout (Confidential / SC-NSC / Subject + Pn /
        # Month-Year / MARKS / TIME) without any extra noise.
        cover_extra_note='',
        sections='[]',
        moderation_status='draft',
        share_scope='private',
        is_library=True,
    )
    db.session.add(new_paper)
    db.session.flush()  # need new_paper.id for QuestionBankItem ownership

    # Convert parsed_sections into QuestionBankItem rows + sections JSON.
    sections_payload = []
    total_marks = 0
    for sec in parsed_sections:
        question_ids = []
        for q in sec.get('questions', []):
            qtext = (q.get('text') or '')
            if not qtext.strip():
                continue
            qmarks = int(q.get('marks') or 0)
            total_marks += qmarks
            tags = ['imported', 'past_paper', 'raw_pdf']
            if doc.paper_year:
                tags.append(str(doc.paper_year))
            item = QuestionBankItem(
                owner_id=current_user.id,
                grade=doc.grade or 12,
                subject=subj,
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
            question_ids.append(item.id)
        if question_ids:
            sections_payload.append({
                'title': sec.get('title') or 'Section',
                'instructions': sec.get('instructions') or '',
                'question_ids': question_ids,
                # Each parsed Question becomes its own top-level Question
                # (Q1, Q2, \u2026) on its own page card.
                'splits': list(range(len(question_ids))),
            })

    if sections_payload:
        # Pull the SCENARIO box (between cover instructions and QUESTION 1)
        # and attach it to the first section so the printed paper renders
        # the bordered scenario block above QUESTION 1, like the original.
        scenario_text = ''
        if pdf_path and pdf_path.lower().endswith('.pdf') and os.path.exists(pdf_path):
            try:
                import pdfplumber as _pp
                with _pp.open(pdf_path) as _pdf:
                    for _pg in _pdf.pages[:8]:
                        _t = _pg.extract_text() or ''
                        m = re.search(
                            r'(?is)\bSCENARIO\b\s*\n(.*?)(?=\n\s*(?:QUESTION\s+\d|SECTION\s+[A-Z]\b))',
                            _t)
                        if m:
                            scenario_text = re.sub(r'\s+', ' ', m.group(1)).strip()
                            break
            except Exception:
                pass
        if scenario_text:
            sections_payload[0]['scenario'] = scenario_text
        new_paper.sections = json.dumps(sections_payload)
        # Trust the cover's "MARKS: NN" if we successfully parsed it
        # (it's authoritative); only fall back to summing per-question
        # marks when the cover didn't tell us.
        if not cover_meta.get('total_marks') and total_marks > 0:
            new_paper.total_marks = total_marks
    db.session.commit()

    # ---- Auto-extract figure images from the source PDF ---------------
    # Each top-level section "question_ids[0]" is QUESTION N on the paper,
    # so build {qnum: question_id} mapping QUESTION 1..N to the first
    # QuestionBankItem id of each section, then mine the PDF for figures.
    if sections_payload and pdf_path and pdf_path.lower().endswith('.pdf') \
            and os.path.exists(pdf_path):
        # ---- Auto-extract "(Note to marker: …)" preambles from the
        # sibling marking-guideline PDF and inject them as the matching
        # Question's qinstructions so the memo card shows the note.
        try:
            _mg_path = _find_sibling_memo_pdf(pdf_path)
            if _mg_path:
                _mg = _extract_memo_answers(_mg_path) or {}
                _notes = _mg.get('__notes__') or {}
                _sub_tables = _mg.get('__tables__') or {}
                if _notes or _sub_tables:
                    _qn_pos = 0
                    _payload_dirty = False
                    for _sec in sections_payload:
                        _qids = _sec.get('question_ids') or []
                        _qi = _sec.get('qinstructions') or [''] * len(_qids)
                        # Pad qinstructions to match the number of
                        # Questions (= number of top-level question_ids
                        # since each parsed Question is its own pseudo
                        # group).
                        while len(_qi) < len(_qids):
                            _qi.append('')
                        for _local_idx in range(len(_qids)):
                            _qn_pos += 1
                            _note = _notes.get(_qn_pos)
                            if _note:
                                # Format as "(Note to marker: …)" so the
                                # template's TF intro renderer shows it
                                # in italic above the rows.
                                _formatted = '(Note to marker:\n' + _note + ')'
                                if _qi[_local_idx] != _formatted:
                                    _qi[_local_idx] = _formatted
                                    _payload_dirty = True
                        if _notes:
                            _sec['qinstructions'] = _qi
                        # Attach nested comparison sub-tables (per-label).
                        if _sub_tables:
                            _existing_st = _sec.get('subtables') or {}
                            _existing_st.update(_sub_tables)
                            _sec['subtables'] = _existing_st
                            _payload_dirty = True
                    if _payload_dirty:
                        new_paper.sections = json.dumps(sections_payload)
                        db.session.commit()
        except Exception as _e:
            app.logger.warning('Memo notes extraction failed for paper %s: %s',
                               new_paper.id, _e)
        try:
            from extract_paper_images import extract as _extract_paper_images
            qmap = {}
            qn = 0
            for _sec in sections_payload:
                for _qid in _sec.get('question_ids', []):
                    qn += 1
                    qmap[qn] = _qid
            _result = _extract_paper_images(pdf_path, new_paper.id, qmap)
            # Back-compat: older extractor returned (saved, skipped) only.
            if isinstance(_result, tuple) and len(_result) >= 3:
                _caption_strip = _result[2] or {}
            else:
                _caption_strip = {}
            # Strip duplicated caption text (advertisement spec lists,
            # bulleted feature blocks, etc.) from the QuestionBankItem
            # whose figure now contains that text visually.
            if _caption_strip:
                _bank_dirty = False
                # Group strip-lines by qid (multiple sub-items can each
                # contribute lines from the same Question item).
                _by_qid = {}
                for (_qid, _local), _lines in _caption_strip.items():
                    _by_qid.setdefault(_qid, []).extend(_lines)
                for _qid, _lines in _by_qid.items():
                    _bank = db.session.get(QuestionBankItem, _qid)
                    if not _bank or not _bank.question_text:
                        continue
                    _txt = _bank.question_text
                    for _ln in _lines:
                        _stripped = _ln.strip()
                        if not _stripped:
                            continue
                        # Build a whitespace-tolerant pattern: collapse
                        # internal runs of whitespace to "\s+" so the
                        # match survives the wider spacing the PDF text
                        # often carries (e.g. "⭐  Intel" vs "⭐ Intel").
                        _tokens = re.split(r'\s+', _stripped)
                        _pat_body = r'\s+'.join(re.escape(t) for t in _tokens if t)
                        _pat = re.compile(
                            r'(?m)^[ \t]*' + _pat_body + r'[ \t]*\n?')
                        _new = _pat.sub('', _txt)
                        if _new != _txt:
                            _txt = _new
                            _bank_dirty = True
                    # Collapse runs of 3+ blank lines left behind.
                    _txt = re.sub(r'\n{3,}', '\n\n', _txt)
                    if _txt != _bank.question_text:
                        _bank.question_text = _txt
                        _bank_dirty = True
                if _bank_dirty:
                    db.session.commit()
        except Exception as _e:
            app.logger.warning('Image extraction failed for paper %s: %s',
                               new_paper.id, _e)

    if sections_payload:
        nq = sum(len(s['question_ids']) for s in sections_payload)
        flash(f'Imported {nq} question(s) across {len(sections_payload)} section(s) '
              f'from "{title_src}". Edit anything you need to.', 'success')
    else:
        flash(parse_warning or
              f'Created a blank draft from "{title_src}". '
              f'No questions could be extracted — add them manually.', 'warning')
    return redirect(url_for('teacher_paper_edit', paper_id=new_paper.id))


# ---- Past-paper PDF parser ------------------------------------------------
_PP_SECTION_RE = re.compile(r'^\s*SECTION\s+([A-Z])\b[ \t:.\-–]*(.*)$', re.IGNORECASE)
_PP_QUESTION_RE = re.compile(r'^\s*QUESTION\s+(\d{1,2})\b[ \t:.\-–]*(.*)$', re.IGNORECASE)
# Trailing "(20)" or "[20]" on its own line or at end of line = total marks for the question.
_PP_MARKS_TAIL_RE = re.compile(r'[\(\[]\s*(\d{1,3})\s*[\)\]]\s*$')

def _extract_past_paper_cover(pdf_path):
    """Read the first 1-2 pages of a DBE past paper and pull out the
    cover-page metadata so the imported GeneratedPaper renders an
    authentic cover (Subject + Paper number, MARKS, TIME, MONTH/YEAR).

    Returns dict with any of: subject, paper_number, total_marks,
    duration_minutes, month, year, page_count_note. All keys are
    optional; the caller should fall back to defaults for missing ones.
    """
    out = {}
    try:
        import pdfplumber  # type: ignore
        with pdfplumber.open(pdf_path) as pdf:
            cover_text = ''
            # Scan up to first 5 pages \u2014 some DBE papers have an
            # INSTRUCTIONS AND INFORMATION block that spans 3 pages
            # (e.g. CAT P1 has items 1\u201320 over pages 2\u20133).
            for p in pdf.pages[:5]:
                try:
                    cover_text += '\n' + (p.extract_text() or '')
                except Exception:
                    pass
    except Exception:
        try:
            from pypdf import PdfReader
        except Exception:
            try:
                from PyPDF2 import PdfReader  # type: ignore
            except Exception:
                return out
        try:
            reader = PdfReader(pdf_path)
            cover_text = '\n'.join((p.extract_text() or '')
                                   for p in reader.pages[:5])
        except Exception:
            return out

    if not cover_text:
        return out

    # MARKS:  150
    m = re.search(r'(?im)^\s*MARKS\s*[:\-]?\s*(\d{1,3})\b', cover_text)
    if m:
        try:
            out['total_marks'] = int(m.group(1))
        except Exception:
            pass
    # TIME:  3 hours / 2 1/2 hours / 180 minutes
    m = re.search(r'(?im)^\s*TIME\s*[:\-]?\s*([0-9½¼¾\.\s/]+)\s*(hour|hr|min)',
                  cover_text)
    if m:
        raw = m.group(1).strip()
        unit = m.group(2).lower()
        # Resolve simple fractions / decimals.
        raw = (raw.replace('½', '.5').replace('¼', '.25').replace('¾', '.75'))
        # "2 1/2" -> "2.5"
        f = re.match(r'(\d+)\s+1/2', raw)
        if f:
            raw = f.group(1) + '.5'
        try:
            val = float(raw)
            out['duration_minutes'] = int(val * 60) if unit.startswith(('hour', 'hr')) else int(val)
        except Exception:
            pass
    # COMPUTER APPLICATIONS TECHNOLOGY P1
    m = re.search(r'(?im)^\s*([A-Z][A-Z &/\-]+?)\s+(P\d)\s*$', cover_text)
    if m:
        out['subject_caps'] = m.group(1).strip()
        out['paper_number'] = m.group(2).strip()
    # MAY/JUNE 2025  or  NOVEMBER 2024
    m = re.search(r'(?im)^\s*((?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z/]*?)\s+(\d{4})\s*$',
                  cover_text)
    if m:
        out['month'] = m.group(1).strip()
        out['year'] = int(m.group(2))

    # ---- INSTRUCTIONS AND INFORMATION block (typically pages 2-3) ----
    # We pull the whole "INSTRUCTIONS AND INFORMATION" section and store it
    # as a list of \n-separated numbered lines so paper_print.html can
    # render it as the official numbered instructions page.
    #
    # First strip the running header/footer noise that appears between
    # pages ("Copyright reserved", "Please turn over", "DBE/May/June 2025",
    # "SC/NSC Confidential", page numbers) so the instructions block can
    # span multiple pages without the regex tripping over a footer.
    instr_text = cover_text
    # Footer / running-header noise (each pattern matches one whole line).
    instr_text = re.sub(r'(?im)^\s*copyright\s+reserved(?:\s+please\s+turn\s+over)?\s*$', '', instr_text)
    instr_text = re.sub(r'(?im)^\s*please\s+turn\s+over\s*$', '', instr_text)
    instr_text = re.sub(r'(?im)^\s*SC\s*/\s*NSC[^\n]*$', '', instr_text)
    instr_text = re.sub(r'(?im)^[^\n]*?DBE\s*/\s*[A-Za-z]+/?[A-Za-z]*\s*\d{4}\s*$', '', instr_text)
    instr_text = re.sub(r'(?im)^[^\n]*?/\s*P\d+\s+\d{1,3}\s+DBE\s*/[^\n]*$', '', instr_text)
    instr_text = re.sub(r'\n{3,}', '\n\n', instr_text)

    m = re.search(r'(?is)INSTRUCTIONS\s+AND\s+INFORMATION\s*\n(.*?)(?=\n\s*(?:SECTION\s+[A-Z]\b|QUESTION\s+\d|SCENARIO\b|\Z))',
                  instr_text)
    if m:
        block = m.group(1)
        # Pre-pass: ensure every "N." item-marker starts on its own line.
        # The PDF's text layout sometimes flows item N onto the same line
        # as the tail of item N-1 (e.g. "...power failures.10. You may...").
        block = re.sub(r'(?<=[a-z\.])\s*(\d{1,2}[\.\)])\s+(?=[A-Z])',
                       r'\n\1 ', block)
        # Split into items at "1." / "2." / "10." line starts.
        # Tokens are: number, dot/paren, body until the next number or EOF.
        items = re.split(r'(?m)^\s*(\d{1,2})[\.\)]\s+', block)
        # re.split returns ['', '1', 'body1', '2', 'body2', ...]
        out_items = []
        for i in range(1, len(items) - 1, 2):
            num = items[i]
            body = items[i + 1].strip()
            # Drop running header / footer noise that may have leaked in.
            body = re.sub(r'(?im)^\s*(?:copyright reserved|please turn over|SC/NSC[^\n]*|\d{4}\s*$)$\n?', '', body)
            body = re.sub(r'(?im)^[A-Za-z][^\n]*?/P\d+\s+\d{1,3}\s+DBE/[^\n]*$\n?', '', body)
            # Normalise bullet markers (\u2022, \u25cf, hyphen-bullets,
            # plus Symbol-font PUA glyph U+F0B7 left over from PDF
            # extraction) to "\u2022".
            body = body.replace('\uf0b7', '\u2022') \
                       .replace('\uf0a7', '\u2022') \
                       .replace('\uf076', '\u2022') \
                       .replace('\uf0a8', '\u2022')
            body = re.sub(r'(?m)^[\s]*[\u2022\u25cf\u25aa\u25a0\u2043]\s+', '\u2022 ', body)
            # Force every bullet to start on its own line.
            body = re.sub(r'\s*\u2022\s+', '\n\u2022 ', body)
            # Drop file-list pollution: bullets that begin with a digit.
            body = re.sub(r'(?m)^\u2022\s+\d[^\n]*$\n?', '', body)
            # Walk the body line-by-line and emit a structured block list:
            # each block is either a bullet line ("\u2022 \u2026") or a text
            # paragraph. Continuation lines (PDF wraps) are folded into the
            # previous block; standalone lines ending with ":" become their
            # own paragraph (e.g. "Do the following:"); a non-bullet line
            # that follows a bullet that already ends in sentence
            # punctuation becomes a new trailing paragraph.
            src_lines = [ln.rstrip() for ln in body.split('\n')]
            blocks = []
            cur_text = []
            last_was_bullet = False
            def _flush():
                if cur_text:
                    blocks.append(' '.join(cur_text).strip())
                    cur_text.clear()
            for ln in src_lines:
                s = ln.strip()
                if not s:
                    _flush()
                    last_was_bullet = False
                    continue
                if s.startswith('\u2022'):
                    _flush()
                    blocks.append('\u2022 ' + s[1:].strip())
                    last_was_bullet = True
                elif last_was_bullet:
                    # Continuation of last bullet if previous bullet doesn't
                    # end with sentence punctuation; otherwise a trailing
                    # paragraph.
                    prev = blocks[-1][2:].strip()
                    if prev and prev[-1] not in '.!?':
                        blocks[-1] = blocks[-1] + ' ' + s
                    else:
                        last_was_bullet = False
                        cur_text.append(s)
                else:
                    # Non-bullet line. If it ends with ":" and we already have
                    # text in cur_text, treat it as a separate "lead-in"
                    # paragraph (e.g. "Do the following:").
                    if s.endswith(':') and cur_text:
                        _flush()
                        blocks.append(s)
                    else:
                        cur_text.append(s)
            _flush()
            # Final pass: kill any trailing "Copyright reserved [Please turn over]"
            blocks = [re.sub(r'\s*Copyright\s+reserved(?:\s+Please\s+turn\s+over)?\s*$', '', b, flags=re.I).strip()
                      for b in blocks]
            blocks = [b for b in blocks if b]
            if blocks:
                # Within an item, blocks are separated by single \n. Items
                # are separated by a blank line (\n\n).
                out_items.append('\n'.join(blocks))
        if out_items:
            # Items are separated by a blank line (\n\n). Bullets within an
            # item stay on their own \n-line so the template can render
            # them as a nested <ul>.
            out['instructions'] = '\n\n'.join(out_items)

    # ---- File-list page (e.g. CAT P1 "list of files in the folder") ----
    # The DBE PDF places a bulleted two-column list (filename + file type)
    # on the page immediately after the INSTRUCTIONS section. Detect those
    # lines in the raw cover_text and emit a structured list so the
    # template can render them as a separate page.
    file_types_re = (
        r'(Word\s+processing\s+(?:file|document)|Spreadsheet|Database|'
        r'HTML\s+file|Image|Folder|PDF\s+file|Presentation|Text\s+file)'
    )
    # Filename: short token of letters/digits/underscores/dots only (e.g.
    # "1eSports", "6_1Tournament", "7SA"). File-type token must occupy the
    # tail of the line and match the known set above.
    fl_pat = re.compile(
        r'(?im)^\s*[\u2022\u25cf\u25aa\u25a0\u2043\-]\s*'
        r'([A-Za-z0-9_][A-Za-z0-9_\-\.]{0,40})\s+'
        + file_types_re + r'\s*$'
    )
    data_files = []
    seen_names = set()
    for fm in fl_pat.finditer(cover_text):
        name = fm.group(1).strip()
        ftype = re.sub(r'\s+', ' ', fm.group(2)).strip()
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        data_files.append({'name': name, 'type': ftype})
    if data_files:
        import json as _json
        out['data_files'] = _json.dumps(data_files)

    return out


def _extract_memo_answers(mg_pdf_path):
    """Read a DBE marking-guideline PDF and return a flat dict mapping
    sub-item label ("1.1", "2.10", "4.1.1", "4.2", ...) to the answer
    text. Designed to be tolerant of the side-by-side two-column layout
    DBE uses for MCQ + Matching on page 2.

    Heuristic: any non-blank text line that starts with a digit-dot-digit
    label and ends with a 1-3 digit marks token is treated as a memo
    line. The answer is the text between the label and the trailing
    marks number. Continuation lines that don't start with a label are
    appended to the most recent label's answer.

    Also collects per-Question "(Note to marker: …)" preambles that
    appear between a "QUESTION N: …" header and the first 'N.x' answer
    line. Notes are exposed on the returned dict via a magic key
    ``__notes__`` mapping ``{qn: text}`` (qn is an int).
    """
    answers = {}
    notes = {}        # {int qn: str note}
    sub_tables = {}   # {label: [[header...], [row...], ...]} for
                      # nested 2-col comparison tables (DBE sometimes
                      # embeds a "System software | Application software"
                      # table inside an answer cell).
    try:
        import pdfplumber as _pp
    except Exception:
        answers['__notes__'] = notes
        answers['__tables__'] = sub_tables
        return answers
    if not mg_pdf_path or not os.path.exists(mg_pdf_path):
        answers['__notes__'] = notes
        answers['__tables__'] = sub_tables
        return answers
    # Line patterns. Marks token at end of line is 1-3 digits, optionally
    # followed by another 1-3 digit group total. Examples:
    #   "1.1 B  1"                       -> label 1.1, ans "B", marks 1
    #   "2.3 C  Section Break 1"         -> label 2.3, ans "C  Section Break"
    #   "3.1 False, Form  (do not...) 1" -> label 3.1, ans "False, Form  (do not...)"
    #   "4.1.1 64 GB  1"                 -> label 4.1.1, ans "64 GB"
    #   "4.1.5 (1) Features ...    2 8"  -> trailing "8" is group total
    _label_re = re.compile(
        r'^\s*(\d{1,2}(?:\.\d{1,3}){1,2})\s+(.+?)\s+(\d{1,3})(?:\s+(\d{1,3}))?\s*$')
    # Side-by-side: same physical row carries TWO labels (1.1 ... 2.1 ...).
    _dual_re = re.compile(
        r'^\s*(\d{1,2}\.\d{1,3})\s+(.+?)\s+(\d{1,3})\s+'
        r'(\d{1,2}\.\d{1,3})\s+(.+?)\s+(\d{1,3})\s*$')
    try:
        with _pp.open(mg_pdf_path) as pdf:
            last_label = None
            # Note-capture state: when a "QUESTION N: ..." header is
            # seen, start buffering any (Note to marker: ...) block that
            # follows, until either a closing ")" appears or the first
            # 'N.x' answer line begins.
            note_qn = None      # int qn currently buffering note for
            note_buf = []       # collected lines (without the leading "(Note to marker:")
            note_done = set()   # qns already finalised
            note_label_seen = set()  # qns for which any N.x label has been seen
            for page in pdf.pages:
                text = page.extract_text() or ''
                # ---- Detect nested 2-column comparison tables embedded
                # inside an outer answer cell (e.g. "System software |
                # Application software" comparing rows). The outer memo
                # table is the largest table on the page; any additional
                # table whose bbox sits inside one of the outer answer
                # cells is the nested data we want.
                try:
                    _pg_tables = page.find_tables() or []
                except Exception:
                    _pg_tables = []
                if len(_pg_tables) >= 1:
                    _pg_tables_sorted = sorted(
                        _pg_tables,
                        key=lambda _t: -((_t.bbox[2] - _t.bbox[0])
                                         * (_t.bbox[3] - _t.bbox[1])))
                    _outer = _pg_tables_sorted[0]
                    try:
                        _outer_rows = _outer.extract() or []
                    except Exception:
                        _outer_rows = []
                    # Build {label: bbox-of-2nd-column-cell}.
                    _lbl_to_bbox = {}
                    _lbl_to_rowtxt = {}  # {label: 2nd-col text}
                    try:
                        for _r_idx, _trow in enumerate(_outer.rows):
                            _cells = getattr(_trow, 'cells', None) or []
                            if len(_cells) < 2 or not _cells[1]:
                                continue
                            _lbl_txt = (_outer_rows[_r_idx][0]
                                        if _r_idx < len(_outer_rows)
                                        else '') or ''
                            _lbl_first = _lbl_txt.strip().split()
                            if not _lbl_first:
                                continue
                            _lbl = _lbl_first[0].rstrip('.')
                            if re.match(r'^\d+(?:\.\d+)+$', _lbl):
                                _lbl_to_bbox[_lbl] = _cells[1]
                                _ans_cell = (_outer_rows[_r_idx][1]
                                             if len(_outer_rows[_r_idx]) > 1
                                             else '') or ''
                                _lbl_to_rowtxt[_lbl] = _ans_cell
                    except Exception:
                        pass
                    # Fallback: capture answers from outer-table rows
                    # for labels that the text-line regex missed
                    # (multi-line answers where the trailing marks token
                    # lives on a different line, e.g. "4.8. Explain
                    # multitasking\nMultitasking allows…\n1").
                    for _lbl, _ans_cell in _lbl_to_rowtxt.items():
                        if _lbl in answers:
                            continue
                        # Strip trailing marks token "(\d+)" left over
                        # from the inline DBE format.
                        _clean = re.sub(
                            r'\s+\d{1,3}\s*$', '',
                            _ans_cell.strip())
                        _clean = re.sub(
                            r'[\u2713\u2714\u2715\u2717\u2718]+', '',
                            _clean).strip()
                        if _clean:
                            answers[_lbl] = _clean
                    for _nt in _pg_tables_sorted[1:]:
                        _nb = _nt.bbox
                        for _lbl, _ab in _lbl_to_bbox.items():
                            if _ab and (_nb[0] >= _ab[0] - 2
                                        and _nb[2] <= _ab[2] + 2
                                        and _nb[1] >= _ab[1] - 2
                                        and _nb[3] <= _ab[3] + 2):
                                try:
                                    _nrows = _nt.extract() or []
                                except Exception:
                                    _nrows = []
                                _cleaned = [
                                    [re.sub(
                                        r'\s+', ' ',
                                        (c or '').replace('\n', ' ')).strip()
                                     for c in r]
                                    for r in _nrows
                                ]
                                _cleaned = [r for r in _cleaned if any(r)]
                                if _cleaned and len(_cleaned[0]) >= 2:
                                    sub_tables[_lbl] = _cleaned
                                break
                for raw in text.split('\n'):
                    ln = raw.rstrip()
                    if not ln.strip():
                        last_label = None
                        continue
                    # Detect "QUESTION N: <title>" header (start of a new
                    # potential note region).
                    _qh = re.match(r'^\s*QUESTION\s+(\d{1,2})\b', ln)
                    if _qh:
                        # Finalise any in-flight note from prior question.
                        if note_qn is not None and note_buf and note_qn not in note_done:
                            _final = [x for x in note_buf if x and x != '__OPEN__']
                            if _final and any(x.startswith('\u2022') for x in _final):
                                notes[note_qn] = '\n'.join(_final).strip()
                                note_done.add(note_qn)
                        note_qn = int(_qh.group(1))
                        note_buf = []
                        continue
                    # Detect "(Note to marker:" opening — start buffering.
                    # Only honour this BEFORE any answer label has been
                    # emitted for the current question, otherwise mid-
                    # question notes will swallow the rest of the page.
                    if note_qn is not None and note_qn not in note_done \
                            and note_qn not in note_label_seen \
                            and re.match(r'^\s*\(?\s*Note\s+to\s+marker', ln, re.I):
                        # Drop the leading "(Note to marker:" prefix.
                        _cleaned = re.sub(
                            r'^\s*\(?\s*Note\s+to\s+marker\s*:?\s*', '',
                            ln, flags=re.I).strip()
                        # Mark the buffer as "open" even when the rest
                        # of the line is empty (bullets follow on next
                        # lines). Use a sentinel so subsequent bullet
                        # captures know we're inside a note block.
                        note_buf.append(_cleaned if _cleaned else '__OPEN__')
                        continue
                    # While in note-buffering mode (note_buf has at least
                    # one entry — sentinel or real), capture bullets and
                    # fold continuation lines.
                    if (note_qn is not None and note_qn not in note_done
                            and note_qn not in note_label_seen
                            and note_buf):
                        _s = ln.strip()
                        # If the line is the FIRST answer label for this
                        # qn (e.g. "3.1 ..."), do NOT fold it into the
                        # note — fall through to the label handler so
                        # the note finalises and the answer is captured.
                        _peek = _label_re.match(ln)
                        if not (_peek and _peek.group(1).split('.', 1)[0] == str(note_qn)):
                            if _s.startswith('\u2022'):
                                # New bullet — strip trailing ").","))" etc.
                                if _s.endswith(').'):
                                    _s = _s[:-2].rstrip()
                                elif _s.endswith(')'):
                                    _s = _s[:-1].rstrip()
                                note_buf.append(_s)
                                continue
                            if note_buf[-1].startswith('\u2022'):
                                # Strip trailing "."/")" from continuation.
                                if _s.endswith(').'):
                                    _s = _s[:-2].rstrip()
                                elif _s.endswith(')'):
                                    _s = _s[:-1].rstrip()
                                note_buf[-1] = note_buf[-1] + ' ' + _s
                                continue
                    md = _dual_re.match(ln)
                    if md:
                        for lbl, ans, _mk in (
                            (md.group(1), md.group(2), md.group(3)),
                            (md.group(4), md.group(5), md.group(6)),
                        ):
                            ans = ans.strip()
                            # Drop bare check-tick glyphs the MG inserts
                            # after MCQ letters (✓, ✔, ).
                            ans = re.sub(r'[\u2713\u2714\u2715\u2717\u2718]+', '',
                                         ans).strip()
                            if ans:
                                answers[lbl] = ans
                            last_label = lbl
                            try:
                                note_label_seen.add(int(lbl.split('.', 1)[0]))
                            except Exception:
                                pass
                        continue
                    m = _label_re.match(ln)
                    if m:
                        lbl = m.group(1)
                        # If this label belongs to the question whose
                        # note we're buffering, finalise the note now.
                        try:
                            _lbl_qn = int(lbl.split('.', 1)[0])
                        except Exception:
                            _lbl_qn = None
                        if (note_qn is not None and _lbl_qn == note_qn
                                and note_qn not in note_done and note_buf):
                            _final = [x for x in note_buf if x and x != '__OPEN__']
                            # Only finalise if all buffered lines look
                            # like real note content (start with a bullet
                            # or contain "(Note to marker" residue).
                            _looks_like_note = any(
                                x.startswith('\u2022') for x in _final)
                            if _final and _looks_like_note:
                                notes[note_qn] = '\n'.join(_final).strip()
                                note_done.add(note_qn)
                            note_buf = []
                        ans = m.group(2).strip()
                        ans = re.sub(r'[\u2713\u2714\u2715\u2717\u2718]+', '',
                                     ans).strip()
                        if ans:
                            answers[lbl] = ans
                        last_label = lbl
                        if _lbl_qn is not None:
                            note_label_seen.add(_lbl_qn)
                    else:
                        # Continuation. If we're still inside a note
                        # block (no answer line yet for this qn), append
                        # the line to the note buffer; otherwise treat
                        # it as a continuation of the previous answer.
                        if (note_qn is not None and note_qn not in note_done
                                and note_qn not in note_label_seen
                                and note_buf):
                            _cont = ln.strip()
                            if _cont.endswith(').'):
                                _cont = _cont[:-2].rstrip()
                            elif _cont.endswith(')'):
                                _cont = _cont[:-1].rstrip()
                            if _cont:
                                note_buf.append(_cont)
                            continue
                        # Continuation line — append to last label's answer.
                        if last_label and last_label in answers:
                            extra = ln.strip()
                            extra = re.sub(r'[\u2713\u2714\u2715\u2717\u2718]+', '',
                                           extra).strip()
                            if extra:
                                answers[last_label] = (
                                    answers[last_label] + '\n' + extra)
            # Finalise any in-flight note left over at EOF.
            if note_qn is not None and note_buf and note_qn not in note_done:
                _final = [x for x in note_buf if x and x != '__OPEN__']
                if _final and any(x.startswith('\u2022') for x in _final):
                    notes[note_qn] = '\n'.join(_final).strip()
    except Exception:
        pass
    answers['__notes__'] = notes
    answers['__tables__'] = sub_tables
    return answers


def _find_sibling_memo_pdf(paper_pdf_path):
    """Given a past-paper PDF path, find a matching marking-guideline PDF
    in the same folder. DBE memos are typically named the same as the
    question paper with "MG" added (or " MG" before "Eng"). Returns the
    absolute path or None."""
    if not paper_pdf_path or not os.path.exists(paper_pdf_path):
        return None
    folder = os.path.dirname(paper_pdf_path)
    base = os.path.basename(paper_pdf_path)
    base_no_ext, ext = os.path.splitext(base)
    bn_lower = base_no_ext.lower()
    if ' mg ' in bn_lower or bn_lower.endswith(' mg'):
        return None  # already a memo
    # Try a few common patterns the DBE uses.
    candidates = []
    # "... May-June 2025 Eng.pdf" -> "... May-June 2025 MG Eng.pdf"
    if ' Eng' in base_no_ext:
        candidates.append(base_no_ext.replace(' Eng', ' MG Eng') + ext)
    # "... .pdf" -> "... MG.pdf"
    candidates.append(base_no_ext + ' MG' + ext)
    # Whitespace-normalised lookup (handles "P2 May-June 2025  Eng.pdf"
    # with double spaces matching the canonical single-space MG name).
    def _norm(s):
        return re.sub(r'\s+', ' ', s).strip().lower()
    folder_files = os.listdir(folder) if os.path.isdir(folder) else []
    norm_to_real = {_norm(fn): fn for fn in folder_files}
    for cand in list(candidates):
        nf = norm_to_real.get(_norm(cand))
        if nf and nf not in candidates:
            candidates.append(nf)
    # Loose: substring match across the folder. Require shared YEAR and
    # PAPER number tokens (P1/P2) so we never cross-match papers.
    src_tokens = set(re.findall(r'[a-z0-9]+', base_no_ext.lower()))
    src_year = next((t for t in src_tokens
                     if re.fullmatch(r'20\d{2}', t)), None)
    src_pn = next((t for t in src_tokens if t in ('p1', 'p2')), None)
    for fn in folder_files:
        if fn.lower().endswith('.pdf') and ' mg ' in (' ' + fn.lower() + ' '):
            fn_tokens = set(re.findall(r'[a-z0-9]+', fn.lower()))
            if src_year and src_year not in fn_tokens:
                continue
            if src_pn and src_pn not in fn_tokens:
                continue
            if len(src_tokens & fn_tokens) >= max(3, len(src_tokens) // 2):
                candidates.append(fn)
    for cand in candidates:
        full = os.path.join(folder, cand)
        if os.path.exists(full):
            return full
    return None


def _parse_past_paper_pdf(pdf_path, strict=False):
    """Extract a list of sections from a DBE-style past paper PDF.

    Returns: [
        {'title': 'SECTION A', 'instructions': '...', 'questions': [
            {'number': '1', 'text': '...full question + sub-questions...', 'marks': 25},
            ...
        ]},
        ...
    ]
    Falls back to a single 'Section A' if no SECTION headers are found.
    Each "QUESTION N" becomes one item; sub-questions (1.1, 1.1.1, etc.)
    stay inside the parent question's text so the teacher can edit them
    inline. Headers/footers and the cover page are best-effort skipped.
    When strict=True, preserve blank lines and indentation and do not
    truncate the question text.
    """
    # Prefer pdfplumber with layout=True so multi-column MCQ pages keep
    # their original column alignment (option letter on the left, option
    # text on the right). This is what makes the imported paper LOOK
    # like the original PDF when rendered in a monospaced textarea.
    pages_text = []
    try:
        import pdfplumber  # type: ignore
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                try:
                    pages_text.append(page.extract_text(layout=True,
                                                        x_density=7.25,
                                                        y_density=13) or '')
                except Exception:
                    try:
                        pages_text.append(page.extract_text() or '')
                    except Exception:
                        pages_text.append('')
    except Exception:
        # Fallback to pypdf if pdfplumber isn't available.
        try:
            from pypdf import PdfReader
        except Exception:
            from PyPDF2 import PdfReader  # type: ignore
        reader = PdfReader(pdf_path)
        for p in reader.pages:
            try:
                pages_text.append(p.extract_text() or '')
            except Exception:
                pages_text.append('')
    raw = '\n'.join(pages_text)
    if not raw.strip():
        return []
    # Normalise whitespace, strip obvious header/footer noise like
    # "Copyright reserved", "Please turn over", page numbers.
    # IMPORTANT: keep leading spaces — they are what aligns MCQ option
    # columns in the layout-preserving extraction.
    cleaned_lines = []
    for ln in raw.splitlines():
        body = ln.rstrip()
        s = body.strip()
        if not s:
            cleaned_lines.append('')
            continue
        if not strict:
            # skip pure page numbers
            if re.fullmatch(r'\d{1,3}', s):
                continue
            if re.search(r'(?i)copyright reserved', s):
                continue
            if re.search(r'(?i)please turn over', s):
                continue
            # DBE running header in any of these forms:
            #   "DBE/2021", "DBE/Nov 2021", "DBE/May/June 2025"
            if re.search(r'(?i)\bDBE/(?:[A-Za-z]+/?)*\s*\d{4}\b', s):
                continue
            # Page footer like "Computer Applications Technology/P2 4 DBE/2021"
            # — anything containing "<Subject>/P<n>  <page-no>  DBE/<year>".
            if re.search(r'(?i)/P\d+\s+\d{1,3}\s+DBE/', s):
                continue
            if re.search(r'(?i)^NSC|SC/NSC', s):
                continue
        # Map common Symbol-font bullet glyphs (PUA) to a real bullet
        # character before we strip the rest of the PUA range below.
        # PDF extractors often emit U+F0B7 (Symbol "•") and U+F076 etc.
        body = body.replace('\uf0b7', '\u2022').replace('\uf0a7', '\u2022') \
                   .replace('\uf076', '\u2022').replace('\uf0a8', '\u2022')
        # Strip private-use / control characters that pdfplumber sometimes
        # leaves behind for embedded images — those bytes can render as
        # broken-image icons when the field is later marked |safe.
        body = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ue000-\uf8ff\ufffd]', '', body)
        # Drop inline HTML/XML tags PDF text extraction can occasionally
        # produce (form-XObject wrappers, embedded XML). DO NOT strip
        # short literal tag tokens such as `<alt>`, `<a>`, `<br>` that
        # frequently appear as content in HTML-related answers in CAT
        # marking guides — only strip tags that have attributes
        # (whitespace + `=`), are closing tags (`</…>`), or are
        # self-closing (`<…/>`).
        body = re.sub(r'</[^>]{1,80}>', '', body)
        body = re.sub(r'<[^>]{1,80}/>', '', body)
        body = re.sub(r'<[A-Za-z][^>]*\s[^>]*=[^>]*>', '', body)
        cleaned_lines.append(body)
    # Collapse runs of >=2 blank lines into a single blank line unless
    # we are in strict mode (keep the original spacing for PDF fidelity).
    if strict:
        lines = cleaned_lines
    else:
        collapsed = []
        blank_run = 0
        for ln in cleaned_lines:
            if ln == '':
                blank_run += 1
                if blank_run <= 1:
                    collapsed.append('')
            else:
                blank_run = 0
                collapsed.append(ln)
        lines = collapsed

    # Walk lines, splitting into sections and questions.
    sections = []
    current_section = None
    current_question = None
    pending = []
    seen_section = False

    def _start_section(letter, rest):
        nonlocal current_section, current_question
        if current_question and current_section is not None:
            current_section['questions'].append(current_question)
            current_question = None
        title = f'SECTION {letter.upper()}'
        if rest:
            title = f'{title} — {rest.strip()}'
        current_section = {'title': title, 'instructions': '', 'questions': []}
        sections.append(current_section)

    def _start_question(num, rest, raw_line=None, prefix_lines=None):
        nonlocal current_question
        if current_question and current_section is not None:
            current_section['questions'].append(current_question)
        current_question = {'number': str(num), 'text': '', 'marks': 0}
        if strict:
            parts = []
            if prefix_lines:
                parts.extend(prefix_lines)
            if raw_line is not None:
                parts.append(raw_line)
            elif rest:
                parts.append(rest)
            current_question['text'] = '\n'.join(parts)
        elif rest:
            current_question['text'] = rest.strip()

    for ln in lines:
        m_sec = _PP_SECTION_RE.match(ln)
        m_q = _PP_QUESTION_RE.match(ln)
        if strict:
            if not ln.lstrip().startswith('SECTION'):
                m_sec = None
            if not ln.lstrip().startswith('QUESTION'):
                m_q = None
        if m_sec:
            if strict:
                pending = [ln]
                seen_section = True
            _start_section(m_sec.group(1), m_sec.group(2) or '')
            continue
        if m_q:
            if current_section is None:
                _start_section('A', '')
                if strict:
                    seen_section = True
            prefix = pending if strict else None
            pending = []
            _start_question(m_q.group(1), m_q.group(2) or '', raw_line=ln if strict else None, prefix_lines=prefix)
            continue
        # Not a header. Only accumulate text once we're inside a question;
        # otherwise it's cover-page / instructions noise we don't want
        # polluting the imported paper.
        if current_question is not None:
            if current_question['text']:
                current_question['text'] += '\n' + ln
            else:
                current_question['text'] = ln
        elif strict and seen_section:
            pending.append(ln)
        # Section-level instructions are intentionally skipped \u2014 the
        # editor lets the teacher add their own per-section instructions
        # and DBE cover instructions are auto-detected separately.
    # Flush the trailing question.
    if current_question and current_section is not None:
        current_section['questions'].append(current_question)

    # Post-process: extract question total marks from a trailing "[N]"
    # (DBE per-question total) or "(N)" near the end of the question text,
    # and trim the section instructions.
    _bracket_total = re.compile(r'\[\s*(\d{1,3})\s*\]')
    for sec in sections:
        sec['instructions'] = (sec.get('instructions') or '').strip()[:1500]
        for q in sec['questions']:
            txt = (q.get('text') or '')
            if not strict:
                txt = txt.strip()
            tail_lines = [l for l in txt.splitlines() if l.strip()]
            # 1) Prefer the last [N] marker anywhere in the final ~10 lines
            #    (DBE marks the per-question total this way).
            picked = 0
            for l in reversed(tail_lines[-12:]):
                m = _bracket_total.search(l)
                if m:
                    try:
                        picked = int(m.group(1)); break
                    except Exception:
                        pass
            # 2) Fall back to a trailing (N) on the very last line.
            if not picked and tail_lines:
                m = _PP_MARKS_TAIL_RE.search(tail_lines[-1])
                if m:
                    try:
                        picked = int(m.group(1))
                    except Exception:
                        pass
            if picked:
                q['marks'] = picked
            if not strict:
                # Strip the [N] total marker anywhere in the last few lines
                # since we now store it as q['marks'] (avoids it showing twice).
                txt = re.sub(r'\s*\[\s*\d{1,3}\s*\]\s*$', '', txt).rstrip()
                # Also strip any stand-alone "[N]" line that crept in mid-body
                # at the very end of the question.
                txt = re.sub(r'(?m)^\s*\[\s*\d{1,3}\s*\]\s*$', '', txt).rstrip()
                # Also strip a final "TOTAL SECTION X: NN" line if it crept in.
                txt = re.sub(r'(?im)^\s*TOTAL\s+SECTION\s+[A-Z][^\n]*$', '', txt).rstrip()
                # Dedent: pdfplumber's layout-preserving extractor leaves a
                # uniform left margin (often 6+ spaces). Strip the common
                # leading whitespace so the question sits flush in the editor
                # while preserving the *relative* indentation that aligns the
                # MCQ option columns.
                non_empty = [l for l in txt.splitlines() if l.strip()]
                if non_empty:
                    common = min((len(l) - len(l.lstrip(' '))) for l in non_empty)
                    if common > 0:
                        txt = '\n'.join(
                            (l[common:] if len(l) >= common else l)
                            for l in txt.splitlines()
                        )
                # Cap absurdly large blobs to keep the editor responsive.
                q['text'] = txt[:8000]
            else:
                q['text'] = txt

    # Drop any empty sections (e.g. cover-page scaffold with no questions).
    sections = [s for s in sections if s.get('questions')]
    return sections


# ---------- Question bank -----------------------------------------------
_SUBJECT_CANONICAL_NAMES = {
    'CAT': 'Computer Applications Technology',
    'IT': 'Information Technology',
    'BSTD': 'Business Studies',
    'BUS': 'Business Studies',
}


def _canonical_subject(name):
    value = (name or '').strip()
    return _SUBJECT_CANONICAL_NAMES.get(value, value)


def _generator_subject_choices():
    """Return full subject names available to the current teacher."""
    if not current_user.is_authenticated:
        return []
    if current_user.is_admin:
        stored = {
            _canonical_subject(subject)
            for (subject,) in db.session.query(QuestionBankItem.subject).distinct()
            if subject
        }
        stored.update(
            _canonical_subject(subject)
            for (subject,) in db.session.query(GeneratedPaper.subject).distinct()
            if subject
        )
        stored.update({'Computer Applications Technology', 'Business Studies'})
        return sorted(stored, key=str.lower)
    subjects = {
        _canonical_subject(subject)
        for subject in (current_user.subjects or '').split(',')
        if subject.strip()
    }
    return sorted(subjects, key=str.lower)


def _expand_subject_aliases(names):
    """Expand a set/list of subject names to include legacy short codes
    so we can match items stored under either 'CAT' or the full name."""
    out = set()
    for n in names:
        n = (n or '').strip()
        if not n:
            continue
        canonical = _canonical_subject(n)
        out.add(canonical)
        if canonical == 'Computer Applications Technology':
            out.add('CAT')
        elif canonical == 'Information Technology':
            out.add('IT')
        elif canonical == 'Business Studies':
            out.update({'BSTD', 'BUS'})
    return out


def _visible_subject_set():
    """Subjects (with legacy aliases) the current user is allowed to see.
    - Teachers / Moderators: only the subjects they registered with.
    - HODs: their own subjects + the subjects of every team member under them.
    - Admins: returns None (no restriction).
    Returns an empty set if the user has no subjects set (locks them out).
    """
    if not current_user.is_authenticated:
        return set()
    if current_user.is_admin:
        return None
    subjects = {s.strip() for s in (current_user.subjects or '').split(',') if s.strip()}
    if getattr(current_user, 'is_hod', False):
        team = User.query.filter(User.hod_id == current_user.id).all()
        for m in team:
            for s in (m.subjects or '').split(','):
                s = s.strip()
                if s:
                    subjects.add(s)
    return _expand_subject_aliases(subjects)


def _bank_visible_filter():
    """SQLAlchemy filter expression that scopes QuestionBankItem rows to what
    the current user is allowed to see in their bank list:
      - own questions
      - public questions (share_scope='public')
      - school questions (share_scope='school') from teachers at the same school
    Admins bypass this filter (caller checks current_user.is_admin).
    """
    own = QuestionBankItem.owner_id == current_user.id
    public = QuestionBankItem.share_scope == 'public'
    school = (current_user.school_name or '').strip()
    if school:
        school_owner_ids = (db.session.query(User.id)
                            .filter(db.func.lower(User.school_name) == school.lower())
                            .subquery())
        school_share = db.and_(
            QuestionBankItem.share_scope == 'school',
            QuestionBankItem.owner_id.in_(db.session.query(school_owner_ids.c.id))
        )
        base = db.or_(own, public, school_share)
    else:
        base = db.or_(own, public)
    subj_set = _visible_subject_set()
    if subj_set is None:
        return base
    if not subj_set:
        # No registered subjects → only the user's own items are visible.
        return own
    return db.and_(base, QuestionBankItem.subject.in_(subj_set))


@app.route('/teacher/bank')
@teacher_required
def teacher_bank():
    grade = request.args.get('grade', type=int)
    subject = request.args.get('subject', '').strip()
    topic_list = [t.strip() for t in request.args.getlist('topic') if t.strip()]
    diff = request.args.get('difficulty', '').strip()
    paper = request.args.get('paper', '').strip()
    server_filter = request.args.get('server_filter') == '1'
    # Owner scope: 'mine' = only my own questions, anything else = all visible.
    owner_scope = (request.args.get('owner') or 'all').strip().lower()
    if owner_scope not in ('all', 'mine'):
        owner_scope = 'all'

    # Map full subject names back to legacy short codes used by older items.
    _bank_subject_aliases = {
        'Computer Applications Technology': ['Computer Applications Technology', 'CAT'],
        'Information Technology': ['Information Technology', 'IT'],
    }

    # Teachers/HODs see: their own questions, public-shared questions,
    # and school-shared questions from teachers at the same school.
    # Admins see everything.
    if current_user.is_admin:
        base_q = QuestionBankItem.query
    else:
        base_q = QuestionBankItem.query.filter(_bank_visible_filter())
    if owner_scope == 'mine':
        base_q = base_q.filter(QuestionBankItem.owner_id == current_user.id)

    q = base_q
    if server_filter:
        if grade:
            q = q.filter_by(grade=grade)
        if subject:
            aliases = _bank_subject_aliases.get(subject, [subject])
            q = q.filter(QuestionBankItem.subject.in_(aliases))
        if topic_list:
            q = q.filter(QuestionBankItem.topic.in_(topic_list))
        if diff:
            q = q.filter_by(difficulty=diff)
        if paper:
            # Match the paper label as a whole tag entry within the comma-separated tags string
            like_a = f"%, {paper},%"      # middle position
            like_b = f"{paper},%"          # first position
            like_c = f"%, {paper}"        # last position
            like_d = paper                  # only tag
            q = q.filter(db.or_(
                QuestionBankItem.tags.like(like_a),
                QuestionBankItem.tags.like(like_b),
                QuestionBankItem.tags.like(like_c),
                QuestionBankItem.tags == like_d,
            ))
    items = q.order_by(QuestionBankItem.created_at.desc()).all()

    # Build dropdown lists from full bank
    all_items = base_q.order_by(QuestionBankItem.created_at.desc()).all()

    # Subject -> sorted topic list (so the Topic dropdown can update when
    # the user picks a Subject). Uses the expanded subject name as key.
    _bank_abbr_to_full_t = {'CAT': 'Computer Applications Technology', 'IT': 'Information Technology'}
    topics_by_subject = {}
    for i in all_items:
        if not i.topic:
            continue
        subj_full = _bank_abbr_to_full_t.get(i.subject, i.subject) or ''
        topics_by_subject.setdefault(subj_full, set()).add(i.topic)

    # Curated CAPS topic lists per subject (DBE FET Grades 10-12 main topics).
    # Merged with whatever topics already exist in the bank so admins can extend.
    caps_topics_by_subject = {
        'Accounting': [
            'Accounting Equation', 'Bank Reconciliation', 'Budgeting',
            'Cash Flow Statement', 'Companies — Financial Statements',
            'Companies — Ledger Accounts', 'Cost Accounting',
            'Creditors Reconciliation', 'Debtors Reconciliation',
            'Ethics & Internal Control', 'Fixed Assets', 'GAAP Principles',
            'Inventory Systems', 'Manufacturing', 'Partnerships',
            'Professional Bodies', 'Ratio Analysis & Interpretation',
            'Reconciliations', 'Salaries & Wages', 'Sole Trader Accounts',
            'VAT',
        ],
        'Business Studies': [
            'Business Environments', 'Business Operations', 'Business Roles',
            'Business Ventures', 'Contracts', 'Corporate Social Responsibility',
            'Creative Thinking & Problem Solving', 'Forms of Ownership',
            'Human Resources Function', 'Insurance', 'Investment — Securities',
            'Investment — Insurance', 'Leadership & Management',
            'Macro Environment — PESTLE', 'Marketing Function', 'Micro Environment',
            'Presentation of Business Information', 'Production Function',
            'Professionalism & Ethics', 'Quality of Performance',
            'Stress, Crisis & Conflict Management', 'Team Performance',
        ],
        'Economics': [
            'Basic Economic Problem', 'Business Cycles', 'Circular Flow',
            'Demand & Supply', 'Dynamics of Markets', 'Economic Growth & Development',
            'Economic Indicators', 'Economic Pursuits', 'Economic Redress',
            'Economic Systems', 'Environmental Sustainability',
            'Foreign Exchange Markets', 'Globalisation', 'Inflation',
            'International Trade', 'Money & Banking', 'Perfect Markets',
            'Imperfect Markets', 'Production Possibilities',
            'Public Sector', 'South African Economy', 'Tourism',
            'Unemployment & Labour',
        ],
        'Mathematics': [
            'Algebra & Equations', 'Analytical Geometry', 'Calculus',
            'Counting & Probability', 'Data Handling & Statistics',
            'Differential Calculus', 'Euclidean Geometry', 'Exponents & Surds',
            'Finance, Growth & Decay', 'Functions & Graphs', 'Inequalities',
            'Number Patterns, Sequences & Series', 'Polynomials',
            'Probability', 'Statistics — Regression & Correlation',
            'Trigonometry', 'Trigonometry — 2D & 3D Problems',
            'Trigonometry — Identities', 'Trigonometry — Reduction Formulae',
        ],
        'Mathematical Literacy': [
            'Conversions & Time', 'Data Handling', 'Finance — Banking',
            'Finance — Budgets', 'Finance — Income, Expenditure, Profit & Loss',
            'Finance — Interest, Loans & Investments', 'Finance — Tariffs',
            'Finance — Taxation', 'Maps, Plans & Other Representations',
            'Measurement — Conversions', 'Measurement — Length, Distance & Speed',
            'Measurement — Perimeter, Area & Volume', 'Measurement — Time',
            'Numbers & Calculations', 'Patterns, Relationships & Representations',
            'Probability', 'Ratio, Rate & Proportion',
        ],
        'Physical Sciences': [
            'Atomic Combinations & Bonding', 'Atomic Structure',
            'Chemical Change — Acids & Bases', 'Chemical Change — Electrochemistry',
            'Chemical Change — Energy & Rates', 'Chemical Change — Equilibrium',
            'Chemical Change — Stoichiometry', 'Chemical Systems — Fertilisers',
            'Chemical Systems — Industrial Processes',
            'Electric Circuits', 'Electrodynamics', 'Electromagnetism',
            'Electrostatics', 'Geometric Optics', 'Matter & Materials',
            'Mechanics — Momentum & Impulse', 'Mechanics — Newton\u2019s Laws',
            'Mechanics — Vertical Projectile Motion', 'Mechanics — Work, Energy & Power',
            'Organic Chemistry', 'Particles Substances are Made Of',
            'Sound & Doppler Effect', 'States of Matter & Kinetic Theory',
            'Waves & Light',
        ],
        'Life Sciences': [
            'Animal Nutrition', 'Biodiversity & Classification',
            'Biospheres to Ecosystems', 'Cell Division — Mitosis',
            'Cell Structure & Function', 'Chemistry of Life', 'DNA, RNA & Protein Synthesis',
            'Endocrine System', 'Energy Transformations to Sustain Life',
            'Environmental Studies', 'Evolution', 'Excretion',
            'Genetics & Inheritance', 'History of Life on Earth',
            'Homeostasis', 'Human Endocrine System', 'Human Impact on the Environment',
            'Human Nervous System', 'Human Reproduction', 'Meiosis',
            'Photosynthesis', 'Plant Reproduction', 'Plant Tissues',
            'Population Ecology', 'Respiration in Humans', 'Support & Transport in Plants',
            'The Eye, Ear & Skin',
        ],
        'Geography': [
            'Atmosphere — Climate & Weather', 'Atmosphere — Climate Change',
            'Climatology', 'Drainage Systems & Fluvial Processes',
            'Economic Geography of South Africa', 'Geographical Skills & Techniques',
            'Geomorphology', 'Map Work & GIS', 'People & Places',
            'Population & Settlement', 'Resources & Sustainability',
            'Rural & Urban Settlement', 'South African Geography',
            'Tropical Cyclones & Mid-Latitude Cyclones', 'Water Resources',
        ],
        'History': [
            'Apartheid South Africa 1940s\u20131960s',
            'Civil Resistance 1970s\u20131980s', 'Civil Society Protests 1950s\u20131970s',
            'Coming of Democracy in South Africa', 'Cold War',
            'End of the Cold War & a New World Order',
            'European Society in the 15th\u201316th Century',
            'French Revolution', 'Globalisation', 'Independent Africa',
            'Industrial Revolution', 'Nationalisms — Middle East, Africa & SA',
            'Pseudo-Sciences & Race in 19th Century',
            'Russian Revolution', 'South Africa 1910\u20131948 — Segregation',
            'The Crisis of Capitalism — Great Depression',
            'The World after WWI', 'Transformation of the World by 1750',
            'Truth & Reconciliation Commission',
            'World War I', 'World War II',
        ],
        'English Home Language': [
            'Comprehension', 'Creative Writing — Essay',
            'Creative Writing — Transactional', 'Drama', 'Figurative Language',
            'Film Study', 'Language in Context', 'Literary Essay',
            'Novel', 'Poetry — Seen', 'Poetry — Unseen',
            'Short Stories', 'Summary Writing', 'Visual Literacy',
        ],
        'English FAL': [
            'Comprehension', 'Creative Writing — Essay',
            'Creative Writing — Transactional', 'Language Structures & Conventions',
            'Literature — Drama', 'Literature — Novel', 'Literature — Poetry',
            'Literature — Short Stories', 'Summary Writing', 'Visual Literacy',
        ],
        'Afrikaans Home Language': [
            'Begripstoets', 'Drama', 'Letterkunde', 'Mondeling',
            'Opsomming', 'Poësie — Gesien', 'Poësie — Ongesien',
            'Roman', 'Skryf — Kreatiewe Opstel', 'Skryf — Transaksioneel',
            'Taal in Konteks', 'Visuele Geletterdheid',
        ],
        'Afrikaans FAL': [
            'Begrip', 'Letterkunde — Drama', 'Letterkunde — Roman',
            'Letterkunde — Kortverhale', 'Letterkunde — Poësie',
            'Mondeling', 'Opsomming', 'Skryf — Opstel',
            'Skryf — Transaksioneel', 'Taalstrukture & -konvensies',
            'Visuele Geletterdheid',
        ],
        'Computer Applications Technology': [
            'Database (Access)', 'File Management', 'HTML & Web Design',
            'Hardware', 'Information Management', 'Internet & Networks',
            'Network Technologies', 'PAT — Phase 1 (Investigate)',
            'PAT — Phase 2 (Process & Present)', 'Presentations (PowerPoint)',
            'Social Implications', 'Software', 'Spreadsheets (Excel)',
            'System Technologies', 'Word Processing (Word)',
        ],
        'Information Technology': [
            'Application Development', 'Communication Technologies',
            'Data & Information Management', 'Database Design (SQL)',
            'Delphi/Pascal Programming', 'GUI Components',
            'Hardware & System Software', 'Internet Technologies',
            'Networks & Internet', 'Object-Oriented Programming',
            'PAT — Solution Development', 'Problem Solving & Algorithms',
            'Programming Concepts', 'Social Implications',
            'Software Engineering Principles', 'System Technologies',
        ],
        'Life Orientation': [
            'Careers & Career Choices', 'Citizenship Education',
            'Democracy & Human Rights', 'Development of the Self in Society',
            'Physical Education', 'Recreation & Physical Wellbeing',
            'Social & Environmental Responsibility', 'Study Skills',
            'World of Work',
        ],
        'Tourism': [
            'Communication & Customer Care', 'Culture & Heritage Tourism',
            'Domestic, Regional & International Tourism',
            'Foreign Exchange', 'Geography of Tourism — Maps & Routes',
            'Marketing', 'Responsible & Sustainable Tourism',
            'Sectors of the Tourism Industry', 'Time Zones',
            'Tourism Attractions', 'Tourism Sectors', 'Travel Documents & Procedures',
            'World Heritage Sites',
        ],
        'Consumer Studies': [
            'Consumer Rights & Responsibilities', 'Design Elements & Principles',
            'Entrepreneurship', 'Fibres, Fabrics & Clothing',
            'Food Production', 'Food & Nutrition',
            'Housing & Furnishings', 'Management of the Consumer Role',
            'Marketing', 'Production & Marketing of Goods',
            'Sustainable Living',
        ],
        'Hospitality Studies': [
            'Food & Beverage Service', 'Food Commodities',
            'Food Preparation', 'Food & Beverage Costing',
            'Hospitality Industry & Sectors', 'Hygiene, Safety & Security',
            'Kitchen & Restaurant Operations', 'Menu Planning',
            'Nutrition', 'Sectors & Careers',
        ],
        'Agricultural Sciences': [
            'Agricultural Management & Marketing', 'Animal Health & Diseases',
            'Animal Nutrition', 'Animal Production, Protection & Control',
            'Animal Reproduction', 'Basic Agricultural Chemistry',
            'Basic Agricultural Genetics', 'Biological Concepts',
            'Plant Production', 'Plant Reproduction & Propagation',
            'Soil Science', 'Sustainable Use of Natural Resources',
        ],
        'Engineering Graphics & Design': [
            'Analytical (Mechanical) Drawing', 'Analytical (Civil) Drawing',
            'Civil Drawing — Floor Plans, Elevations, Sections',
            'Descriptive Geometry', 'Electrical Diagrams',
            'Freehand Drawing & Sketching', 'Isometric Drawing',
            'Loci', 'Mechanical Assembly Drawing',
            'Orthographic Projection', 'Perspective Drawing',
            'Sectional Views', 'Solid Geometry — Interpenetration & Development',
        ],
        'Dramatic Arts': [
            'Acting & Performance', 'Costume, Make-up & Set Design',
            'History of Theatre', 'Improvisation',
            'Movement & Voice', 'Performance Analysis',
            'Play Texts — Contemporary', 'Play Texts — South African',
            'Production & Direction', 'Theatre Practitioners',
        ],
        'Music': [
            'Aural & Theory', 'Composition', 'General Music Knowledge',
            'Harmony', 'Indigenous African Music', 'Jazz Studies',
            'Music History', 'Performance Practical',
            'Sight-Reading', 'Western Art Music',
        ],
        'Visual Arts': [
            'Art History — 20th Century Movements',
            'Art History — South African Art', 'Conceptual Art',
            'Critical Analysis & Visual Culture',
            'Drawing & Painting', 'Mixed Media',
            'New Media — Digital & Photography', 'Practical Project',
            'Printmaking', 'Sculpture & 3D Work',
        ],
        'Religion Studies': [
            'Common & Distinctive Features of Religions',
            'Comparative Study of Religions',
            'Internal Differences within Religions',
            'Normative Sources', 'Religion & Science',
            'Religion & Society', 'Religion in South Africa',
            'Religious Freedom & Human Rights', 'Sacred Texts',
        ],
    }

    # Merge curated CAPS topics into the per-subject map (so empty banks
    # still expose the official topic list per subject).
    for subj_name, ts in caps_topics_by_subject.items():
        topics_by_subject.setdefault(subj_name, set()).update(ts)
    topics_by_subject = {k: sorted(v) for k, v in topics_by_subject.items()}

    # Master topic list (for "All subjects") = union of every topic + DB topics.
    topics = sorted({t for ts in topics_by_subject.values() for t in ts}
                    | {i.topic for i in all_items if i.topic})

    # Subjects: union of subjects present in the bank with the curated CAPS list.
    # Expand legacy abbreviations (CAT, IT) to their full CAPS subject names.
    _bank_abbr_to_full = {'CAT': 'Computer Applications Technology', 'IT': 'Information Technology'}
    db_subjects = {_bank_abbr_to_full.get(i.subject, i.subject) for i in all_items if i.subject}
    caps_subjects = {
        'Accounting', 'Afrikaans FAL', 'Afrikaans Home Language',
        'Agricultural Sciences', 'Business Studies',
        'Computer Applications Technology', 'Consumer Studies',
        'Dramatic Arts', 'Economics', 'Engineering Graphics & Design',
        'English FAL', 'English Home Language', 'Geography', 'History',
        'Hospitality Studies', 'Information Technology', 'Life Orientation',
        'Life Sciences', 'Mathematical Literacy', 'Mathematics',
        'Music', 'Physical Sciences', 'Religion Studies',
        'Tourism', 'Visual Arts',
    }
    subjects = sorted(db_subjects | caps_subjects)

    # Paper labels are stored as tags like "CAT P2 May/June 2025" or "CAT P2 Nov 2022".
    # The 2-5 letter prefix is the subject abbreviation. Map it back to the full
    # subject name so we can show only the relevant papers for the picked subject.
    paper_re = re.compile(r"^([A-Z]{2,5})\s+P\d+\s+(May/June|Nov|November|March|Sept|September|Feb|February)\s+\d{4}$")
    # Subject abbreviation conventions used across DBE archives.
    _abbr_to_subject = {
        'CAT': 'Computer Applications Technology',
        'IT':  'Information Technology',
        'MATH': 'Mathematics',
        'MATHS': 'Mathematics',
        'MLIT': 'Mathematical Literacy',
        'ML':   'Mathematical Literacy',
        'ACCN': 'Accounting',
        'ACC':  'Accounting',
        'BSTD': 'Business Studies',
        'BUS':  'Business Studies',
        'ECON': 'Economics',
        'ECO':  'Economics',
        'PHSC': 'Physical Sciences',
        'PHYS': 'Physical Sciences',
        'LFSC': 'Life Sciences',
        'LIFE': 'Life Sciences',
        'GEOG': 'Geography',
        'GEO':  'Geography',
        'HIST': 'History',
        'ENGHL': 'English Home Language',
        'ENGFAL': 'English FAL',
        'ENG':  'English Home Language',
        'AFRHL': 'Afrikaans Home Language',
        'AFRFAL': 'Afrikaans FAL',
        'AFR':  'Afrikaans Home Language',
        'LO':   'Life Orientation',
        'TOUR': 'Tourism',
        'CONS': 'Consumer Studies',
        'HOSP': 'Hospitality Studies',
        'AGRI': 'Agricultural Sciences',
        'EGD':  'Engineering Graphics & Design',
        'DRAM': 'Dramatic Arts',
        'MUS':  'Music',
        'VART': 'Visual Arts',
        'RELG': 'Religion Studies',
        'RELS': 'Religion Studies',
    }
    paper_set = set()
    papers_by_subject = {}
    for i in all_items:
        if not i.tags:
            continue
        # Use the item's own subject as the primary mapping; fall back to the
        # tag-prefix abbreviation if the item has no subject set.
        item_subject_full = _bank_abbr_to_full.get(i.subject, i.subject) if i.subject else None
        for tag in (t.strip() for t in i.tags.split(',')):
            m = paper_re.match(tag)
            if not m:
                continue
            paper_set.add(tag)
            subj_full = item_subject_full or _abbr_to_subject.get(m.group(1))
            if subj_full:
                papers_by_subject.setdefault(subj_full, set()).add(tag)
    papers_by_subject = {k: sorted(v) for k, v in papers_by_subject.items()}

    # Seed every subject with the standard DBE NSC paper set so the
    # Question paper dropdown always has options to pick from, even before
    # any questions tagged with that paper exist in the bank.
    _subject_to_abbr = {
        'Computer Applications Technology': 'CAT',
        'Information Technology': 'IT',
        'Mathematics': 'MATH', 'Mathematical Literacy': 'MLIT',
        'Accounting': 'ACCN', 'Business Studies': 'BSTD', 'Economics': 'ECON',
        'Physical Sciences': 'PHSC', 'Life Sciences': 'LFSC',
        'Geography': 'GEOG', 'History': 'HIST',
        'English Home Language': 'ENGHL', 'English FAL': 'ENGFAL',
        'Afrikaans Home Language': 'AFRHL', 'Afrikaans FAL': 'AFRFAL',
        'Life Orientation': 'LO', 'Tourism': 'TOUR',
        'Consumer Studies': 'CONS', 'Hospitality Studies': 'HOSP',
        'Agricultural Sciences': 'AGRI',
        'Engineering Graphics & Design': 'EGD',
        'Dramatic Arts': 'DRAM', 'Music': 'MUS', 'Visual Arts': 'VART',
        'Religion Studies': 'RELG',
    }
    # Number of papers per subject (NSC structure)
    _subject_paper_counts = {
        'Computer Applications Technology': 2, 'Information Technology': 2,
        'Mathematics': 2, 'Mathematical Literacy': 2,
        'Accounting': 1, 'Business Studies': 1, 'Economics': 2,
        'Physical Sciences': 2, 'Life Sciences': 2,
        'Geography': 2, 'History': 2,
        'English Home Language': 3, 'English FAL': 3,
        'Afrikaans Home Language': 3, 'Afrikaans FAL': 3,
        'Life Orientation': 1, 'Tourism': 1,
        'Consumer Studies': 1, 'Hospitality Studies': 1,
        'Agricultural Sciences': 2,
        'Engineering Graphics & Design': 2,
        'Dramatic Arts': 1, 'Music': 2, 'Visual Arts': 1,
        'Religion Studies': 2,
    }
    _seed_years = [2025, 2024, 2023, 2022, 2021]
    _seed_sittings = ['May/June', 'Nov']
    for subj_name, abbr in _subject_to_abbr.items():
        n_papers = _subject_paper_counts.get(subj_name, 2)
        bucket = papers_by_subject.setdefault(subj_name, set()) if not isinstance(
            papers_by_subject.get(subj_name), list) else set(papers_by_subject[subj_name])
        if isinstance(papers_by_subject.get(subj_name), list):
            bucket = set(papers_by_subject[subj_name])
        for yr in _seed_years:
            for sitting in _seed_sittings:
                for pn in range(1, n_papers + 1):
                    label = f"{abbr} P{pn} {sitting} {yr}"
                    paper_set.add(label)
                    bucket.add(label)
        papers_by_subject[subj_name] = sorted(bucket)

    def _paper_sort_key(label):
        # Sort newest first: extract year then season weight
        m = re.search(r"(\d{4})$", label)
        year = int(m.group(1)) if m else 0
        season = 1 if 'Nov' in label else 0  # Nov after May/June within same year
        return (-year, -season, label)
    papers = sorted(paper_set, key=_paper_sort_key)

    return render_template('teacher/bank.html', items=items, topics=topics,
                           papers=papers, grade=grade,
                           subjects=subjects, subject=subject,
                           topics_by_subject=topics_by_subject,
                           papers_by_subject=papers_by_subject,
                           selected_topics=topic_list, diff=diff, paper=paper,
                           owner_scope=owner_scope)


@app.route('/teacher/bank/new', methods=['GET', 'POST'])
@app.route('/teacher/bank/<item_id>/edit', methods=['GET', 'POST'])
@teacher_required
def teacher_bank_edit(item_id=None):
    item = QuestionBankItem.query.get_or_404(item_id) if item_id else None
    subject_choices = _generator_subject_choices()
    selected_subject = _canonical_subject(
        item.subject if item else request.values.get('subject'))
    if item and selected_subject and selected_subject not in subject_choices:
        subject_choices = sorted(
            set(subject_choices) | {selected_subject}, key=str.lower)
    if selected_subject not in subject_choices:
        selected_subject = (
            'Computer Applications Technology'
            if 'Computer Applications Technology' in subject_choices
            else (subject_choices[0] if subject_choices else
                  'Computer Applications Technology')
        )
    # ---- Moderator fork mode -------------------------------------------
    # When a moderator (HOD reviewing someone else's paper) clicks "edit"
    # on a question that belongs to the paper owner, we don't allow them
    # to mutate the original bank item — instead we fork: create a
    # private copy owned by the moderator and swap the question_id in the
    # paper's sections JSON. The owner's bank item is never touched.
    _mod_fork_paper = None
    if (item is not None
            and current_user.is_authenticated
            and item.owner_id != current_user.id
            and (request.values.get('mod') == '1')
            and request.values.get('paper_id')):
        _mod_fork_paper = GeneratedPaper.query.get(request.values.get('paper_id'))
        if not _mod_fork_paper or not _can_moderate(_mod_fork_paper):
            _mod_fork_paper = None
    # Enforce visibility: a teacher can only open another user's item if it is
    # public, or school-shared by a colleague at the same school. Owners and
    # admins always pass.
    if item and item.owner_id != current_user.id and not current_user.is_admin and _mod_fork_paper is None:
        scope = (item.share_scope or '').lower()
        allowed = (scope == 'public')
        if not allowed and scope == 'school':
            owner = User.query.get(item.owner_id)
            mine = (current_user.school_name or '').strip().lower()
            theirs = (owner.school_name or '').strip().lower() if owner else ''
            allowed = bool(mine and theirs and mine == theirs)
        # Subject scope (teachers/moderators: own subjects; HOD: own + team's).
        if allowed:
            subj_set = _visible_subject_set()
            if subj_set is not None and (item.subject or '') not in subj_set:
                allowed = False
        if not allowed:
            abort(404)
    read_only = bool(item
                     and item.owner_id != current_user.id
                     and not current_user.is_admin
                     and _mod_fork_paper is None)
    if read_only and request.method == 'POST':
        abort(403)
    if request.method == 'POST':
        # Moderator fork: clone the original into a new private item owned
        # by the moderator, then apply edits to the clone. Swap the
        # paper's question_id reference and leave the owner's bank
        # item untouched.
        if _mod_fork_paper is not None and item is not None and item.owner_id != current_user.id:
            original_qid = item.id
            fork = QuestionBankItem(
                owner_id=current_user.id,
                grade=item.grade, subject=item.subject, topic=item.topic,
                subtopic=item.subtopic, difficulty=item.difficulty,
                question_type=item.question_type,
                question_text=item.question_text, answer_text=item.answer_text,
                marks=item.marks, tags=item.tags, image_path=item.image_path,
                share_scope='private', is_shared=False,
            )
            db.session.add(fork)
            db.session.flush()  # assign id
            # Swap reference inside paper.sections JSON.
            try:
                _secs = json.loads(_mod_fork_paper.sections or '[]')
                if isinstance(_secs, list):
                    for _sec in _secs:
                        if not isinstance(_sec, dict):
                            continue
                        _qids = _sec.get('question_ids') or []
                        for _i, _q in enumerate(_qids):
                            if _q == original_qid:
                                _qids[_i] = fork.id
                        _sec['question_ids'] = _qids
                    _mod_fork_paper.sections = json.dumps(_secs)
            except Exception:
                pass
            # Switch the in-memory item to the fork so the rest of this
            # POST handler writes the form values onto the fork.
            item = fork
        if not item:
            item = QuestionBankItem(owner_id=current_user.id)
            db.session.add(item)
        requested_subject = _canonical_subject(
            request.form.get('subject', selected_subject))
        if not current_user.is_admin and requested_subject not in subject_choices:
            abort(400, description='Select one of your registered subjects.')
        item.subject = requested_subject
        item.grade = request.form.get('grade', type=int) or 12
        item.topic = request.form.get('topic', '').strip()
        item.subtopic = request.form.get('subtopic', '').strip()
        item.difficulty = request.form.get('difficulty', 'medium')
        item.question_type = request.form.get('question_type', 'short_answer')
        item.question_text = request.form.get('question_text', '').strip()
        # Normalize Wingdings PUA tick chars (\uF0FC / \uF0FB) and U+2714 to U+2713
        # so they render as a real check mark in any font (no missing-glyph boxes).
        _ans_raw = request.form.get('answer_text', '').strip()
        item.answer_text = (_ans_raw
                            .replace('\uf0fc', '\u2713')
                            .replace('\uf0fb', '\u2713')
                            .replace('\u2714', '\u2713'))
        # Allow 0 marks for scenario stems (intro text with no marks badge).
        marks_raw = request.form.get('marks', '').strip()
        try:
            item.marks = max(0, int(marks_raw)) if marks_raw != '' else 1
        except (TypeError, ValueError):
            item.marks = 1
        item.tags = request.form.get('tags', '').strip()
        # Visibility scope: private | school | public.
        scope = (request.form.get('share_scope') or 'private').strip().lower()
        if scope not in ('private', 'school', 'public'):
            scope = 'private'
        item.share_scope = scope
        # Keep legacy is_shared in sync (True only when public) so old code paths
        # that still check it continue to behave correctly.
        item.is_shared = (scope == 'public')
        # Optional figure / diagram for the question
        if request.form.get('image_clear') == '1':
            item.image_path = ''
        img = request.files.get('image')
        if img and img.filename:
            rel, _ = _save_upload(img, 'questions', TEACHER_LOGO_EXTS)
            if rel:
                item.image_path = rel
        if not item.question_text:
            flash('Question text is required.', 'danger')
        else:
            db.session.commit()
            flash('Question saved.', 'success')
            nxt = request.form.get('next') or request.args.get('next') or ''
            # Only allow same-origin relative redirects.
            if nxt and nxt.startswith('/') and not nxt.startswith('//'):
                return redirect(nxt)
            return redirect(url_for('teacher_bank'))
    # Build the tag suggestion list: distinct tags from questions the
    # current user can already see, sorted alphabetically.
    tag_q = db.session.query(QuestionBankItem.tags)
    if not current_user.is_admin:
        tag_q = tag_q.filter(_bank_visible_filter())
    tag_q = tag_q.filter(QuestionBankItem.subject.in_(
        _expand_subject_aliases([selected_subject])))
    tag_rows = tag_q.all()
    seen = set()
    existing_tags = []
    for (raw,) in tag_rows:
        if not raw:
            continue
        for t in str(raw).split(','):
            t = t.strip()
            if t and t.lower() not in seen:
                seen.add(t.lower())
                existing_tags.append(t)
    existing_tags.sort(key=lambda s: s.lower())
    return render_template('teacher/bank_edit.html', item=item,
                           read_only=read_only, existing_tags=existing_tags,
                           subject_choices=subject_choices,
                           selected_subject=selected_subject)


@app.route('/teacher/bank/<item_id>/inline_save', methods=['POST'])
@teacher_required
def teacher_bank_inline_save(item_id):
    """JSON endpoint used by the paper editor to save a question's full
    body (question_text / answer_text / marks / question_type) inline,
    without leaving the editor. Mirrors the moderator-fork semantics of
    `teacher_bank_edit`: when a moderator edits another teacher's question
    in the context of a paper they're moderating, we clone the bank item
    into a private copy owned by the moderator and swap the question_id
    inside that paper's `sections` JSON, leaving the original untouched.
    Returns JSON: {ok, id, forked, marks, question_text, answer_text,
                   question_type, text}.
    """
    item = QuestionBankItem.query.get_or_404(item_id)
    payload = request.get_json(silent=True) or {}
    paper_id = (payload.get('paper_id') or '').strip()
    is_mod_ctx = bool(payload.get('mod')) and bool(paper_id)
    mod_paper = None
    forked = False
    if (item.owner_id != current_user.id and is_mod_ctx):
        mod_paper = GeneratedPaper.query.get(paper_id)
        if not mod_paper or not _can_moderate(mod_paper):
            mod_paper = None
    if (item.owner_id != current_user.id
            and not current_user.is_admin
            and mod_paper is None):
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    # Moderator fork: clone into private item then redirect edits to it.
    if mod_paper is not None and item.owner_id != current_user.id:
        original_qid = item.id
        fork = QuestionBankItem(
            owner_id=current_user.id,
            grade=item.grade, subject=item.subject, topic=item.topic,
            subtopic=item.subtopic, difficulty=item.difficulty,
            question_type=item.question_type,
            question_text=item.question_text, answer_text=item.answer_text,
            marks=item.marks, tags=item.tags, image_path=item.image_path,
            share_scope='private', is_shared=False,
        )
        db.session.add(fork); db.session.flush()
        try:
            _secs = json.loads(mod_paper.sections or '[]')
            if isinstance(_secs, list):
                for _sec in _secs:
                    if not isinstance(_sec, dict):
                        continue
                    _qids = _sec.get('question_ids') or []
                    for _i, _q in enumerate(_qids):
                        if _q == original_qid:
                            _qids[_i] = fork.id
                    _sec['question_ids'] = _qids
                mod_paper.sections = json.dumps(_secs)
        except Exception:
            pass
        item = fork
        forked = True
    prev_qt = item.question_text or ''
    prev_ans = item.answer_text or ''
    prev_marks = int(item.marks or 0)
    prev_type = item.question_type or ''
    changed_any = False
    qt_raw = payload.get('question_text', None)
    preserve_ws = bool(payload.get('raw_pdf'))
    if qt_raw is not None:
        qt = str(qt_raw)
        if not qt.strip():
            return jsonify({'ok': False, 'error': 'Question text is required.'}), 400
        _next_qt = qt if preserve_ws else qt.strip()
        if _next_qt != prev_qt:
            item.question_text = _next_qt
            changed_any = True
    if 'answer_text' in payload:
        _ans = str(payload.get('answer_text') or '').strip()
        _next_ans = (_ans
                     .replace('\uf0fc', '\u2713')
                     .replace('\uf0fb', '\u2713')
                     .replace('\u2714', '\u2713'))
        if _next_ans != prev_ans:
            item.answer_text = _next_ans
            changed_any = True
    if 'marks' in payload:
        try:
            _next_marks = max(0, int(payload.get('marks') or 0))
            if _next_marks != prev_marks:
                item.marks = _next_marks
                changed_any = True
        except (TypeError, ValueError):
            pass
    if 'question_type' in payload:
        qty = str(payload.get('question_type') or '').strip()
        if qty and qty != prev_type:
            item.question_type = qty
            changed_any = True
    if changed_any and paper_id:
        hist_paper = GeneratedPaper.query.get(paper_id)
        if hist_paper and (current_user.is_admin or hist_paper.owner_id == current_user.id
                           or _can_moderate(hist_paper)):
            _push_edit_history(hist_paper, {
                't': 'qtxt',
                'qid': item.id,
                'qt': prev_qt,
                'ans': prev_ans,
                'm': prev_marks,
                'ty': prev_type,
            }, coalesce_on='qid')
    db.session.commit()
    # Short summary text matching the bankMap.text format.
    import re as _re
    _txt = _re.sub(r'(?i)^\s*Match the following description with the correct term from the list:\s*',
                   '', item.question_text or '')
    if len(_txt) > 80:
        _txt = _txt[:77] + '...'
    return jsonify({
        'ok': True,
        'id': item.id,
        'forked': forked,
        'marks': item.marks or 0,
        'question_text': item.question_text or '',
        'answer_text': item.answer_text or '',
        'question_type': item.question_type or '',
        'text': _txt,
    })


@app.route('/teacher/bank/<item_id>/delete', methods=['POST'])
@teacher_required
def teacher_bank_delete(item_id):
    item = QuestionBankItem.query.get_or_404(item_id)
    if item.owner_id != current_user.id and not current_user.is_admin:
        abort(403)
    db.session.delete(item); db.session.commit()
    flash('Question deleted.', 'info')
    return redirect(url_for('teacher_bank'))


@app.route('/teacher/bank/delete-mine', methods=['POST'])
@teacher_required
def teacher_bank_delete_mine():
    """Delete all questions owned by the current user.

    Default/seeded questions (owned by other users, e.g. imported sample
    papers or public shared questions) are left untouched.
    """
    own_items = QuestionBankItem.query.filter_by(owner_id=current_user.id).all()
    n = len(own_items)
    for it in own_items:
        db.session.delete(it)
    db.session.commit()
    if n:
        flash(f'Deleted {n} of your questions. Default and shared questions were kept.', 'info')
    else:
        flash('You have no personal questions to delete.', 'info')
    return redirect(url_for('teacher_bank'))


# ---------- Paper generator ---------------------------------------------
def _paper_visible_filter():
    """SQLAlchemy filter expression that scopes GeneratedPaper rows to what
    the current user is allowed to see in the generator list:
      - own papers
      - public papers (share_scope='public')
      - school papers (share_scope='school') from teachers at the same school
      - papers assigned to the current user as moderator (HOD review queue)
    Admins bypass this filter (caller checks current_user.is_admin).
    """
    own = GeneratedPaper.owner_id == current_user.id
    public = GeneratedPaper.share_scope == 'public'
    assigned = GeneratedPaper.moderator_id == current_user.id
    school = (current_user.school_name or '').strip()
    if school:
        school_owner_ids = (db.session.query(User.id)
                            .filter(db.func.lower(User.school_name) == school.lower())
                            .subquery())
        school_share = db.and_(
            GeneratedPaper.share_scope == 'school',
            GeneratedPaper.owner_id.in_(db.session.query(school_owner_ids.c.id))
        )
        base = db.or_(own, public, school_share, assigned)
    else:
        base = db.or_(own, public, assigned)
    subj_set = _visible_subject_set()
    if subj_set is None:
        return base
    if not subj_set:
        return own
    return db.and_(base, GeneratedPaper.subject.in_(subj_set))


def _can_view_paper(paper):
    """True if current_user is allowed to view (preview/memo/read-only) the paper."""
    if not current_user.is_authenticated:
        return False
    if current_user.is_admin:
        return True
    if paper.owner_id == current_user.id:
        return True
    # Subject scope: non-owners must have the paper's subject in their visible set.
    subj_set = _visible_subject_set()
    if subj_set is not None and (paper.subject or '') not in subj_set:
        return False
    if _can_moderate(paper):
        return True
    scope = (paper.share_scope or 'private').lower()
    if scope == 'public':
        return True
    if scope == 'school':
        my_school = (current_user.school_name or '').strip().lower()
        owner = User.query.get(paper.owner_id)
        if owner and (owner.school_name or '').strip().lower() == my_school and my_school:
            return True
    return False


_PDF_PNO_CACHE = {}


def _pdf_header_pno(abs_path):
    """Return '1'/'2' — the paper number stamped in a DBE PDF's running
    header ("Computer Applications Technology/P1"), or None if unknown.
    Cached by (path, mtime) so repeated list renders stay fast."""
    try:
        _mt = os.path.getmtime(abs_path)
    except OSError:
        return None
    _key = (abs_path, _mt)
    if _key in _PDF_PNO_CACHE:
        return _PDF_PNO_CACHE[_key]
    _pno = None
    try:
        import fitz
        with fitz.open(abs_path) as _d:
            _txt = _d[0].get_text() or ''
            if len(_txt.strip()) < 40 and _d.page_count > 1:
                _txt += _d[1].get_text() or ''
        _m = re.search(r'Technology\s*/?\s*P\s*([12])', _txt, re.I)
        if _m:
            _pno = _m.group(1)
    except Exception:
        _pno = None
    _PDF_PNO_CACHE[_key] = _pno
    return _pno


def _find_paper_source_pdfs(paper):
    """Best-effort lookup of the original DBE question paper + memo PDFs
    that a generated paper was built from.

    The originals live in `static/uploads/` with filenames such as
    "Computer Applications Technology P2 May-June 2024 Eng.pdf" (paper)
    and "... MG Eng.pdf" (memo). We map a GeneratedPaper.title like
    "CAT P2 Nov 2021" or "CAT P2 May-June 2024" to that filename.
    Returns {'paper_url': str|None, 'memo_url': str|None, 'paper_name': str|None, 'memo_name': str|None}.
    """
    try:
        import re as _re, glob as _glob
        title = (paper.title or '').strip()
        # Pull P1/P2 and the session token (e.g. "Nov 2021", "May-June 2024")
        m = _re.search(r'\bP\s*([12])\b', title, _re.IGNORECASE)
        paper_no = m.group(1) if m else None
        ms = _re.search(r'((?:May[-\s]?June|Nov(?:ember)?|June)\s*\d{4})', title, _re.IGNORECASE)
        session_tok = ms.group(1) if ms else None
        if not (paper_no and session_tok):
            return None
        # Normalise "May June" -> "May-June", "November" -> "Nov"
        session_tok = _re.sub(r'\s+', ' ', session_tok)
        session_tok = session_tok.replace('May June', 'May-June')
        session_tok = _re.sub(r'November', 'Nov', session_tok, flags=_re.IGNORECASE)
        year = session_tok.split()[-1]
        month_part = ' '.join(session_tok.split()[:-1])
        uploads_dir = os.path.join(app.static_folder, 'uploads')

        # Subject guard: source filenames start with the full subject name
        # (e.g. "Business Studies P1 ..." / "Computer Application(s)
        # Technology P2 ..."), so only match files for THIS paper's subject
        # to keep subjects isolated.
        _subj = _canonical_subject(getattr(paper, 'subject', '') or '')
        _subj_prefixes = {
            'Computer Applications Technology': (
                'computer application technology', 'computer applications technology'),
            'Business Studies': ('business studies',),
        }.get(_subj)

        def _scan(memo: bool):
            mg_marker = ' MG ' if memo else ' '
            try:
                names = os.listdir(uploads_dir)
            except OSError:
                return None
            wanted_p = f'P{paper_no}'
            best = None
            for n in names:
                if not n.lower().endswith('.pdf'):
                    continue
                if _subj_prefixes and not n.lower().startswith(_subj_prefixes):
                    continue
                if wanted_p not in n:
                    continue
                if year not in n:
                    continue
                if month_part and month_part.lower() not in n.lower():
                    continue
                has_mg = ' MG ' in n
                if memo and not has_mg:
                    continue
                if (not memo) and has_mg:
                    continue
                # Prefer shortest (avoid "(1)" duplicates)
                if best is None or len(n) < len(best):
                    best = n
            return best

        paper_name = _scan(False)
        memo_name = _scan(True)

        # Guard against MISLABELLED source files (e.g. a file named
        # "…P2 … MG…" that actually contains the P1 marking guideline). Only
        # link a source PDF when its own content confirms the paper number,
        # so we never open the wrong paper under the right name.
        def _content_ok(name):
            if not name:
                return False
            _pno = _pdf_header_pno(os.path.join(uploads_dir, name))
            return _pno is None or _pno == paper_no

        if not _content_ok(paper_name):
            paper_name = None
        if not _content_ok(memo_name):
            memo_name = None

        out = {'paper_name': paper_name, 'memo_name': memo_name,
               'paper_url': None, 'memo_url': None}
        if paper_name:
            out['paper_url'] = url_for('static', filename=f'uploads/{paper_name}')
        if memo_name:
            out['memo_url'] = url_for('static', filename=f'uploads/{memo_name}')
        return out
    except Exception:
        return None


@app.route('/teacher/generator')
@teacher_required
def teacher_papers_generated():
    owner_scope = (request.args.get('owner') or 'all').strip().lower()
    if owner_scope not in ('all', 'mine'):
        owner_scope = 'all'
    subject_choices = _generator_subject_choices()
    selected_subject = _canonical_subject(request.args.get('subject'))
    if selected_subject not in subject_choices:
        selected_subject = (
            'Computer Applications Technology'
            if 'Computer Applications Technology' in subject_choices
            else (subject_choices[0] if subject_choices else '')
        )
    if current_user.is_admin:
        q = GeneratedPaper.query
    else:
        q = GeneratedPaper.query.filter(_paper_visible_filter())
    if selected_subject:
        q = q.filter(GeneratedPaper.subject.in_(
            _expand_subject_aliases([selected_subject])))
    if owner_scope == 'mine':
        # "My papers only" = papers this user actually created, excluding the
        # seeded/imported library (past) papers (which are also owned by the
        # importing user but should not count as the user's own work).
        q = q.filter(GeneratedPaper.owner_id == current_user.id,
                     db.or_(GeneratedPaper.is_library.is_(False),
                            GeneratedPaper.is_library.is_(None)))
    papers = q.order_by(GeneratedPaper.exam_date.desc().nullslast(),
                        GeneratedPaper.created_at.desc()).all()
    # Generate window only: show just the recent DBE library templates
    # (2023–2025); older seeded past papers (e.g. 2021/2022) are hidden HERE
    # (they still appear in the Question Bank and Past Papers pages). Papers
    # the user actually created are always kept, regardless of year.
    _ALLOWED_TEMPLATE_YEARS = {2023, 2024, 2025}

    def _tmpl_year_ok(_p):
        if not getattr(_p, 'is_library', False):
            return True
        _y = _p.exam_date.year if getattr(_p, 'exam_date', None) else None
        if _y is None:
            _m = re.search(r'(20\d{2})', _p.title or '')
            _y = int(_m.group(1)) if _m else None
        return _y in _ALLOWED_TEMPLATE_YEARS

    papers = [p for p in papers if _tmpl_year_ok(p)]
    # Spotlight the paper this user most recently opened/edited so the
    # quick "Memo / Paper" preview links are one click away at the top of
    # the listing.
    _last_id = session.get('last_edited_paper_id')
    last_edited = None
    if _last_id:
        last_edited = next((p for p in papers if p.id == _last_id), None)
    # Always surface the "Last edited" card whenever the user has any
    # papers, so clicking a paper row always has a card to populate (and
    # the Paper / Memo / Original buttons are always present). Fall back to
    # the most-recent paper when nothing has been opened this session yet.
    if last_edited is None and papers:
        last_edited = papers[0]
    last_edited_sources = _find_paper_source_pdfs(last_edited) if last_edited else None
    # Pre-compute card-friendly metadata + source PDF links for every
    # listed paper so the client can swap the "Last edited" card to the
    # row the user just clicked without a round-trip.
    papers_card_data = {}
    for _pp in papers:
        try:
            _src = _find_paper_source_pdfs(_pp) or {}
        except Exception:
            _src = {}
        papers_card_data[_pp.id] = {
            'id': _pp.id,
            'title': (_pp.title or '').replace('Nov ', 'November '),
            'date': _pp.exam_date.strftime('%d %b %Y') if _pp.exam_date else '',
            'grade': _pp.grade,
            'total_marks': _pp.total_marks,
            'preview_url': url_for('teacher_paper_preview', paper_id=_pp.id),
            'memo_url': url_for('teacher_paper_memo', paper_id=_pp.id),
            'word_url': url_for('teacher_paper_download_docx', paper_id=_pp.id),
            'word_memo_url': url_for('teacher_paper_download_memo_docx', paper_id=_pp.id),
            'paper_url': _src.get('paper_url'),
            'paper_name': _src.get('paper_name'),
            'orig_memo_url': _src.get('memo_url'),
            'memo_name': _src.get('memo_name'),
        }
    return render_template('teacher/generator_list.html',
                           papers=papers, owner_scope=owner_scope,
                           subject_choices=subject_choices,
                           selected_subject=selected_subject,
                           last_edited=last_edited,
                           last_edited_sources=last_edited_sources,
                           papers_card_data=papers_card_data)


@app.route('/teacher/generator/new', methods=['GET', 'POST'])
@app.route('/teacher/generator/<paper_id>/edit', methods=['GET', 'POST'])
@teacher_required
def teacher_paper_edit(paper_id=None):
    # For a brand-new paper on GET, create a blank record immediately so the
    # split-screen editor (which requires a paper_id for the preview pane) is
    # always shown in full. Keep rendering in the same request to avoid an
    # extra browser hop before the editor opens.
    if request.method == 'GET' and paper_id is None:
        subject_choices = _generator_subject_choices()
        requested_subject = _canonical_subject(request.args.get('subject'))
        if requested_subject not in subject_choices:
            requested_subject = (
                'Computer Applications Technology'
                if 'Computer Applications Technology' in subject_choices
                else (subject_choices[0] if subject_choices else
                      'Computer Applications Technology')
            )
        # Resume-aware "new paper": if the teacher already has an unfinished
        # draft (empty title and no questions added yet) lying around,
        # re-open that one instead of stacking up another empty row. This
        # means the user can navigate away mid-creation, click "New paper"
        # again later, and land back in the same draft they started.
        reuse = None
        try:
            candidates = (GeneratedPaper.query
                          .filter_by(owner_id=current_user.id)
                          .filter((GeneratedPaper.moderation_status == None)
                                  | (GeneratedPaper.moderation_status.in_(['draft', ''])))
                          .order_by(GeneratedPaper.created_at.desc())
                          .limit(8).all())
            for _p in candidates:
                _title = (_p.title or '').strip()
                try:
                    _secs = json.loads(_p.sections or '[]')
                except Exception:
                    _secs = []
                _has_qs = any((isinstance(s, dict) and s.get('question_ids'))
                              for s in (_secs or []))
                if (not _title and not _has_qs
                        and _canonical_subject(_p.subject) == requested_subject):
                    reuse = _p
                    break
        except Exception:
            reuse = None
        if reuse is not None:
            return redirect(url_for('teacher_paper_edit', paper_id=reuse.id))
        paper = GeneratedPaper(
            owner_id=current_user.id,
            title='',
            subject=requested_subject,
            grade=12,
            duration_minutes=180,
            total_marks=150,
            sections='[]',
        )
        db.session.add(paper)
        db.session.commit()
        paper_id = paper.id

    paper = GeneratedPaper.query.get_or_404(paper_id) if paper_id else None
    # The assigned moderator (and admins editing someone else's paper)
    # may edit a paper they don't own. Their edits get tagged so they
    # render in green in the preview/print.
    _is_mod_edit = bool(paper
                        and paper.owner_id != current_user.id
                        and _can_moderate(paper))
    # Backfill the "Original" snapshot the first time a moderator opens a
    # paper that was flagged before the three-version workflow shipped.
    # Once a snapshot exists we never overwrite it here.
    if (_is_mod_edit and request.method == 'GET'
            and (paper.moderation_status or '') in ('flagged', 'rejected', 'signed_off')):
        _need_commit = False
        if not (paper.sections_original or '').strip():
            paper.sections_original = _strip_mod_tags(paper.sections or '[]')
            _need_commit = True
        if not (paper.header_original or '').strip():
            paper.header_original = json.dumps(_paper_header_snapshot(paper))
            _need_commit = True
        if _need_commit:
            db.session.commit()
    # Owner lock: while a paper is in moderation (flagged) or has been
    # signed off by the moderator, the owner cannot edit it. They must
    # either wait for the moderator or "Accept" the moderator's changes.
    # Admins always retain edit access.
    if (paper and not current_user.is_admin and not _is_mod_edit
            and paper.owner_id == current_user.id
            and (paper.moderation_status or '') in ('flagged', 'signed_off')):
        if request.method == 'POST':
            abort(403)
        flash('This paper is locked while moderation is in progress. '
              'Review the moderator\u2019s version and accept the changes to continue editing.',
              'info')
        if paper.moderation_status == 'signed_off':
            return redirect(url_for('teacher_paper_preview', paper_id=paper.id, version='moderated'))
        return redirect(url_for('teacher_papers_generated'))
    # Non-owners (teachers/HODs that aren't admin and aren't the assigned
    # moderator) get a read-only view of the paper preview rather than an
    # edit form, instead of a 403.
    if (paper and request.method == 'GET'
            and paper.owner_id != current_user.id
            and not current_user.is_admin
            and not _is_mod_edit):
        if not _can_view_paper(paper):
            abort(404)
        return redirect(url_for('teacher_paper_preview', paper_id=paper.id))
    if (paper and paper.owner_id != current_user.id
            and not current_user.is_admin
            and not _is_mod_edit):
        abort(403)

    if request.method == 'POST':
        if not paper:
            paper = GeneratedPaper(owner_id=current_user.id)
            db.session.add(paper)
        # If a moderator is editing a paper that has no original snapshot
        # yet (e.g. flagged before this code shipped, or signed-off without
        # any changes captured), snapshot the CURRENT pre-edit state now —
        # before we overwrite the row with form data — so the diff has a
        # baseline to compare against on this and every later save.
        if _is_mod_edit:
            if not (paper.sections_original or '').strip():
                paper.sections_original = _strip_mod_tags(paper.sections or '[]')
            if not (paper.header_original or '').strip():
                paper.header_original = json.dumps(_paper_header_snapshot(paper))
        logo_upload_error = None
        paper.title = request.form.get('title', 'Examination Paper').strip()
        paper.school_name = request.form.get('school_name', '').strip()
        requested_subject = _canonical_subject(request.form.get(
            'subject', paper.subject or 'Computer Applications Technology'))
        subject_choices = _generator_subject_choices()
        if not current_user.is_admin and requested_subject not in subject_choices:
            abort(400, description='Select one of your registered subjects.')
        paper.subject = requested_subject
        paper.grade = request.form.get('grade', type=int) or 12
        date_str = request.form.get('exam_date', '').strip()
        paper.exam_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
        paper.duration_minutes = request.form.get('duration_minutes', type=int) or 180
        paper.total_marks = request.form.get('total_marks', type=int) or 150
        paper.examiner = request.form.get('examiner', '').strip()
        paper.moderator = request.form.get('moderator', '').strip()
        _new_instr = request.form.get('instructions', '').strip()
        # Stale-tab shield: older editor scripts auto-inject the CAT cover
        # instruction library ('[Auto] …') into any subject. For non-CAT
        # papers, ignore such payloads and keep the stored instructions.
        _subj_low = (paper.subject or '').lower()
        if (_new_instr.startswith('[Auto]')
                and 'computer applications' not in _subj_low
                and 'information technology' not in _subj_low):
            _new_instr = paper.instructions or ''
        paper.instructions = _new_instr
        # Cover / header / footer customisation
        paper.paper_number     = request.form.get('paper_number', '').strip()
        paper.cover_authority  = request.form.get('cover_authority', '').strip()
        paper.cover_subtitle   = request.form.get('cover_subtitle', '').strip()
        paper.header_left      = request.form.get('header_left', '').strip()
        paper.header_right     = request.form.get('header_right', '').strip()
        paper.sub_header       = request.form.get('sub_header', '').strip()
        paper.footer_left      = request.form.get('footer_left', 'Copyright reserved').strip()
        paper.footer_right     = request.form.get('footer_right', 'Please turn over').strip()
        paper.footer_center    = request.form.get('footer_center', '').strip()
        paper.memo_title       = request.form.get('memo_title', 'MARKING GUIDELINES').strip()
        paper.cover_extra_note = request.form.get('cover_extra_note', '').strip()
        # Visibility scope (private | school | public). Default to existing or 'private'.
        scope = (request.form.get('share_scope') or paper.share_scope or 'private').strip().lower()
        if scope not in ('private', 'school', 'public'):
            scope = 'private'
        paper.share_scope = scope
        # logo upload / clear
        if request.form.get('logo_clear') == '1':
            paper.logo_path = ''
        logo = request.files.get('logo')
        if logo and logo.filename:
            rel, _ = _save_upload(logo, 'logos', TEACHER_LOGO_EXTS)
            if rel:
                paper.logo_path = rel
            else:
                logo_upload_error = 'Unsupported logo format. Use PNG, JPG, JPEG, SVG, WEBP, JFIF, GIF, BMP, or AVIF.'
        # sections JSON
        try:
            new_sections_json = request.form.get('sections_json', '[]')
            _new_secs = json.loads(new_sections_json)  # validate
            # Preserve per-section custom fields that the editor form does
            # not round-trip (tf_examples, tf_no_mark, qmemo_notes, qimages,
            # qinstructions, qtitles, etc.). Without this every autosave
            # wipes hand-authored memo/preview customisations.
            try:
                _old_secs = json.loads(paper.sections or '[]')
            except Exception:
                _old_secs = []
            _preserve_keys = (
                'tf_examples', 'tf_no_mark', 'qmemo_notes', 'qimages',
                'qinstructions', 'qtitles', 'qoutros', 'subitems',
                'scenario', 'scenarios', 'qpost_texts',
                'forced_breaks', 'no_breaks',
                'marks', 'counted_marks', 'qmarks',
                'memo_intro', 'memo_breakdown', 'memo_front_pages',
            )
            for _i, _ns in enumerate(_new_secs or []):
                if not isinstance(_ns, dict):
                    continue
                if _i >= len(_old_secs) or not isinstance(_old_secs[_i], dict):
                    continue
                _os = _old_secs[_i]
                for _k in _preserve_keys:
                    if _k in _os and _k not in _ns:
                        _ns[_k] = _os[_k]
            # Guard: stale editor tabs auto-inject CAT-specific '[Auto] …'
            # section instructions (and per-question splits) into ANY paper.
            # For non-CAT subjects, strip that boilerplate and restore the
            # stored group layout so the paper's numbering can't drift.
            _subj_l = (paper.subject or '').lower()
            _is_cat_subj = ('computer applications' in _subj_l
                            or 'information technology' in _subj_l)
            # Stale-tab shield: editor pages older than generation 2 carry no
            # `editor_gen` field. Their JS auto-injects CAT Section-A splits
            # into any subject, so for non-CAT papers we keep the STORED
            # structure keys and only accept content-level changes.
            _editor_gen = (request.form.get('editor_gen') or '').strip()
            if not _is_cat_subj and _editor_gen != '2':
                for _i, _ns in enumerate(_new_secs or []):
                    if not isinstance(_ns, dict):
                        continue
                    _os = _old_secs[_i] if _i < len(_old_secs) and isinstance(_old_secs[_i], dict) else {}
                    for _k in ('splits', 'qtitles', 'qinstructions',
                               'qmemo_notes', 'subitems', 'instructions',
                               'question_ids', 'title'):
                        if _k in _os:
                            _ns[_k] = _os[_k]
            if not _is_cat_subj:
                _CAT_BLOCK_TITLES = {'MULTIPLE-CHOICE QUESTIONS',
                                     'MATCHING ITEMS', 'TRUE/FALSE ITEMS'}
                for _i, _ns in enumerate(_new_secs or []):
                    if not isinstance(_ns, dict):
                        continue
                    if (_ns.get('instructions') or '').startswith('[Auto]'):
                        _ns['instructions'] = ''
                    _qi = _ns.get('qinstructions')
                    _qt = _ns.get('qtitles')
                    _os = _old_secs[_i] if _i < len(_old_secs) and isinstance(_old_secs[_i], dict) else {}
                    _old_titles = {str(x or '').strip().upper()
                                   for x in (_os.get('qtitles') or [])}
                    _injected = (
                        (isinstance(_qi, list) and any(
                            str(x or '').startswith('[Auto]') for x in _qi))
                        or (isinstance(_qt, list) and any(
                            str(x or '').strip().upper() in _CAT_BLOCK_TITLES
                            and str(x or '').strip().upper() not in _old_titles
                            for x in _qt))
                    )
                    if _injected:
                        for _k in ('splits', 'qtitles', 'qinstructions',
                                   'qmemo_notes', 'subitems'):
                            if _k in _os:
                                _ns[_k] = _os[_k]
            new_sections_json = json.dumps(_new_secs, ensure_ascii=False)
            if _is_mod_edit:
                # Always diff against the pre-moderation original snapshot
                # so we can show the strikethrough-old + green-new pair
                # for every changed field, no matter how many times the
                # moderator saves.
                paper.sections = _tag_moderator_section_edits(
                    paper.sections_original, new_sections_json)
            else:
                paper.sections = new_sections_json
        except Exception:
            # NEVER wipe the paper on a malformed autosave payload — keep
            # the previously stored sections.
            app.logger.exception('sections_json parse failed; keeping stored sections')
        # Recompute top-level field overrides on every moderator save so
        # the duration / title / marks / etc. diff stays in sync.
        if _is_mod_edit:
            try:
                paper.moderator_overrides = json.dumps(_compute_paper_overrides(paper))
            except Exception:
                paper.moderator_overrides = ''
        # If the moderator edits a paper they have already signed off,
        # revert it back to "flagged" so they must sign off again.
        if _is_mod_edit and (paper.moderation_status or '') == 'signed_off':
            paper.moderation_status = 'flagged'
            paper.signed_off_at = None
            # Clear the previous moderated snapshot — it's now stale.
            paper.sections_moderated = ''
        db.session.commit()
        # Remember which paper this user last touched so the listing can
        # surface it as a spotlighted card with one-click Memo / Paper
        # preview links.
        try:
            session['last_edited_paper_id'] = paper.id
        except Exception:
            pass
        if request.form.get('__autosave') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if logo_upload_error:
                return (logo_upload_error, 415)
            return ('', 204)
        if logo_upload_error:
            flash(logo_upload_error, 'warning')
        else:
            flash('Paper saved.', 'success')
        return redirect(url_for('teacher_paper_edit', paper_id=paper.id))

    if current_user.is_admin:
        bank_q = QuestionBankItem.query
    else:
        bank_q = QuestionBankItem.query.filter(_bank_visible_filter())
    if paper and paper.subject:
        bank_q = bank_q.filter(QuestionBankItem.subject.in_(
            _expand_subject_aliases([paper.subject])))
    bank = bank_q.order_by(
        QuestionBankItem.topic, QuestionBankItem.created_at.desc()).all()
    # Make sure every question referenced by THIS paper's sections is
    # available in `bank` — even if it's outside the teacher's normal
    # visibility scope (e.g. a moderator editing another teacher's
    # private question, or an imported paper that references items the
    # current user wouldn't otherwise see). The editor renders the full
    # body of each question inline, so it needs them all.
    if paper:
        try:
            _bank_ids = {b.id for b in bank}
            _ref_ids = []
            for _sec in (json.loads(paper.sections or '[]') or []):
                if isinstance(_sec, dict):
                    for _qid in (_sec.get('question_ids') or []):
                        if _qid and _qid not in _bank_ids and _qid not in _ref_ids:
                            _ref_ids.append(_qid)
            if _ref_ids:
                _extra = (QuestionBankItem.query
                          .filter(QuestionBankItem.id.in_(_ref_ids)).all())
                bank = list(bank) + list(_extra)
        except Exception:
            pass
    # CAPS-aligned scaffolds: rendered as preset buttons in the editor.
    caps_templates = {
        key: {
            'label': tpl['label'],
            'subject': tpl.get('subject', ''),
            'paper_number': tpl.get('paper_number', ''),
            'grade': tpl.get('grade'),
            'duration_minutes': tpl.get('duration_minutes'),
            'total_marks': tpl.get('total_marks'),
            'instructions': tpl.get('instructions', ''),
            'sections': flatten_template(key),
        }
        for key, tpl in CAPS_PAPER_TEMPLATES.items()
        if _canonical_subject(tpl.get('subject')) == _canonical_subject(paper.subject)
    }
    if paper and paper.id:
        try:
            session['last_edited_paper_id'] = paper.id
        except Exception:
            pass
    paper_for_edit = _paper_render_copy(paper, sanitize_cover_note=True) if paper else None
    _html = render_template('teacher/generator_edit.html',
                            paper=paper_for_edit, bank=bank,
                            subject_choices=_generator_subject_choices(),
                            caps_templates=caps_templates,
                            caps_guidelines=CAPS_GUIDELINES,
                            instruction_library=INSTRUCTION_LIBRARY,
                            is_mod_edit=_is_mod_edit)
    # Never let the browser serve a stale cached copy of the editor: the page
    # carries all of its JS inline, so a cached HTML means cached (old) logic.
    _resp = Response(_html)
    _resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    _resp.headers['Pragma'] = 'no-cache'
    _resp.headers['Expires'] = '0'
    return _resp


@app.route('/teacher/generator/<paper_id>/delete', methods=['POST'])
@teacher_required
def teacher_paper_remove(paper_id):
    paper = GeneratedPaper.query.get_or_404(paper_id)
    if paper.owner_id != current_user.id and not current_user.is_admin: abort(403)
    # The seeded/imported official library papers are protected so the
    # shared library can't be accidentally wiped. Papers created via
    # "Add new paper" (and clones) may be deleted by their owner.
    if paper.is_library:
        flash('Library papers cannot be deleted. Clone it first if you want to remove your own copy.', 'warning')
        return redirect(url_for('teacher_papers_generated'))
    db.session.delete(paper); db.session.commit()
    flash('Paper deleted.', 'info')
    return redirect(url_for('teacher_papers_generated'))


@app.route('/teacher/generator/bulk_delete', methods=['POST'])
@teacher_required
def teacher_paper_bulk_remove():
    """Delete one, many, or all generated papers the current user is
    permitted to remove (their own, or any if admin). Accepts either an
    explicit list of paper IDs in form field 'paper_ids', or
    'scope=all' to delete every paper the user owns (or every paper
    in the system for admins)."""
    scope = (request.form.get('scope') or '').strip().lower()
    if scope == 'all':
        q = GeneratedPaper.query
        if not current_user.is_admin:
            q = q.filter(GeneratedPaper.owner_id == current_user.id)
        papers = q.all()
    else:
        ids = request.form.getlist('paper_ids')
        if not ids:
            flash('No papers selected.', 'warning')
            return redirect(url_for('teacher_papers_generated'))
        papers = GeneratedPaper.query.filter(GeneratedPaper.id.in_(ids)).all()
    deleted = 0
    skipped = 0
    protected = 0
    for paper in papers:
        if paper.owner_id != current_user.id and not current_user.is_admin:
            skipped += 1
            continue
        # Protect seeded/imported library papers from deletion.
        if paper.is_library:
            protected += 1
            continue
        db.session.delete(paper)
        deleted += 1
    db.session.commit()
    if deleted:
        flash(f'{deleted} paper{"s" if deleted != 1 else ""} deleted.', 'info')
    if skipped:
        flash(f'{skipped} paper{"s" if skipped != 1 else ""} skipped (no permission).', 'warning')
    if protected:
        flash(f'{protected} library paper{"s" if protected != 1 else ""} skipped (library papers cannot be deleted).', 'warning')
    return redirect(url_for('teacher_papers_generated'))


@app.route('/teacher/generator/<paper_id>/clone', methods=['POST'])
@teacher_required
def teacher_paper_clone(paper_id):
    """Clone an entire existing paper into the current user's workspace
    as a fresh draft. Copies header fields and all sections/questions
    (the question_ids inside each section continue to reference the
    same QuestionBankItem rows, which the user is allowed to read via
    the bank's visibility rules). Moderation state is reset.
    """
    src = GeneratedPaper.query.get_or_404(paper_id)
    if not _can_view_paper(src):
        abort(403)
    # Fields to carry over verbatim — header/cover/footer plus content.
    copy_fields = (
        'title', 'school_name', 'subject', 'grade', 'exam_date',
        'duration_minutes', 'total_marks', 'examiner', 'moderator',
        'instructions', 'logo_path', 'paper_number', 'cover_authority',
        'cover_subtitle', 'header_left', 'header_right', 'sub_header',
        'footer_left', 'footer_center', 'footer_right', 'memo_title',
        'cover_extra_note', 'sections',
    )
    new_paper = GeneratedPaper(owner_id=current_user.id)
    for f in copy_fields:
        setattr(new_paper, f, getattr(src, f))
    # Prefix the title so the teacher can spot the copy in their list.
    base_title = (src.title or 'Examination Paper').strip()
    if not base_title.lower().startswith('copy of '):
        new_paper.title = f'Copy of {base_title}'
    # Fresh moderation state — the clone starts as a private draft.
    new_paper.moderation_status = 'draft'
    new_paper.share_scope = 'private'
    new_paper.moderator_id = None
    new_paper.moderator_notes = ''
    new_paper.flagged_at = None
    new_paper.signed_off_at = None
    new_paper.sections_original = ''
    new_paper.sections_moderated = ''
    new_paper.sections_final = ''
    new_paper.header_original = ''
    new_paper.moderator_overrides = ''
    db.session.add(new_paper)
    db.session.commit()
    flash('Paper cloned. You are now editing your own copy.', 'success')
    return redirect(url_for('teacher_paper_edit', paper_id=new_paper.id))


@app.route('/teacher/generator/<paper_id>/add_stem', methods=['POST'])
@teacher_required
def teacher_paper_add_stem(paper_id):
    """Create a 0-mark scenario-stem QuestionBankItem (text + optional image)
    and return its id/text/image_path as JSON for the editor to inject into
    the current section. The stem is owned by the current user but stays
    private (is_shared=False) so it doesn't pollute the shared bank.
    """
    paper = GeneratedPaper.query.get_or_404(paper_id)
    if paper.owner_id != current_user.id and not current_user.is_admin:
        abort(403)
    text = (request.form.get('text') or '').strip()
    if not text:
        return ({'error': 'Stem text is required.'}, 400)
    img = request.files.get('image')
    image_rel = ''
    if img and img.filename:
        image_rel, _ = _save_upload(img, 'questions', TEACHER_LOGO_EXTS)
        if not image_rel:
            return ({'error': 'Unsupported image format. Use PNG, JPG, JPEG, SVG, WEBP, GIF, BMP, or AVIF.'}, 415)
    item = QuestionBankItem(
        owner_id=current_user.id,
        grade=paper.grade or 12,
        topic='Stem',
        subtopic='',
        difficulty='medium',
        question_type='stem',
        question_text=text,
        answer_text='',
        marks=0,
        tags='stem',
        is_shared=False,
        image_path=image_rel or '',
    )
    db.session.add(item)
    db.session.commit()
    return ({
        'id': item.id,
        'text': item.question_text,
        'marks': 0,
        'image_path': item.image_path,
        'type': 'stem',
        'topic': 'Stem',
    }, 200)


def _is_matching_question(q):
    """Return True if q is a match_columns type question."""
    return (getattr(q, 'question_type', '') or '').lower() == 'match_columns' or \
           bool(_MATCH_INTRO_RE.match((getattr(q, 'question_text', '') or '').lstrip()))


def _split_mcq_matching(qs, sec_title, sec_instructions):
    """If a section contains both MCQ and matching questions, split into
    separate sub-sections: MCQ first, then matching.  Any non-MCQ/non-matching
    questions go into a 'rest' group after matching.
    Returns a list of section dicts (may be length 1 if no split needed)."""
    mcq_qs, match_qs, rest_qs = [], [], []
    for q in qs:
        if _is_matching_question(q):
            match_qs.append(q)
        elif (getattr(q, 'question_type', '') or '').lower() in ('mcq', 'multiple_choice'):
            mcq_qs.append(q)
        else:
            rest_qs.append(q)

    # Only split when both groups are non-empty.
    if not (mcq_qs and match_qs):
        return None  # caller will use the original single section

    result = []
    if mcq_qs:
        result.append({'title': sec_title, 'sub_title': 'MULTIPLE-CHOICE',
                       'instructions': sec_instructions,
                       'questions': mcq_qs,
                       'marks': sum(q.marks or 0 for q in mcq_qs),
                       'is_tf': False, 'is_split_child': True})
    if match_qs:
        result.append({'title': sec_title, 'sub_title': 'MATCHING ITEMS',
                       'instructions': '',
                       'questions': match_qs,
                       'marks': sum(q.marks or 0 for q in match_qs),
                       'is_tf': False, 'is_split_child': True})
    if rest_qs:
        result.append({'title': sec_title, 'sub_title': '',
                       'instructions': '',
                       'questions': rest_qs,
                       'marks': sum(q.marks or 0 for q in rest_qs),
                       'is_tf': False, 'is_split_child': True})
    return result


def _split_question_subitems(text, qn):
    """Parse an imported past-paper Question body into structured sub-items.

    Imported PDFs concatenate a Question's whole body (lead title + intro +
    every sub-item line) into one ``question_text`` blob. To render them as
    DBE-style numbered rows with marks on the far right, split that blob
    into ``{label, text, marks}`` entries plus an ``intro`` string and an
    optional ``lead_title``.

    Returns a dict with keys ``lead_title``, ``intro``, ``items`` — or
    ``None`` if the text doesn't look like a multi-sub-item Question.
    """
    if not text or not str(text).strip():
        return None
    raw = str(text).replace('\r', '')
    # DBE matching-items questions (Q2 with COLUMN A / COLUMN B and a
    # "(N x 1)" mark indicator) must NOT be split into per-row sub-items
    # — the bullets_to_html filter renders the whole block as a single
    # two-column table, and splitting destroys the layout.
    _u = ' '.join(raw.upper().split())
    if (
        'COLUMN A' in _u and 'COLUMN B' in _u
        and re.search(r'\(\s*\d+\s*[X×]\s*1\s*\)', _u)
    ):
        return None
    # Normalise tabs to spaces and dedent each line.
    lines = [ln.rstrip() for ln in raw.split('\n')]
    # Strip leading whitespace per line but keep blank-line separators.
    lines = [ln.strip() for ln in lines]
    qn_str = str(qn)
    sub_re = re.compile(r'^' + re.escape(qn_str) + r'\.(\d+(?:\.\d+)?)\s+(.*)$')
    marks_tail_re = re.compile(r'\s*\(\s*(\d+)\s*\)\s*$')

    lead_title = ''
    intro_lines = []
    items = []
    cur = None  # current sub-item being accumulated

    # First non-empty line that is ALL-CAPS short heading -> lead_title.
    # Skip leading "SECTION A/B/..." banner and "QUESTION N" header lines
    # so the real subject heading (e.g. "MULTIPLE-CHOICE QUESTIONS") is
    # captured instead. Both leftovers are stripped from the intro
    # afterwards too.
    started = False
    _skip_pat = re.compile(
        r'^(?:SECTION\s+[A-Z]|QUESTION\s+\d+(?:\s*[:.\-\u2013\u2014].*)?)$',
        re.IGNORECASE)
    for ln in lines:
        if not started and ln:
            stripped = ln.strip()
            # Skip stand-alone "SECTION X" / "QUESTION N" banners while
            # still searching for the real lead title.
            if _skip_pat.match(stripped):
                continue
            # Heuristic: short uppercase heading like "WORD PROCESSING"
            if (len(stripped) <= 60
                    and stripped == stripped.upper()
                    and re.fullmatch(r'[A-Z0-9 ()/\-&,.]+', stripped)):
                lead_title = stripped
                started = True
                continue
            started = True
        m = sub_re.match(ln) if ln else None
        if m:
            # Close previous sub-item.
            if cur is not None:
                items.append(cur)
            label = qn_str + '.' + m.group(1)
            body = m.group(2).strip()
            cur = {'label': label, 'text': body, 'marks': 0}
        else:
            if cur is None:
                # Still in intro region.
                intro_lines.append(ln)
            else:
                # Continuation of current sub-item body. Preserve bullet
                # lines (•, -, *) and blank-line paragraph breaks as their
                # own lines so the rendered question keeps its DBE layout.
                if not ln:
                    # Mark a hard paragraph break — bullets_to_html turns
                    # any blank line in the body into a real line gap, so
                    # an Enter the teacher pressed in the inline editor
                    # actually drops to a new line in the printed paper.
                    if not cur['text'].endswith('\n\n'):
                        cur['text'] = cur['text'].rstrip() + '\n\n'
                elif re.match(r'^\s*(?:[\u2022\u25cf\u25aa\u25e6\*\-\u2013\u2014]|o\s)', ln):
                    cur['text'] = cur['text'].rstrip() + '\n' + ln
                else:
                    # If the previous content ended in a paragraph break
                    # (blank line) keep the break — don't flatten back
                    # into a soft-wrap. Otherwise it's a soft-wrapped
                    # continuation of the previous text line.
                    if cur['text'].endswith('\n\n'):
                        cur['text'] = cur['text'] + ln
                    elif cur['text'].endswith('\n'):
                        cur['text'] = cur['text'] + ln
                    else:
                        cur['text'] = cur['text'] + ' ' + ln
    if cur is not None:
        items.append(cur)
    # Extract trailing "(N)" marks for each sub-item. The marks may sit on
    # their own line in the middle of the body (followed by a "Save and
    # close…" closer) — capture either pattern and pull the closer out as
    # an outro for the Question.
    outro_lines = []  # legacy; unused now (post_text per item)
    marks_line_re = re.compile(r'(?:^|\n)\s*\(\s*(\d+)\s*\)\s*(?=\n|$)')
    # Marks can also appear at end-of-line with text before them, followed
    # by a closer line like "Save and close the document." e.g.
    #   "Change the direction of the text to horizontal.    (3)\nSave and close…"
    marks_eol_re = re.compile(r'\(\s*(\d+)\s*\)[ \t]*\n')
    last_after_item = None
    for it in items:
        it['post_text'] = ''
        # Prefer a "(N)" sitting on its own line first — these are the
        # canonical DBE per-sub-item marks. A trailing "(N)" on the
        # final sentence is often the bonus / closing-tag mark for the
        # whole Question (e.g. "ONE mark will be allocated… (1)") and
        # should NOT be claimed by the last sub-item.
        ml = marks_line_re.search(it['text'])
        if ml:
            it['marks'] = int(ml.group(1))
            before = it['text'][:ml.start()].rstrip()
            after = it['text'][ml.end():].strip()
            it['text'] = before
            if after:
                it['post_text'] = after
                last_after_item = it
            continue
        mt = marks_tail_re.search(it['text'])
        if mt:
            it['marks'] = int(mt.group(1))
            it['text'] = marks_tail_re.sub('', it['text']).strip()
        else:
            me = marks_eol_re.search(it['text'])
            if me:
                it['marks'] = int(me.group(1))
                before = it['text'][:me.start()].rstrip()
                after = it['text'][me.end():].strip()
                it['text'] = before
                if after:
                    it['post_text'] = after
                    last_after_item = it
        # Strip an extra leading numeric prefix that may have leaked back in.
        it['text'] = re.sub(r'^\s*' + re.escape(qn_str) + r'\.\d+(?:\.\d+)?\s+', '', it['text'])
    # Promote the final "Save and close…" closer line of the LAST item with
    # trailing text into the group-level outro so pagination can still hide
    # it on continuation pages and show it once at the end.
    outro = ''
    if last_after_item is not None:
        post = last_after_item['post_text']
        # Split the last item's post_text into a leading mid-Question
        # subheading (e.g. "Work in the X worksheet.") and a trailing
        # closer (e.g. "Save and close the Y document."). The closer
        # alone becomes the group outro; the rest stays on the item.
        post_lines = [ln.strip() for ln in post.split('\n') if ln.strip()]
        closer_idx = None
        for idx in range(len(post_lines) - 1, -1, -1):
            if re.match(r'(?i)^(save\s+and\s+close|close\s+the|save\s+the)\b', post_lines[idx]):
                closer_idx = idx
                break
        if closer_idx is not None:
            outro = '\n'.join(post_lines[closer_idx:]).strip()
            last_after_item['post_text'] = '\n'.join(post_lines[:closer_idx]).strip()
    # Trim intro: drop blank top/bottom; collapse multi-blanks.
    while intro_lines and not intro_lines[0]:
        intro_lines.pop(0)
    while intro_lines and not intro_lines[-1]:
        intro_lines.pop()
    # Strip a leading "QUESTION N" / "QUESTION N: SUBJECT" header line —
    # the print template already renders that as the group head, so
    # leaving it in the intro produces a visible duplicate above the body.
    # Optionally also promote the colon-suffix ("TRUE/FALSE ITEMS") into
    # ``lead_title`` when one wasn't picked up earlier, so the group head
    # still shows "QUESTION 3: TRUE/FALSE ITEMS".
    if intro_lines:
        # Strip a "SECTION X" banner first (it leaks in from the page
        # header), then look for a "QUESTION N" line and promote any
        # colon-suffix into lead_title.
        if re.match(r'^\s*SECTION\s+[A-Z]\s*$', intro_lines[0], re.IGNORECASE):
            intro_lines.pop(0)
            while intro_lines and not intro_lines[0]:
                intro_lines.pop(0)
    if intro_lines:
        _m_qh = re.match(
            r'^\s*QUESTION\s+' + re.escape(qn_str)
            + r'\b[ \t:.\-\u2013\u2014]*(.*)$',
            intro_lines[0], re.IGNORECASE)
        if _m_qh:
            _tail = _m_qh.group(1).strip()
            if _tail and not lead_title:
                lead_title = _tail
            intro_lines.pop(0)
            while intro_lines and not intro_lines[0]:
                intro_lines.pop(0)
    intro = '\n'.join(intro_lines).strip()
    if not items:
        return None
    return {'lead_title': lead_title, 'intro': intro, 'outro': outro, 'items': items}


# ---------------------------------------------------------------------------
# CAT P1 reference appendices (HTML tag sheet + Input-mask character sheet).
# These are standard reference tables that appear at the end of every CAT P1
# paper. PDF extraction mangles them into a single garbled string in the last
# group's outro; we strip that out and render the structured tables instead.
# ---------------------------------------------------------------------------

_APPENDIX_HTML_TAG_SHEET = {
    'kind': 'tags',
    'title': 'HTML TAG SHEET',
    'sections': [
        ('Basic Tags', [
            ('<body></body>', 'Defines the body of the web page'),
            ('<body bgcolor="pink">', 'Sets the background colour of the web page'),
            ('<body text="black">', 'Sets the colour of the body text'),
            ('<head></head>', 'Contains information about the web page'),
            ('<html></html>', 'Creates an HTML document – starts and ends a web page'),
            ('<title></title>', 'Defines a title for the web page'),
            ('<br/>', 'Inserts a line break'),
            ('<!-- -->', 'Comment'),
        ]),
        ('Text Tags', [
            ('<h1></h1>', 'Creates the largest heading'),
            ('<h6></h6>', 'Creates the smallest heading'),
            ('<b></b>', 'Creates bold text'),
            ('<i></i>', 'Creates italic text'),
            ('<u></u>', 'Creates underlined text'),
            ('<font size="3"></font>', 'Sets size of font, from "1" to "7"'),
            ('<font color="green"></font>', 'Sets font colour'),
            ('<font face="Times New Roman"></font>', 'Sets font type'),
        ]),
        ('Links Tags', [
            ('<a href="URL"></a>', 'Creates a hyperlink'),
            ('<a href="URL"><img src="name"/></a>', 'Creates an image link'),
            ('<a name="NAME"></a>', 'Creates a target location in the document'),
            ('<a href="#NAME"></a>', 'Links to a target location created somewhere else in the document'),
            ('<a href="mailto:NAME">', 'Links to an e-mail address'),
        ]),
        ('Formatting Tags', [
            ('<p></p>', 'Creates a new paragraph'),
            ('<p align="left">', 'Aligns a paragraph to the "left" (default), can also be "right" or "center"'),
            ('<center></center>', 'Horizontally centres text, a section, table or an image'),
            ('<ol type="A","a","I","i","1">', 'Defines the type of numbering used'),
            ('<ol></ol>', 'Creates a numbered list'),
            ('<ul></ul>', 'Creates a bulleted list'),
            ('<ul type="disc","square","circle"></ul>', 'Defines the type of bullets used'),
        ]),
        ('Formatting Tags continued', [
            ('<li></li>', 'Inserted before each list item, and adds a number or symbol depending on the type of list selected'),
            ('<img src="name"/>', 'Adds an image'),
            ('<img src="name" align="left"/>', 'Aligns an image: can be "right", "bottom", "top"'),
            ('<p align="center"><img src="name"/></p>', 'Aligns an image in the "center", can also be "middle"'),
            ('<img src="name" border="1"/>', 'Sets the size of the border around an image'),
            ('<img src="name" width="200" height="200"/>', 'Sets the height and width of an image'),
            ('<img src="name" alt="alternative text"/>', 'Displays alternative text when the mouse hovers over the image or when the image is not found'),
            ('<hr/>', 'Inserts a horizontal line'),
            ('<hr size="3"/>', 'Sets size (height) of a line'),
            ('<hr width="80%"/>', 'Sets the width of a line, in percentage or absolute value'),
            ('<hr color="ff0000"/>', 'Sets the colour of the line'),
        ]),
        ('Table Tags', [
            ('<table></table>', 'Creates a table'),
            ('<tr></tr>', 'Creates a row in a table'),
            ('<td></td>', 'Creates a cell in a table'),
            ('<th></th>', 'Creates a table header (a cell with bold, centred text)'),
            ('<table width="50">', 'Sets the width of the table'),
            ('<table border="1">', 'Sets the width of the border around the table cells'),
            ('<table cellspacing="1">', 'Sets the space between the table cells'),
            ('<table cellpadding="1">', 'Sets the space between a cell border and its contents'),
            ('<tr align="left">', 'Sets the alignment for cell(s) ("left", can also be "center" or "right")'),
            ('<tr valign="top">', 'Sets the vertical alignment for cell(s) ("top", can also be "middle" or "bottom")'),
            ('<td colspan="2">', 'Sets the number of columns a cell should span'),
            ('<td rowspan="4">', 'Sets the number of rows a cell should span'),
        ]),
    ],
}

# CAT P1 May/June 2021 ships a *reduced* HTML tag sheet (no <u>, no mailto,
# no <center>, img tags written without the trailing slash, and a slightly
# different image-alignment wording). Later papers (Nov 2021, 2022+) use the
# fuller default sheet above, so this variant is selected only for the
# May/June 2021 paper via _select_html_tag_sheet().
_APPENDIX_HTML_TAG_SHEET_MJ2021 = {
    'kind': 'tags',
    'title': 'HTML TAG SHEET',
    'sections': [
        ('Basic Tags', [
            ('<body></body>', 'Defines the body of the web page'),
            ('<body bgcolor="pink">', 'Sets the background colour of the web page'),
            ('<body text="black">', 'Sets the colour of the body text'),
            ('<head></head>', 'Contains information about the web page'),
            ('<html></html>', 'Creates an HTML document – starts and ends a web page'),
            ('<title></title>', 'Defines a title for the web page'),
            ('<br/>', 'Inserts a line break'),
            ('<!-- -->', 'Comment'),
        ]),
        ('Text Tags', [
            ('<h1></h1>', 'Creates the largest heading'),
            ('<h6></h6>', 'Creates the smallest heading'),
            ('<b></b>', 'Creates bold text'),
            ('<i></i>', 'Creates italic text'),
            ('<font size="3"></font>', 'Sets size of font, from "1" to "7"'),
            ('<font color="green"></font>', 'Sets font colour'),
            ('<font face="Times New Roman"></font>', 'Sets font type'),
        ]),
        ('Links Tags', [
            ('<a href="URL"></a>', 'Creates a hyperlink'),
            ('<a href="URL"><img src="name"></a>', 'Creates an image link'),
            ('<a name="NAME"></a>', 'Creates a target location in the document'),
            ('<a href="#NAME"></a>', 'Links to a target location created somewhere else in the document'),
        ]),
        ('Formatting Tags', [
            ('<p></p>', 'Creates a new paragraph'),
            ('<p align="left">', 'Aligns a paragraph to the "left" (default), can also be "right" or "center"'),
            ('<ol type="A","a","I","i","1">', 'Defines the type of numbering used'),
            ('<ol></ol>', 'Creates a numbered list'),
            ('<ul></ul>', 'Creates a bulleted list'),
            ('<ul type="disc","square","circle"></ul>', 'Defines the type of bullets used'),
        ]),
        ('Formatting Tags continued', [
            ('<li></li>', 'Inserted before each list item, and adds a number or symbol depending on the type of list selected'),
            ('<img src="name">', 'Adds an image'),
            ('<img src="name" align="left">', 'Aligns an image: can be "left", "right", "bottom", "top", "middle"'),
            ('<align="center"><img src="name">', 'Aligns an image to the "center"'),
            ('<img src="name" border="1">', 'Sets the size of the border around an image'),
            ('<img src="name" width="200" height="200">', 'Sets the height and width of an image'),
            ('<img src="name" alt="alternative text">', 'Displays alternative text when the mouse hovers over the image or when the image is not found'),
            ('<hr/>', 'Inserts a horizontal line'),
            ('<hr size="3"/>', 'Sets size (height) of a line'),
            ('<hr width="80%"/>', 'Sets the width of a line, in percentage or absolute value'),
            ('<hr color="ff0000"/>', 'Sets the colour of the line'),
        ]),
        ('Table Tags', [
            ('<table></table>', 'Creates a table'),
            ('<tr></tr>', 'Creates a row in a table'),
            ('<td></td>', 'Creates a cell in a table'),
            ('<th></th>', 'Creates a table header (a cell with bold, centred text)'),
            ('<table width="50">', 'Sets the width of the table'),
            ('<table border="1">', 'Sets the width of the border around the table cells'),
            ('<table cellspacing="1">', 'Sets the space between the table cells'),
            ('<table cellpadding="1">', 'Sets the space between a cell border and its contents'),
            ('<tr align="left">', 'Sets the alignment for cell(s) ("left", can also be "center" or "right")'),
            ('<tr valign="top">', 'Sets the vertical alignment for cell(s) ("top", can also be "middle" or "bottom")'),
            ('<td colspan="2">', 'Sets the number of columns a cell should span'),
            ('<td rowspan="4">', 'Sets the number of rows a cell should span'),
        ]),
    ],
}


def _select_html_tag_sheet(paper):
    """Return a year-specific HTML TAG SHEET variant to substitute for the
    default expanded sheet, or None to keep the default. Only CAT P1
    May/June 2021 currently needs the reduced variant."""
    title = (getattr(paper, 'title', '') or '')
    t = title.lower()
    is_p1 = ('p1' in t) or str(getattr(paper, 'paper_number', '') or '').strip() in ('1', 'P1')
    is_mj_2021 = ('2021' in t) and ('may' in t or 'june' in t) and ('nov' not in t)
    if is_p1 and is_mj_2021:
        return _APPENDIX_HTML_TAG_SHEET_MJ2021
    return None

_APPENDIX_INPUT_MASK = {
    'kind': 'chars',
    'title': 'INPUT MASK CHARACTER SHEET',
    'sections': [
        ('Input mask characters', [
            ('0', 'Digit (0 to 9, entry required, plus [+] and minus [–] signs not allowed)'),
            ('9', 'Digit or space (entry not required, plus and minus signs not allowed)'),
            ('#', 'Digit or space (entry not required; spaces are displayed as blanks while in Edit mode, but blanks are removed when data is saved; plus and minus signs allowed)'),
            ('L', 'Letter (A to Z, entry required)'),
            ('?', 'Letter (A to Z, entry optional)'),
            ('A', 'Letter or digit (entry required)'),
            ('a', 'Letter or digit (entry optional)'),
            ('&', 'Any character or a space (entry required)'),
            ('C', 'Any character or a space (entry optional)'),
            ('. , : ; - /', 'Decimal placeholder and thousand, date and time separators (the actual character used depends on the settings in the Regional Settings Properties dialog box in the Windows Control Panel)'),
            ('<', 'Causes all characters to be converted to lowercase'),
            ('>', 'Causes all characters to be converted to uppercase'),
            ('!', 'Causes the input mask to display from right to left, rather than from left to right. Characters typed into the mask always fill it from left to right. You can include the exclamation point anywhere in the input mask'),
            ('\\', 'Causes the character that follows to be displayed as the literal character (for example, \\A is displayed as just A)'),
        ]),
    ],
}

# Per-paper file-name lists for the candidate INFORMATION SHEET. Keyed by a
# best-effort "paper key" so we can ship reference data for several papers.
# Each entry maps the question number (int) to a dict with the file-name
# list and the expected per-Q total marks (used as a fallback if the
# extracted question data is missing marks).
_INFO_SHEET_FILES = {
    # CAT P1 May/June 2025
    'CAT_P1_2025_06': {
        1: {'files': ['1eSports'],                                          'marks': 27},
        2: {'files': ['2Stats'],                                            'marks': 18},
        3: {'files': ['3Rank'],                                             'marks': 16},
        4: {'files': ['4Shop'],                                             'marks': 24},
        5: {'files': ['5Games'],                                            'marks': 35},
        6: {'files': ['6_1Tournament', '6_2Entry'],                         'marks': 15},
        7: {'files': ['7Report', '7Staff', '7Export', '7Results'],          'marks': 15},
    },
    # CAT P1 November 2025
    'CAT_P1_2025_11': {
        1: {'files': ['1Courses'],                                          'marks': 22},
        2: {'files': ['2Brochure'],                                         'marks': 23},
        3: {'files': ['3Lecturers'],                                        'marks': 22},
        4: {'files': ['4Students'],                                         'marks': 18},
        5: {'files': ['5Records'],                                          'marks': 35},
        6: {'files': ['6_1Home', '6_2Popular'],                             'marks': 15},
        7: {'files': ['7Letter', '7Stats'],                                 'marks': 15},
    },
    # CAT P1 November 2022
    'CAT_P1_2022_11': {
        1: {'files': ['1Tourism'],                                          'marks': 26},
        2: {'files': ['2Competition'],                                      'marks': 19},
        3: {'files': ['3Tourists'],                                         'marks': 21},
        4: {'files': ['4Sightings'],                                        'marks': 19},
        5: {'files': ['5Bookings'],                                         'marks': 35},
        6: {'files': ['6_1Dolphin', '6_2Heritage'],                         'marks': 15},
        7: {'files': ['7BigFive', '7Map', '7TravelMode'],                   'marks': 15},
    },
    # CAT P1 November 2023
    'CAT_P1_2023_11': {
        1: {'files': ['1Top10'],                                            'marks': 24},
        2: {'files': ['2Tips'],                                             'marks': 21},
        3: {'files': ['3CarSales'],                                         'marks': 17},
        4: {'files': ['4Sales'],                                            'marks': 23},
        5: {'files': ['5Shuttle'],                                          'marks': 35},
        6: {'files': ['6_1Win', '6_2Opening'],                              'marks': 15},
        7: {'files': ['7Bookings', '7New', '7NewLogo'],                     'marks': 15},
    },
    # CAT P1 May/June 2024
    'CAT_P1_2024_06': {
        1: {'files': ['1Zoo'],                                              'marks': 26},
        2: {'files': ['2Adoption'],                                         'marks': 19},
        3: {'files': ['3Budget'],                                           'marks': 19},
        4: {'files': ['4Excursions'],                                       'marks': 21},
        5: {'files': ['5Animals'],                                          'marks': 35},
        6: {'files': ['6_1Advert', '6_1Nav', '6_2Fees'],                    'marks': 15},
        7: {'files': ['7AccessCard', '7Merged', '7Reproduction', '7Pics (compressed folder)'], 'marks': 15},
    },
    # CAT P1 November 2021
    'CAT_P1_2021_11': {
        1: {'files': ['1Health'],                                           'marks': 25},
        2: {'files': ['2Marine'],                                           'marks': 20},
        3: {'files': ['3Projects'],                                         'marks': 21},
        4: {'files': ['4Air'],                                              'marks': 19},
        5: {'files': ['5Save'],                                             'marks': 35},
        6: {'files': ['6_1Clean', '6_2Pollute'],                            'marks': 15},
        7: {'files': ['7Letter', '7Merge', '7Date', '7Picture'],           'marks': 15},
    },
}

# Suite/browser option lists per paper year. The DBE info sheet refreshes
# the listed Office versions every year.
_INFO_SHEET_SUITES = {
    'CAT_P1_2022_11': ['Microsoft Office 2013', 'Microsoft Office 2016', 'Microsoft Office 2019', 'Office 365/\nMicrosoft Office 2021'],
    'CAT_P1_2025_06': ['Microsoft Office 2016', 'Microsoft Office 2019', 'Microsoft Office 2021', 'Office 365'],
    'CAT_P1_2025_11': ['Microsoft Office 2016', 'Microsoft Office 2019', 'Microsoft Office 2021', 'Office 365'],
    'CAT_P1_2023_11': ['Microsoft Office 2016', 'Microsoft Office 2019', 'Microsoft Office 2021', 'Office 365'],
    'CAT_P1_2024_06': ['Microsoft Office 2013', 'Microsoft Office 2016', 'Microsoft Office 2019', 'Office 365/\nMicrosoft Office 2021'],
    'CAT_P1_2021_11': ['Microsoft Office 2013', 'Microsoft Office 2016', 'Microsoft Office 2019', 'Office 365'],
}

# Markers we look for inside the trailing outro/text to know an appendix
# follows. Order matters: HTML tag sheet usually precedes input-mask sheet.
_APPENDIX_MARKERS = [
    ('HTML TAG SHEET', _APPENDIX_HTML_TAG_SHEET),
    ('INPUT MASK CHARACTER SHEET', _APPENDIX_INPUT_MASK),
]


def _build_info_sheet_appendix(paper, resolved_sections):
    """Build the candidate INFORMATION SHEET appendix from the live paper +
    sections. Returns ``None`` when we have no file-name data for this paper."""
    # Pick the file-name map. For now we only know CAT P1 2025 June; fall
    # through to a generic stub keyed solely on Q numbers + marks if no
    # explicit map matches.
    subj = (getattr(paper, 'subject', '') or '').upper()
    title = (getattr(paper, 'title', '') or '').upper()
    combined = f'{subj} {title}'
    # Info sheet only applies to the CAT P1 (practical) paper — never P2.
    is_p1 = ('P1' in combined) or ('PAPER 1' in combined) or ('PAPER1' in combined)
    is_p2 = ('P2' in combined) or ('PAPER 2' in combined) or ('PAPER2' in combined)
    files_map = None
    paper_key = None
    if ('CAT' in subj or 'COMPUTER APPLICATIONS' in subj) and is_p1 and not is_p2:
        is_nov = ('NOV' in combined) or ('NOVEMBER' in combined)
        if '2021' in combined and is_nov:
            paper_key = 'CAT_P1_2021_11'
        elif '2022' in combined and is_nov:
            paper_key = 'CAT_P1_2022_11'
        elif '2023' in combined and is_nov:
            paper_key = 'CAT_P1_2023_11'
        elif '2024' in combined:
            paper_key = 'CAT_P1_2024_06'
        elif is_nov:
            paper_key = 'CAT_P1_2025_11'
        else:
            paper_key = 'CAT_P1_2025_06'
        files_map = _INFO_SHEET_FILES.get(paper_key)
    if files_map is None:
        return None
    suites = _INFO_SHEET_SUITES.get(paper_key) or _INFO_SHEET_SUITES['CAT_P1_2025_06']
    # Resolve year/session strings from the paper key.
    if paper_key == 'CAT_P1_2021_11':
        session_line = 'DBE/November 2021'
        paper_title  = 'COMPUTER APPLICATIONS TECHNOLOGY P1 \u2013 NOVEMBER 2021'
    elif paper_key == 'CAT_P1_2022_11':
        session_line = 'DBE/November 2022'
        paper_title  = 'COMPUTER APPLICATIONS TECHNOLOGY P1 \u2013 NOVEMBER 2022'
    elif paper_key == 'CAT_P1_2024_06':
        session_line = 'DBE/May/June 2024'
        paper_title  = 'COMPUTER APPLICATIONS TECHNOLOGY P1 \u2013 MAY/JUNE 2024'
    elif paper_key == 'CAT_P1_2023_11':
        session_line = 'DBE/November 2023'
        paper_title  = 'COMPUTER APPLICATIONS TECHNOLOGY P1 \u2013 NOVEMBER 2023'
    elif paper_key == 'CAT_P1_2025_11':
        session_line = 'DBE/November 2025'
        paper_title  = 'COMPUTER APPLICATIONS TECHNOLOGY P1 \u2013 NOVEMBER 2025'
    else:
        session_line = 'DBE/May/June 2025'
        paper_title  = 'COMPUTER APPLICATIONS TECHNOLOGY P1 \u2013 MAY/JUNE 2025'
    # Walk the resolved sections, aggregate marks per Q-number. Forced
    # page-break chunking can split one logical question into multiple
    # groups: each chunk carries the SAME per-Q total in ``grp.marks`` (or
    # zero on chunks without it), and the items themselves are partitioned
    # across chunks. So we take the max ``grp.marks`` across chunks, and
    # fall back to summing item marks deduped by id when no chunk carries
    # the total.
    grp_max = {}      # qn -> max grp.marks seen
    item_marks = {}   # qn -> {item_id: marks}
    order = []
    for sec in resolved_sections:
        for g in sec.get('qgroups') or []:
            qn = g.get('qn')
            if qn is None:
                continue
            if qn not in grp_max:
                grp_max[qn] = 0
                item_marks[qn] = {}
                order.append(qn)
            gm = int(g.get('marks') or 0)
            if gm > grp_max[qn]:
                grp_max[qn] = gm
            for q in g.get('questions') or []:
                try:
                    qm = int(getattr(q, 'marks', 0) or 0)
                except Exception:
                    qm = 0
                qid = getattr(q, 'id', None) or id(q)
                item_marks[qn][qid] = qm
    rows = []
    for qn in order:
        marks = grp_max[qn]
        if marks <= 0:
            marks = sum(item_marks[qn].values())
        # If we have an expected total in the paper map, prefer it (the
        # source DBE info sheet is authoritative).
        meta = files_map.get(qn) or {}
        if isinstance(meta, dict):
            expected = int(meta.get('marks') or 0)
            files = meta.get('files') or [f'Q{qn}']
        else:
            expected = 0
            files = meta or [f'Q{qn}']
        if expected > 0:
            marks = expected
        rows.append({'qn': qn, 'marks': marks, 'files': files})
    if not rows:
        return None
    grand = sum(r['marks'] for r in rows)
    return {
        'kind': 'info',
        'title': '',  # the page renders its own header layout
        'subject_line': getattr(paper, 'subject', '') or 'COMPUTER APPLICATIONS TECHNOLOGY/P1',
        'session_line': session_line,
        'paper_title': paper_title,
        'suites': suites,
        'total_marks': grand,
        'rows': rows,
    }


def _extract_appendices(resolved_sections):
    """Strip appendix marker text out of the last group's outro and return a
    list of structured appendix dicts to render as standalone pages."""
    if not resolved_sections:
        return []
    # Find the final group across all sections.
    last_grp = None
    for sec in resolved_sections:
        for g in sec.get('qgroups') or []:
            last_grp = g
    if not last_grp:
        return []
    outro = last_grp.get('outro') or ''
    if not outro:
        return []
    # Find the earliest marker present.
    earliest = None
    for marker, _data in _APPENDIX_MARKERS:
        idx = outro.upper().find(marker)
        if idx >= 0 and (earliest is None or idx < earliest):
            earliest = idx
    if earliest is None:
        return []
    # Truncate the outro at the first marker (keep e.g. "TOTAL: 150" if
    # present above it; the grand-total div renders separately so it's
    # safe to drop the line entirely if it only contains the total).
    head = outro[:earliest].rstrip()
    # Drop a stray trailing "TOTAL: 150" line — it's already rendered.
    head = re.sub(r'(?:^|\n)\s*TOTAL\s*:\s*\d+\s*$', '', head).rstrip()
    last_grp['outro'] = head
    # Decide which appendices to include based on which markers appear.
    # CAT P1 papers always pair HTML TAG SHEET with INPUT MASK CHARACTER SHEET,
    # so if the HTML tag sheet is present we also append the input-mask sheet
    # even when the marker text was lost during PDF extraction.
    upper = outro.upper()
    out = []
    html_present = 'HTML TAG SHEET' in upper
    for marker, data in _APPENDIX_MARKERS:
        if marker in upper:
            out.append(data)
        elif marker == 'INPUT MASK CHARACTER SHEET' and html_present:
            out.append(data)
    return out


def _build_paper_context(paper, with_memo=False, version='current'):
    """Resolve question_ids in sections to full question objects.

    ``version`` selects which snapshot to render:
        'current'   — paper.sections (live working copy, default)
        'original'  — paper.sections_original (pre-moderation snapshot)
        'moderated' — paper.sections_moderated (moderator sign-off snapshot)
        'final'     — paper.sections_final (teacher-accepted snapshot)
    Falls back to the current sections if the requested snapshot is empty.
    """
    # Pre-compiled patterns used to scrub stale tail noise from imported
    # answer_text (per-mark notation, section totals, leaked next-question
    # heading). Same shape as the cleaner that already runs on question_text.
    _RE_NEXT_Q_HEAD = re.compile(
        r'\s*(?:\(\d+\)\s*)?\[\d+\]\s*QUESTION\s+\d+\s*:\s*[A-Z][A-Z0-9 ()/\-&]+\s*$',
        re.IGNORECASE,
    )
    # An imported answer sometimes carries the START of the NEXT
    # sub-question because the MG text extractor couldn't tell where
    # one stopped and the next began (e.g. "(Any two) 2\n4.8. Explain
    # multitasking\nMultitasking allows…"). Cut everything from the
    # first such leaked "N.M[.K][.] " label onward.
    _RE_LEAKED_LABEL = re.compile(
        r'\n\s*\d+\.\d+(?:\.\d+)?\.?\s+\S', re.MULTILINE)
    _RE_TRAIL_BRACKET = re.compile(r'\s*\[\d+\]\s*$')
    _RE_TRAIL_MARK_DIGITS = re.compile(r'\s+\d+(?:\s+\d+)?\s*$')

    def _clean_memo_answer(q):
        """Strip imported tail noise from `q.answer_text` and split into
        (heading, body): the FIRST non-blank line becomes the italic memo
        heading (DBE-style topical phrase, e.g. "TWO limitations for
        customers using QR codes"), the rest is the body. Falls back to
        question_text if answer_text has no separate heading line."""
        txt = (getattr(q, 'answer_text', '') or '').strip()
        if not txt:
            qt = (getattr(q, 'question_text', '') or '').strip()
            return (qt, '')
        # If the answer is hand-authored HTML (e.g. a comparison table for
        # "Difference between queries"), skip the line-by-line splitter
        # entirely — every line would be parsed as a separate "heading"
        # and escaped, exposing the raw markup. Pass the whole thing
        # through as the body so memo_ticks renders it as Markup.
        if '<table' in txt.lower() or txt.lstrip().startswith('<'):
            return ('', txt)
        # Cut any leaked next-sub-question content first.
        _m_leak = _RE_LEAKED_LABEL.search(txt)
        if _m_leak:
            txt = txt[:_m_leak.start()].rstrip()
        # Iteratively peel off trailing junk.
        for _ in range(4):
            new = _RE_NEXT_Q_HEAD.sub('', txt)
            new = _RE_TRAIL_BRACKET.sub('', new)
            new = _RE_TRAIL_MARK_DIGITS.sub('', new)
            new = new.rstrip()
            if new == txt:
                break
            txt = new
        lines = [ln for ln in txt.split('\n')]
        # Drop leading blank lines, then split off the first non-blank as heading.
        while lines and not lines[0].strip():
            lines.pop(0)
        if not lines:
            return ((getattr(q, 'question_text', '') or '').strip(), '')
        heading = lines[0].strip()
        body_lines = lines[1:]
        # Comparison-table signature: either two-plus "(Any …)" tokens
        # on one body line, OR the body contains zero enumerators
        # ("(1)", "1.", "•") AND has at least one "(Any …)" tail token.
        # The latter catches a DBE side-by-side table whose raw text
        # extraction collapsed both columns onto each line (e.g.
        # "Intranet Internet / Private network Public network / …
        # (Any two)").
        _is_cmp = any(
            len(re.findall(r'\(Any\s+[^)]+\)', _bl or '', re.I)) >= 2
            for _bl in body_lines
        )
        if not _is_cmp:
            _has_enum = any(
                re.match(r'^\s*(?:\(\d+\)|\d+[.)]|\u2022)', _bl or '')
                for _bl in body_lines)
            _has_any_tail = any(
                re.search(r'\(Any\s+[^)]+\)', _bl or '', re.I)
                for _bl in body_lines)
            if _has_any_tail and not _has_enum:
                _is_cmp = True
        # Additional cmp signature: a body line that looks like a
        # 2-column header row ("Capitalised Word(s) Capitalised Word(s)"
        # — letters/spaces/parens only, no digits, no slash, no
        # sentence punctuation) appearing BEFORE the first enumerator
        # row, combined with any "(Any …)" tail. The DBE MG often emits
        # tables like "ICT Explanation\n(1) … (1) …" or "Issue
        # Solution\n(1) …" that our row-extractor captures separately
        # in `subtables`, so the body text duplicates the column-header
        # row and must be elided from the heading.
        if not _is_cmp:
            _has_any_tail = any(
                re.search(r'\(Any\s+[^)]+\)', _bl or '', re.I)
                for _bl in body_lines)
            if _has_any_tail:
                _cap_hdr = re.compile(
                    r'^\s*[A-Z][A-Za-z()\-]+(?:\s+[A-Za-z()\-]+){0,4}\s+'
                    r'[A-Z][A-Za-z()\-]+(?:\s+[A-Za-z()\-]+){0,4}\s*$')
                for _bl in body_lines:
                    _s = (_bl or '').strip()
                    if not _s:
                        continue
                    if re.match(r'^\s*(?:\(\d+\)|\d+[.)]|\u2022)', _s):
                        break
                    if _cap_hdr.match(_s):
                        _is_cmp = True
                        break
        # Heading wrap repair: if the importer split a long heading
        # across lines (no blank separator, next line is plain text not
        # starting with a numbered/bullet marker, and the heading does
        # not already end with sentence-final punctuation), fold the
        # continuation back into the heading. Repeat until we hit a
        # blank line, an enumerator like "(1)" / "1." / "1)", a tick
        # marker, or "Reason:" / "Example:" style labels.
        _stop_re = re.compile(
            r'^\s*(?:\(\d+\)|\d+[.)]|[\u2713\u2714\uF0FB\uF0FC]|'
            r'Reason\s*:|Example\s*:|Motivation\s*:|Solution\s*:|'
            r'\(Any\b|\(Note\b|\(Accept\b|'
            r'<(?:i|b|u|em|strong|sub|sup)\b)',
            re.IGNORECASE,
        )
        _wrap_folds = 0
        while body_lines:
            _peek = body_lines[0].strip()
            if not _peek:
                break
            if _stop_re.match(_peek):
                break
            # Awarded-mark body line: any line containing a tick glyph
            # is body content (DBE memos use ticks to mark awarded
            # marks inline, e.g. "Users are tricked ✓ into clicking…").
            # Never fold such a line into the heading.
            if re.search(r'[\u2713\u2714\uF0FB\uF0FC]', _peek):
                break
            # Subgroup label ("Physical health:", "Mental and emotional
            # health:") — never merge into heading.
            if _peek.endswith(':') and len(_peek) < 80:
                break
            # Already ends a sentence — keep as body.
            if heading.endswith(('.', ':', '?', '!')):
                break
            # Comparison-table answer: allow at most one wrap-merge so a
            # split heading like "Difference between system software and
            # application\nsoftware" reunites — but never gobble the
            # column-header row or data rows below. The next line must
            # be SHORT (≤2 words) AND not look like a 2-column row
            # (e.g. "Intranet Internet" → 2 capitalised proper nouns,
            # which IS the column-headers row, not a heading wrap).
            if _is_cmp:
                if _wrap_folds >= 1:
                    break
                _words = _peek.split()
                if len(_words) > 2:
                    break
                # Two-capitalised-words row IS the column header row.
                if (len(_words) == 2
                        and _words[0][:1].isupper()
                        and _words[1][:1].isupper()):
                    break
            # Only fold the wrap line into the heading when a later
            # line clearly marks the start of the answer body (an
            # enumerator / "Reason:" / "(Any …)" etc., OR contains a
            # tick glyph anywhere — which marks the awarded mark on
            # short single-line answers like "<alt> attribute ✓").
            # Otherwise the second line IS the answer body (e.g.
            # heading="…CPU", body="64 GB") and must stay below the
            # heading.
            _has_body_marker = any(
                _stop_re.match((bl or '').strip())
                or re.search(r'[\u2713\u2714\uF0FB\uF0FC]', bl or '')
                for bl in body_lines[1:])
            if not _has_body_marker:
                break
            heading = (heading + ' ' + _peek).strip()
            body_lines.pop(0)
            _wrap_folds += 1
        # Trim leading blanks of body too.
        while body_lines and not body_lines[0].strip():
            body_lines.pop(0)
        body = '\n'.join(body_lines).rstrip()
        # If the heading contains a bullet/answer marker (starts with "(1)",
        # a digit, a tick, or a "•" bullet), the import had no separate
        # heading line — drop the heading and treat the whole answer as body.
        if re.match(r'^\s*(?:\(\d+\)|\d+[.)]|[\u2713\u2714\uF0FB\uF0FC]|\u2022)', heading):
            if heading.lstrip().startswith('\u2022'):
                # Bullet-only answer (no separate topical heading): drop heading.
                body = '\n'.join(lines).rstrip()
                heading = ''
            else:
                qt = (getattr(q, 'question_text', '') or '').strip()
                body = '\n'.join(lines).rstrip()
                heading = qt
        # Re-inject per-mark ticks the MG importer stripped. DBE memos
        # show one tick per mark inline on every awardable phrase:
        #   - Single-line short answer (no enumerator, no "(Any …)"
        #     tail): append a trailing tick per mark at end of body.
        #   - Multi-line bullets without an "(Any …)" tail: append a
        #     tick at end of EACH bullet (rendered by memo_ticks_filter
        #     after this, but only when source already has a glyph —
        #     so we drop the glyph here as actual unicode so the SVG
        #     pass picks it up).
        _marks = getattr(q, 'marks', 0) or 0
        if body and _marks:
            _bl = body.split('\n')
            _has_any = any(re.search(r'\(Any\s+[^)]+\)', x, re.I) for x in _bl)
            _has_enum = any(
                re.match(r'^\s*(?:\(\d+\)|\d+[.)]|\u2022)', x) for x in _bl)
            _has_tick = any(
                ch in body for ch in ('\u2713', '\u2714', '\uf0fb', '\uf0fc'))
            if not _has_any and not _has_tick:
                if not _has_enum:
                    # If the body is a sequence of "Label: value" paragraphs
                    # (DBE concept/relevance, advantage/explanation, etc.)
                    # and the number of labels equals the marks, award one
                    # tick per labelled paragraph — placed at the end of
                    # the line just before the next label (or end of body).
                    _label_re = re.compile(
                        r'^[A-Z][A-Za-z][A-Za-z /]{0,40}:\s+\S')
                    _label_idx = [i for i, x in enumerate(_bl)
                                  if _label_re.match(x)]
                    if len(_label_idx) >= 2 and len(_label_idx) == _marks:
                        # End-of-paragraph = line before next label, or last line.
                        for _k, _start in enumerate(_label_idx):
                            _end = (_label_idx[_k + 1] - 1
                                    if _k + 1 < len(_label_idx)
                                    else len(_bl) - 1)
                            _bl[_end] = _bl[_end].rstrip() + ' \u2713'
                    else:
                        # Single short answer. DBE memos place a tick at
                        # every awardable phrase boundary; when the
                        # importer stripped the original ticks it left
                        # behind a tell-tale DOUBLE SPACE at each old
                        # tick position. Restore ticks there first, then
                        # top up at end-of-body to reach the mark total.
                        _joined = '\n'.join(_bl)
                        # Each "  " (two spaces, not at line start) marks
                        # one stripped tick. Replace with " \u2713 ".
                        _ds_count = len(re.findall(r'(?<=\S)  (?=\S)', _joined))
                        if _ds_count and _ds_count < _marks:
                            _joined = re.sub(
                                r'(?<=\S)  (?=\S)', ' \u2713 ', _joined)
                            _remaining = _marks - _ds_count
                        elif _ds_count and _ds_count >= _marks:
                            # More double-spaces than marks — replace
                            # only the first `_marks` occurrences.
                            def _sub(_count=[0]):
                                def _r(_m):
                                    if _count[0] < _marks:
                                        _count[0] += 1
                                        return ' \u2713 '
                                    return _m.group(0)
                                return _r
                            _joined = re.sub(
                                r'(?<=\S)  (?=\S)', _sub(), _joined)
                            _remaining = 0
                        else:
                            _remaining = _marks
                        _bl = _joined.split('\n')
                        if _remaining > 0:
                            _bl[-1] = _bl[-1].rstrip() + ' ' + ('\u2713' * _remaining)
                else:
                    # Bulleted list with no (Any N) tail — append one
                    # tick to every enumerator line.
                    for _idx, _ln in enumerate(_bl):
                        if re.match(
                                r'^\s*(?:\(\d+\)|\d+[.)]|\u2022)', _ln):
                            _bl[_idx] = _ln.rstrip() + ' \u2713'
                body = '\n'.join(_bl)
        return (heading, body)

    _vmap = {
        'original':  paper.sections_original,
        'moderated': paper.sections_moderated,
        'final':     paper.sections_final,
    }
    _src = (_vmap.get(version) or '').strip() or (paper.sections or '[]')
    # Defensive: the Original (pre-moderation) and Final (post-accept)
    # views must never carry the moderator's green overlays, even if a
    # legacy snapshot accidentally captured them.
    if version in ('original', 'final'):
        _src = _strip_mod_tags(_src)
    try:
        sections = json.loads(_src or '[]')
    except Exception:
        sections = json.loads(paper.sections or '[]')
    _subj_u = (getattr(paper, 'subject', '') or '').lower()
    _ttl_u = (getattr(paper, 'title', '') or '').lower()
    _pno_u = str(getattr(paper, 'paper_number', '') or '').strip().lower()
    _is_cat = ('computer applications' in _subj_u) or ('cat' in _subj_u)
    _is_p1 = ('p1' in _ttl_u) or ('paper 1' in _ttl_u) or (_pno_u in ('1', 'p1'))
    _is_p2 = ('p2' in _ttl_u) or ('paper 2' in _ttl_u) or (_pno_u in ('2', 'p2'))
    _is_cat_p1 = _is_cat and _is_p1 and (not _is_p2)
    # Per-question totals that the bank items understate (marks live inside
    # the question body text).  Default matches the Nov CAT P1 layout; the
    # May/June 2021 paper has Q5=40 and Q6/Q7 worth 20 marks each.
    _is_cat_p1_mj2021 = _is_cat_p1 and ('2021' in _ttl_u) and (('may' in _ttl_u) or ('june' in _ttl_u))
    if _is_cat_p1_mj2021:
        _force_q_marks = {5: 40, 6: 20, 7: 20}
    elif _is_cat_p1:
        _force_q_marks = {5: 35, 6: 15, 7: 15}
    else:
        _force_q_marks = {}
    # For the Moderated view we need the per-question text from the
    # pre-moderation Original snapshot so we can render strikethrough-old
    # + green-new for any question whose bank text the moderator changed.
    _orig_qsnaps = {}
    if version == 'moderated':
        try:
            _orig_secs = json.loads(paper.sections_original or '[]')
        except Exception:
            _orig_secs = []
        for _s in (_orig_secs or []):
            if isinstance(_s, dict):
                for _qid, _snap in (_s.get('question_snapshots') or {}).items():
                    if isinstance(_snap, dict):
                        _orig_qsnaps[_qid] = _snap
    resolved = []
    grand_marks = 0
    # Track a global question number that increments per group across all sections.
    global_qn = 0
    for sec in sections:
        qs = []
        sec_snaps = sec.get('question_snapshots') or {} if isinstance(sec, dict) else {}
        for qid in sec.get('question_ids', []):
            q = QuestionBankItem.query.get(qid)
            if q:
                # Apply any embedded snapshot so the rendered version is
                # frozen against later edits to the global bank item.
                snap = sec_snaps.get(qid) if isinstance(sec_snaps, dict) else None
                if isinstance(snap, dict) and version in ('original', 'moderated', 'final'):
                    # Detach from session FIRST so our mutations can never
                    # accidentally be flushed back to the DB.
                    try:
                        db.session.expunge(q)
                    except Exception:
                        pass
                    if 'question_text' in snap:
                        q.question_text = snap.get('question_text') or ''
                    if 'answer_text' in snap:
                        q.answer_text = snap.get('answer_text') or ''
                    if 'marks' in snap:
                        try:
                            q.marks = int(snap.get('marks') or 0)
                        except Exception:
                            pass
                    if 'image_path' in snap:
                        q.image_path = snap.get('image_path') or ''
                qs.append(q); grand_marks += q.marks or 0
        # Consolidate consecutive matching items so the shared Column B options
        # block is only rendered once.
        _annotate_matching_runs(qs)
        # Moderated view: overlay strikethrough-old + green-new on every
        # question whose text differs from the pre-moderation Original
        # snapshot. New questions (in mod_qids) are already styled green
        # by the print template, so skip them here.
        if version == 'moderated' and _orig_qsnaps:
            _mod_qids_set = set(sec.get('mod_questions') or [])
            for q in qs:
                if not q or getattr(q, 'match_skip', False):
                    continue
                qid = getattr(q, 'id', None)
                if not qid or qid in _mod_qids_set:
                    continue
                old_snap = _orig_qsnaps.get(qid)
                if not isinstance(old_snap, dict):
                    continue
                old_text = old_snap.get('question_text') or ''
                new_text = getattr(q, 'display_text', None)
                if new_text is None:
                    new_text = q.question_text or ''
                if old_text and new_text and old_text != new_text:
                    # Word-level diff so only the actually-changed runs
                    # are coloured (struck-through old / green new).
                    # Unchanged runs render as plain text.
                    q.display_text = _word_diff_html(old_text, new_text)
        # Build per-section question groups based on the editor's `splits` array.
        # Each split index marks the start of a new numbered Question (5, 6, ...)
        # within the same section letter. Default = single group starting at 0.
        raw_splits = sec.get('splits') or [0]
        try:
            splits = sorted({int(s) for s in raw_splits if isinstance(s, (int, float)) and 0 <= int(s) <= len(qs)})
        except Exception:
            splits = [0]
        if not splits or splits[0] != 0:
            splits = [0] + [s for s in splits if s != 0]
        # Per-Question titles (parallel to splits) and 3-level sub-item indices.
        raw_qtitles = sec.get('qtitles') or []
        try:
            qtitles = [str(t or '') for t in raw_qtitles]
        except Exception:
            qtitles = []
        raw_qinstr = sec.get('qinstructions') or []
        try:
            qinstr = [str(t or '') for t in raw_qinstr]
        except Exception:
            qinstr = []
        raw_subitems = sec.get('subitems') or []
        try:
            split_set = set(splits)
            subitems_set = {int(s) for s in raw_subitems
                            if isinstance(s, (int, float)) and 0 <= int(s) < len(qs)
                            and int(s) not in split_set}
        except Exception:
            subitems_set = set()
        # Optional per-item post_text map ({qid: text}) — renders below
        # the item's figure (matches DBE layout for notes that appear
        # after an example image, e.g. Q6.1's NOTE bullets).
        raw_qpost = sec.get('qpost_texts') or {}
        if not isinstance(raw_qpost, dict):
            raw_qpost = {}
        qgroups = []
        for gi, start in enumerate(splits):
            end = splits[gi + 1] if gi + 1 < len(splits) else len(qs)
            global_qn += 1
            group_qs = qs[start:end]
            # Attach post_text from the section map to each ORM item so
            # the template's existing `q.post_text` block renders it.
            for _q in group_qs:
                _pt = raw_qpost.get(_q.id, '')
                try:
                    _q.post_text = _pt
                except Exception:
                    pass
            # Compute per-item printed labels (2 or 3 levels) using subitems.
            labels = []
            top_k = 0
            child_j = 0
            for offset in range(end - start):
                qi = start + offset
                is_child = (qi != start) and (qi in subitems_set)
                if is_child:
                    child_j += 1
                    labels.append('{}.{}.{}'.format(global_qn, top_k, child_j))
                else:
                    top_k += 1
                    child_j = 0
                    labels.append('{}.{}'.format(global_qn, top_k))
            grp_title = qtitles[gi] if gi < len(qtitles) else ''
            # Fallback: derive a topic title from the first non-stem
            # question's `topic` field when the section data does not
            # provide an explicit per-Question title (so the memo header
            # reads "QUESTION 7: SOCIAL IMPLICATIONS" instead of falling
            # through to the section name like "SECTION B").
            if not grp_title:
                for _gq in group_qs:
                    _topic = (getattr(_gq, 'topic', '') or '').strip()
                    _qt = (getattr(_gq, 'question_type', '') or '').lower()
                    if (_topic
                            and _topic.lower() not in ('theory', 'stem', 'practical',
                                                       'objective questions', '')
                            and _qt != 'stem' and _topic.lower() != 'stem'):
                        grp_title = _topic
                        break
            # Final fallback for CAT papers: map question number to the
            # canonical DBE topic title.
            if not grp_title:
                _subj = (getattr(paper, 'subject', '') or '').lower()
                _pno = (getattr(paper, 'paper_number', '') or '').strip()
                _ttl = (getattr(paper, 'title', '') or '').lower()
                _is_cat_p2 = ('computer applications' in _subj
                              and ('p2' in _ttl or _pno == '2'))
                _is_cat_p1 = ('computer applications' in _subj
                              and ('p1' in _ttl or _pno == '1'))
                _CAT_P2_TITLES = {
                    1: 'MULTIPLE-CHOICE QUESTIONS',
                    2: 'MATCHING ITEMS',
                    3: 'TRUE/FALSE ITEMS',
                    4: 'SYSTEMS TECHNOLOGIES',
                    5: 'INTERNET AND NETWORK TECHNOLOGIES',
                    6: 'INFORMATION MANAGEMENT',
                    7: 'SOCIAL IMPLICATIONS',
                    8: 'SOLUTION DEVELOPMENT',
                    9: 'INTEGRATED SCENARIO',
                    10: 'INTEGRATED SCENARIO',
                }
                if _is_cat_p2 and global_qn in _CAT_P2_TITLES:
                    grp_title = _CAT_P2_TITLES[global_qn]
                # CAT P1 (practical) — DBE uses application-type per Q.
                _CAT_P1_TITLES = {
                    1: 'WORD PROCESSING',
                    2: 'WORD PROCESSING',
                    3: 'SPREADSHEET',
                    4: 'SPREADSHEET',
                    5: 'DATABASE',
                    6: 'WEB DESIGN (HTML)',
                    7: 'GENERAL',
                }
                if _is_cat_p1 and global_qn in _CAT_P1_TITLES:
                    grp_title = _CAT_P1_TITLES[global_qn]
            grp_instr = qinstr[gi] if gi < len(qinstr) else ''
            # Detect TF for THIS group (so the TF intro + examples render only
            # on the TF Question, not on the section's first Question).
            grp_is_tf = _is_true_false_section(grp_title, group_qs)
            # Pre-compute memo row metadata so the template doesn't have to
            # juggle rowspans for stem?sub-item groupings. Stem rows are
            # SKIPPED in the memo (they belong only in the printed paper).
            # Each surviving row has:
            #   sub, depth, q, group_first, group_rowspan, group_total, in_group
            memo_rows = []
            # Build a parallel list of (label, q) excluding stems but keeping
            # the depth structure (a stem becomes the parent of the run that
            # immediately follows it in the editor's data model).
            # Per-label nested 2-col comparison tables, captured from
            # the marking-guide PDF at re-import time.
            _sub_tables = sec.get('subtables') or {}
            # Helper: extract the "(Any one)" / "(Any two)" tail tokens
            # from a flattened answer body so we can render them as the
            # last row of the comparison sub-table.
            def _cmp_tail(_b):
                if not _b:
                    return '(Any one)'
                _m = re.findall(r'\(Any\s+[^)]+\)', _b, re.I)
                return _m[-1] if _m else '(Any one)'
            # Extract ordered list of "(Any …)" tail tokens and any
            # "(Note(s)? to marker: …)" italic block from the body so the
            # template can render per-column tails plus a marker note.
            _NUM_WORDS = {
                'one': 1, 'two': 2, 'three': 3, 'four': 4,
                'five': 5, 'six': 6, 'seven': 7, 'eight': 8,
            }
            def _cmp_tails(_b):
                if not _b:
                    return []
                return re.findall(r'\(Any\s+[^)]+\)', _b, re.I)
            def _tail_ticks(_tail):
                _m = re.match(r'\(Any\s+(\w+)', _tail or '', re.I)
                if not _m:
                    return 1
                _w = _m.group(1).lower()
                if _w in _NUM_WORDS:
                    return _NUM_WORDS[_w]
                try:
                    return int(_w)
                except ValueError:
                    return 1
            def _cmp_notes(_b):
                if not _b:
                    return ''
                _m = re.search(
                    r'\(Notes?\s+to\s+marker[^)]*\)',
                    _b, re.I | re.S)
                return _m.group(0).strip() if _m else ''
            def _cmp_footer(_b, _cols, _marks):
                """Return [(text, colspan), ...] for the tail row of a
                comparison table. Single shared tail spans all columns
                with `marks` ticks; per-column tails get one cell each
                with ticks parsed from the (Any N …) token."""
                _cols = max(int(_cols or 1), 1)
                _tails = _cmp_tails(_b)
                _uniq = list(dict.fromkeys(_tails))
                if len(_uniq) <= 1:
                    _tail = _uniq[0] if _uniq else '(Any one)'
                    _n = max(int(_marks or _tail_ticks(_tail)), 1)
                    return [(('\u2713' * _n) + ' ' + _tail, _cols)]
                _out = []
                for _i in range(_cols):
                    _t = _tails[_i] if _i < len(_tails) else _tails[-1]
                    _n = max(_tail_ticks(_t), 1)
                    _out.append((('\u2713' * _n) + ' ' + _t, 1))
                return _out
            i = 0
            n = len(group_qs)
            while i < n:
                lbl = labels[i]
                depth = lbl.count('.') + 1
                q = group_qs[i]
                qt_lower = (getattr(q, 'question_type', '') or '').lower()
                topic_lower = (getattr(q, 'topic', '') or '').lower()
                is_stem = (qt_lower == 'stem') or (topic_lower == 'stem')
                # Treat a depth-2 row as an IMPLICIT stem when it has no
                # answer text AND the very next item is a depth-3 child
                # (e.g. 4.1 → 4.1.1, 4.1.2, …). The DBE marking guide
                # never shows such parent rows — only the children.
                if (not is_stem and depth == 2
                        and i + 1 < n
                        and (labels[i + 1].count('.') + 1) == 3
                        and not (getattr(q, 'answer_text', '') or '').strip()):
                    is_stem = True
                if is_stem:
                    # Skip the stem row entirely. The sub-items that follow
                    # are still in the labels list with depth-3 numbering and
                    # will be picked up by the chain handler below.
                    i += 1
                    continue
                if depth == 3:
                    # Open a chain of consecutive depth-3 rows.
                    chain_start = i
                    chain_end = i
                    while chain_end + 1 < n and (labels[chain_end + 1].count('.') + 1) == 3:
                        # Skip stems hidden inside the chain (defensive).
                        nxt_q = group_qs[chain_end + 1]
                        nxt_is_stem = ((getattr(nxt_q, 'question_type', '') or '').lower() == 'stem'
                                       or (getattr(nxt_q, 'topic', '') or '').lower() == 'stem')
                        if nxt_is_stem:
                            break
                        chain_end += 1
                    chain_total = sum((group_qs[t].marks or 0) for t in range(chain_start, chain_end + 1))
                    chain_len = chain_end - chain_start + 1
                    for t in range(chain_start, chain_end + 1):
                        _h, _b = _clean_memo_answer(group_qs[t])
                        _ct = _sub_tables.get(labels[t])
                        _ccols = len(_ct[0]) if (_ct and _ct[0]) else 2
                        memo_rows.append({
                            'sub': labels[t], 'depth': 3, 'q': group_qs[t],
                            'clean_heading': _h, 'clean_body': _b,
                            'cmp_table': _ct,
                            'cmp_tail': _cmp_tail(_b),
                            'cmp_tails': _cmp_tails(_b),
                            'cmp_notes': _cmp_notes(_b),
                            'cmp_marks': (group_qs[t].marks or 0),
                            'cmp_footer': _cmp_footer(_b, _ccols, group_qs[t].marks or 0),
                            'group_first': (t == chain_start),
                            'group_rowspan': chain_len if t == chain_start else 0,
                            'group_total': chain_total if t == chain_start else 0,
                            'in_group': True,
                        })
                    i = chain_end + 1
                    continue
                # Plain depth-2 row.
                _h, _b = _clean_memo_answer(q)
                _ct = _sub_tables.get(lbl)
                _ccols = len(_ct[0]) if (_ct and _ct[0]) else 2
                memo_rows.append({
                    'sub': lbl, 'depth': depth, 'q': q,
                    'clean_heading': _h, 'clean_body': _b,
                    'cmp_table': _ct,
                    'cmp_tail': _cmp_tail(_b),
                    'cmp_tails': _cmp_tails(_b),
                    'cmp_notes': _cmp_notes(_b),
                    'cmp_marks': (q.marks or 0),
                    'cmp_footer': _cmp_footer(_b, _ccols, q.marks or 0),
                    'group_first': False, 'group_rowspan': 0, 'group_total': 0,
                    'in_group': False,
                })
                i += 1
            grp_has_groups = any(r['in_group'] for r in memo_rows)
            _mod_qtitles = sec.get('mod_qtitles') or []
            _mod_qinstr  = sec.get('mod_qinstr') or []
            _mod_old_qt  = sec.get('mod_old_qtitles') or []
            _mod_old_qi  = sec.get('mod_old_qinstr') or []
            _mod_qids    = set(sec.get('mod_questions') or [])
            # Optional per-group hero image (e.g. Question 9 scenario robot)
            _qimages = sec.get('qimages') or []
            _grp_intro_image = _qimages[gi] if gi < len(_qimages) else ''
            # Optional per-group "(Note to marker: ...)" override that
            # appears INSIDE the True/False memo card (HTML allowed,
            # e.g. <u>...</u> for underlined emphasis).
            _qmemo_notes = sec.get('qmemo_notes') or []
            _grp_tf_memo_note = _qmemo_notes[gi] if gi < len(_qmemo_notes) else ''
            # Optional per-group outro (rendered after the last sub-item,
            # before the [N] total badge). Used for DBE closers like
            # "Save and close the 1eSports document."
            _qoutros = sec.get('qoutros') or []
            _grp_outro = _qoutros[gi] if gi < len(_qoutros) else ''
            qgroups.append({
                'qn': global_qn,
                'questions': group_qs,
                'marks': sum(q.marks or 0 for q in group_qs),
                'labels': labels,
                'title': grp_title,
                'instructions': grp_instr,
                'intro_image': _grp_intro_image,
                'tf_memo_note': _grp_tf_memo_note,
                'is_tf': grp_is_tf,
                'memo_rows': memo_rows,
                'has_groups': grp_has_groups,
                'mod_title': bool(_mod_qtitles[gi]) if gi < len(_mod_qtitles) else False,
                'mod_instr': bool(_mod_qinstr[gi]) if gi < len(_mod_qinstr) else False,
                'mod_old_title': _mod_old_qt[gi] if gi < len(_mod_old_qt) else '',
                'mod_old_instr': _mod_old_qi[gi] if gi < len(_mod_old_qi) else '',
                'mod_qids': _mod_qids,
                # Optional per-section overrides for the TF EXAMPLES
                # table + NO-mark notice (DBE varies these year-to-year).
                'tf_examples': sec.get('tf_examples') or None,
                'tf_no_mark':  sec.get('tf_no_mark')  or None,
                # Matching-memo column order: some DBE MGs place the ✓ AFTER
                # the matched term ("F  Hardcopy  ✓  1") instead of before it
                # ("C  ✓  Broadband  1"). Default False = tick before term.
                'match_tick_after_term': bool(sec.get('match_tick_after_term')),
                'outro': _grp_outro,
            })
            # If a group has exactly one parsed question whose body holds an
            # entire imported Question (lead title + intro + 1.1, 1.2, ...
            # sub-items), expand it into per-sub-item rows so each gets its
            # own number column and far-right marks like the original DBE PDF.
            if len(group_qs) == 1:
                only_q = group_qs[0]
                parsed = _split_question_subitems(
                    getattr(only_q, 'display_text', None) or (only_q.question_text or ''),
                    global_qn,
                )
                if parsed and parsed['items']:
                    grp = qgroups[-1]
                    grp['parsed_subitems'] = parsed
                    # Override labels for printing.
                    grp['labels'] = [it['label'] for it in parsed['items']]
                    # Keep the cover-authoritative marks total (sum of parsed
                    # sub-item marks may be partial when the PDF wraps oddly).
                    # Promote the extracted lead title into the group title
                    # if the group had none (so the QUESTION head shows
                    # "QUESTION 1: WORD PROCESSING" like the original).
                    if not grp.get('title') and parsed.get('lead_title'):
                        grp['title'] = parsed['lead_title']
                    # The intro text (everything before the first 1.1) becomes
                    # the per-Question instructions block under the head.
                    if parsed.get('intro') and not grp.get('instructions'):
                        grp['instructions'] = parsed['intro']
                    if parsed.get('outro'):
                        grp['outro'] = parsed['outro']
                    # Replace the single question with a list of pseudo-Qs
                    # (SimpleNamespace) so the existing template loop just
                    # works.
                    # Load JSON answer map (label -> answer) if the
                    # importer stored one in the bank item's answer_text.
                    _ans_map = {}
                    # Infer per-Question card type so the memo renders
                    # MCQ / Matching / TF as compact cards (matching the
                    # DBE marking-guidelines layout).
                    _ttl_u = (grp.get('title') or '').upper()
                    _intro_u = (parsed.get('intro') or '').upper()
                    _ctx_u = _ttl_u + ' ' + _intro_u
                    if ('TRUE' in _ctx_u and 'FALSE' in _ctx_u
                            and 'ITEM' in _ctx_u):
                        _pseudo_qt = 'true_false'
                    elif 'MATCH' in _ctx_u or 'COLUMN A' in _ctx_u:
                        _pseudo_qt = 'matching'
                    elif ('MULTIPLE' in _ctx_u and 'CHOICE' in _ctx_u) \
                            or 'MULTIPLE-CHOICE' in _ctx_u:
                        _pseudo_qt = 'mcq'
                    else:
                        _pseudo_qt = 'structured'
                    pseudo = []
                    for it in parsed['items']:
                        _ans_text = _ans_map.get(it['label'], '')
                        # Matching answers from the MG PDF look like
                        # "P  ADSL" (letter + 2 spaces + term). The
                        # memo-card template expects "P) ADSL" so it can
                        # split the letter from the term — reshape here.
                        if _pseudo_qt == 'matching' and _ans_text:
                            _m_mt = re.match(r'^\s*([A-Z])\s{2,}(.+)$',
                                             _ans_text)
                            if _m_mt:
                                _ans_text = (_m_mt.group(1) + ') '
                                              + _m_mt.group(2).strip())
                        ns = types.SimpleNamespace(
                            id=only_q.id,
                            question_text=it['text'],
                            display_text=it['text'],
                            answer_text=_ans_text,
                            marks=int(it.get('marks') or 0),
                            image_path=None,
                            question_type=_pseudo_qt,
                            post_text=it.get('post_text', ''),
                        )
                        pseudo.append(ns)
                    # Promote TF context so the memo template treats the
                    # group as a true/false card (with the "Note to
                    # marker:" intro rendered inside the card).
                    if _pseudo_qt == 'true_false':
                        grp['is_tf'] = True
                    grp['questions'] = pseudo
                    # Recompute the per-Question total. Prefer the bank
                    # item's stored marks (it already accounts for
                    # matching/MCQ multipliers and any marks the parser
                    # misses). Only when the bank item stores 0 do we
                    # fall back to the sum of parsed "(N)" sub-items, so
                    # the [N] footer matches the editor's left list.
                    _sub_total = sum(int(it.get('marks') or 0) for it in parsed['items'])
                    _stored_total = int(getattr(only_q, 'marks', 0) or 0)
                    if _stored_total > 0:
                        grp['marks'] = _stored_total
                    elif _sub_total > 0:
                        grp['marks'] = _sub_total
                    # Rebuild memo_rows from the per-sub-item pseudo list
                    # so the marking-guideline view shows one row per
                    # sub-item (1.1, 1.1.1, 1.2, ...) instead of one huge
                    # cell containing the whole Question text. Depth-3
                    # rows are coalesced into a single chain with shared
                    # group_total just like the original memo builder.
                    _new_mr = []
                    _ii = 0
                    _nn = len(pseudo)
                    while _ii < _nn:
                        _lbl = grp['labels'][_ii] if _ii < len(grp['labels']) else ''
                        _depth = _lbl.count('.') + 1 if _lbl else 2
                        if _depth >= 3:
                            _cs = _ii
                            _ce = _ii
                            while _ce + 1 < _nn:
                                _nl = grp['labels'][_ce + 1] if (_ce + 1) < len(grp['labels']) else ''
                                if (_nl.count('.') + 1 if _nl else 2) != _depth:
                                    break
                                _ce += 1
                            _ct = sum((pseudo[_t].marks or 0)
                                      for _t in range(_cs, _ce + 1))
                            _cl = _ce - _cs + 1
                            for _t in range(_cs, _ce + 1):
                                _new_mr.append({
                                    'sub': grp['labels'][_t],
                                    'depth': _depth,
                                    'q': pseudo[_t],
                                    'clean_heading': '',
                                    'clean_body': (pseudo[_t].answer_text or '').strip(),
                                    'group_first': (_t == _cs),
                                    'group_rowspan': _cl if _t == _cs else 0,
                                    'group_total': _ct if _t == _cs else 0,
                                    'in_group': True,
                                })
                            _ii = _ce + 1
                            continue
                        _new_mr.append({
                            'sub': _lbl,
                            'depth': _depth,
                            'q': pseudo[_ii],
                            'clean_heading': '',
                            'clean_body': (pseudo[_ii].answer_text or '').strip(),
                            'group_first': False,
                            'group_rowspan': 0,
                            'group_total': 0,
                            'in_group': False,
                        })
                        _ii += 1
                    grp['memo_rows'] = _new_mr
                    grp['has_groups'] = any(r['in_group'] for r in _new_mr)
                    # Auto-attach figure images to sub-items.
                    #
                    # Folder layout (all under static/):
                    #   uploads/paper_images/<paper_id>/<question_id>/<key>.<ext>
                    #       Per-QUESTION folder. <key> is the sub-item's
                    #       LOCAL label (the part after the leading
                    #       Question number, dots preserved).
                    #       e.g. for Q5 sub-item 5.13 the file is
                    #       "13.PNG"; for Q1 sub-item 1.1.1 the file is
                    #       "1.1.PNG".
                    #       Because the key is local and the folder is
                    #       keyed by question_id (which never changes),
                    #       these figures follow the question when the
                    #       teacher rearranges the paper.
                    #
                    #   uploads/paper_images/<paper_id>/<key>.<ext>
                    #       Legacy fallback: <key> is the GLOBAL compact
                    #       label (e.g. "45" for 4.5). Only matched when
                    #       the per-question folder didn't supply a file
                    #       for that sub-item.
                    try:
                        _paper_id = getattr(paper, 'id', '') or ''
                        _qid = getattr(only_q, 'id', '') or ''
                        # Build label->ns lookup for this question.
                        _by_compact = {}   # global compact key  -> ns
                        _by_local   = {}   # local key (with dots, no leading qn) -> ns
                        for ns, it in zip(pseudo, parsed['items']):
                            _gkey = it['label'].replace('.', '')
                            _by_compact.setdefault(_gkey, ns)
                            # Local key = label MINUS the leading
                            # Question-number segment, dots preserved.
                            # "5.13" -> "13"; "1.1.1" -> "1.1"; "5.1" -> "1".
                            _parts = it['label'].split('.', 1)
                            if len(_parts) == 2:
                                _by_local.setdefault(_parts[1], ns)
                        # 1) Per-question folder (preferred — survives
                        #    rearrange). Filename starts with the local
                        #    key, dots preserved: "13.PNG", "1.1.PNG".
                        if _paper_id and _qid:
                            _q_dir = os.path.join('static', 'uploads',
                                                  'paper_images', _paper_id, _qid)
                            if os.path.isdir(_q_dir):
                                _q_url = ('uploads/paper_images/' + _paper_id
                                          + '/' + _qid + '/')
                                for fn in os.listdir(_q_dir):
                                    m = re.match(r'^(\d+(?:\.\d+)*)', fn)
                                    if not m:
                                        continue
                                    key = m.group(1)
                                    if key in _by_local and not _by_local[key].image_path:
                                        _by_local[key].image_path = _q_url + fn
                        # 2) Legacy per-paper folder (global compact key).
                        if _paper_id:
                            _p_dir = os.path.join('static', 'uploads',
                                                  'paper_images', _paper_id)
                            if os.path.isdir(_p_dir):
                                _p_url = 'uploads/paper_images/' + _paper_id + '/'
                                for fn in os.listdir(_p_dir):
                                    full = os.path.join(_p_dir, fn)
                                    if os.path.isdir(full):
                                        continue
                                    m = re.match(r'^(\d{2,4})', fn)
                                    if not m:
                                        continue
                                    key = m.group(1)
                                    if key in _by_compact and not _by_compact[key].image_path:
                                        _by_compact[key].image_path = _p_url + fn
                    except Exception:
                        pass
                    # When a sub-item has an attached figure, peel any
                    # trailing "Save and close ..." closer line off the
                    # body text and move it into post_text so it renders
                    # BELOW the image (matching the original DBE layout).
                    try:
                        _closer_re = re.compile(
                            r'\n[ \t]*((?:save\s+and\s+close|close\s+the|save\s+the)\b[^\n]*)\s*$',
                            re.IGNORECASE,
                        )
                        for ns in pseudo:
                            if not ns.image_path:
                                continue
                            m = _closer_re.search(ns.display_text or '')
                            if not m:
                                continue
                            closer = m.group(1).strip()
                            closer = re.sub(r'\s*\(\s*\d+\s*\)\s*$', '', closer).rstrip()
                            ns.display_text = (ns.display_text[:m.start()]).rstrip()
                            ns.question_text = ns.display_text
                            ns.post_text = (closer + ('\n' + ns.post_text if ns.post_text else '')).strip()
                    except Exception:
                        pass
                    # If the group's outro starts with a "Save and close ..."
                    # closer line and the LAST item carries an image, peel
                    # that closer off the outro and into the item's
                    # post_text so it renders directly under the figure
                    # (matches the original DBE layout where the closer
                    # appears between the image and the per-Question
                    # [N] total badge).
                    try:
                        outro_text = grp.get('outro', '') or ''
                        if outro_text and pseudo and pseudo[-1].image_path:
                            _lead_closer_re = re.compile(
                                r'^\s*((?:save\s+and\s+close|close\s+the|save\s+the)\b[^\n]*)(?:\n|$)',
                                re.IGNORECASE,
                            )
                            m = _lead_closer_re.match(outro_text)
                            if m:
                                closer = re.sub(r'\s*\(\s*\d+\s*\)\s*$', '', m.group(1).strip()).rstrip()
                                grp['outro'] = outro_text[m.end():].lstrip('\n')
                                last_ns = pseudo[-1]
                                last_ns.post_text = (closer + ('\n' + last_ns.post_text if last_ns.post_text else '')).strip()
                    except Exception:
                        pass
        # Paginate large groups across multiple page cards. A standard A4
        # DBE page comfortably holds ~14 sub-items when packed tightly;
        # spill the rest into continuation groups (same qn, marked
        # `continued=True`) so the template emits a fresh `.page` div with
        # "QUESTION N (continued)" only when there's genuinely too much
        # content for one sheet.
        _PER_PAGE = 14
        # Manual page-break overrides set by the user via the preview
        # editor: any item whose qid is in this set MUST start a new
        # continuation page, regardless of the height estimate.
        _forced_break_qids = set(sec.get('forced_breaks') or []) if isinstance(sec, dict) else set()
        # Inverse override: items the user has explicitly pinned to the
        # PREVIOUS page (clicked ↑). The auto-paginator is forbidden
        # from inserting a break before these items, even when the
        # height budget would have triggered one.
        _no_break_qids = set(sec.get('no_breaks') or []) if isinstance(sec, dict) else set()
        # Forced page-breaks: split a qgroup so the listed label starts a
        # fresh continuation page even when the count is below _PER_PAGE.
        # Disabled -- the prior layout tweaks created large pockets of
        # blank space because they forced extra page breaks even when the
        # content fit comfortably on a single sheet.
        _FORCE_BREAK_BEFORE = set()
        _split_groups = []
        for grp in qgroups:
            labels_list = grp.get('labels') or []
            qs_list = grp.get('questions') or []
            break_idxs = [i for i, lbl in enumerate(labels_list)
                          if i > 0 and lbl in _FORCE_BREAK_BEFORE]
            if not break_idxs:
                _split_groups.append(grp)
                continue
            outro = grp.pop('outro', '')
            total_marks = grp.get('marks', 0)
            bounds = [0] + break_idxs + [len(labels_list)]
            chunks = list(zip(bounds[:-1], bounds[1:]))
            # Peel a trailing NOTE: block off the LAST item before each
            # forced break, so it becomes the continuation page's intro
            # instructions instead of dangling at the bottom of the prior
            # page (matches the original DBE layout where the NOTE
            # references "the previous page").
            _note_re = re.compile(r'\n[ \t]*(NOTE:[\s\S]*)$', re.IGNORECASE)
            peeled_notes = {}  # chunk_index -> note text to prepend to that chunk's instructions
            for bi, idx in enumerate(break_idxs):
                last_q = qs_list[idx - 1]
                body = getattr(last_q, 'display_text', '') or ''
                m = _note_re.search(body)
                if not m:
                    continue
                note_block = m.group(1).strip()
                trimmed = body[:m.start()].rstrip()
                last_q.display_text = trimmed
                last_q.question_text = trimmed
                peeled_notes[bi + 1] = note_block
            for ci, (a, b) in enumerate(chunks):
                is_first = (ci == 0)
                is_last = (ci == len(chunks) - 1)
                sub = dict(grp)
                sub['questions'] = qs_list[a:b]
                sub['labels'] = labels_list[a:b]
                sub['continued'] = (not is_first) or grp.get('continued', False)
                if not is_first:
                    sub['instructions'] = peeled_notes.get(ci, '')
                sub['marks'] = total_marks if is_last else 0
                sub['outro'] = outro if is_last else ''
                sub['suppress_total'] = (not is_last)
                _split_groups.append(sub)
        qgroups = _split_groups
        # Height-aware chunker: estimate the rendered px height of each
        # item (text lines + figure bonus + per-item gap) and split a
        # qgroup whenever the cumulative height would exceed the A4 page
        # budget. This prevents printed papers from spilling 1-2 trailing
        # lines onto an otherwise blank physical page.
        # A4 portrait is ~1123px at 96 DPI; subtract page padding (~155px
        # top+bottom), running header/footer (~60px) and the q-head /
        # q-intro overhead so the budget is what's available for items.
        _PAGE_BUDGET_PX = 880
        # Manual page-breaks set by the user are ADDITIONAL forced split
        # points layered on top of the auto-paginator. We must NOT disable
        # the budget — otherwise a single `.page` div grows taller than
        # A4 and the browser silently splits it when printing, so the
        # PDF no longer matches what the preview shows.
        def _est_item_h(q):
            txt = (getattr(q, 'display_text', None)
                   or getattr(q, 'question_text', '') or '')
            post = getattr(q, 'post_text', '') or ''
            # Each ~80-char visual line = ~20px (1.5 line-height @ 13.5px).
            line_units = 1
            for ln in (txt + '\n' + post).split('\n'):
                line_units += max(1, (len(ln) + 79) // 80)
            h = line_units * 20 + 8  # base lines + item padding
            if getattr(q, 'image_path', None):
                # Conservative average figure: ~250px tall. Tall DBE
                # figures (full-width screenshots, tables) can exceed
                # this; we leave a safety margin in the budget.
                h += 260
            return h
        _expanded = []
        for grp in qgroups:
            qs_list = grp.get('questions') or []
            labels_list = grp.get('labels') or []
            _first_qtype = ''
            if qs_list:
                _first_qtype = (getattr(qs_list[0], 'question_type', '') or '').lower()
            if _first_qtype in ('matching', 'match_columns'):
                _expanded.append(grp)
                continue
            # Walk items, accumulating estimated height; break when the
            # next item would overflow the budget.
            outro = grp.pop('outro', '')
            total_marks = grp.get('marks', 0)
            chunks = []
            cur_start = 0
            cur_h = 120  # q-head + q-intro overhead
            for i, q in enumerate(qs_list):
                ih = _est_item_h(q)
                _qid = getattr(q, 'id', None)
                _force = (i > cur_start) and (_qid in _forced_break_qids)
                _pin   = (_qid in _no_break_qids)
                # Never break inside a matching run: its rows render as ONE
                # table on the run-first item, so splitting rows into a later
                # chunk would drop them from the rendered table.
                _in_match_run = getattr(q, 'match_skip', False)
                # Always keep at least one item per chunk.
                if (i > cur_start and not _in_match_run
                        and (_force or ((not _pin) and (cur_h + ih) > _PAGE_BUDGET_PX))):
                    chunks.append((cur_start, i))
                    cur_start = i
                    cur_h = 40  # continuation pages skip the intro
                cur_h += ih
            chunks.append((cur_start, len(qs_list)))
            if len(chunks) == 1:
                grp['outro'] = outro
                _expanded.append(grp)
                continue
            for ci, (a, b) in enumerate(chunks):
                is_first = (ci == 0)
                is_last  = (ci == len(chunks) - 1)
                sub = dict(grp)
                sub['questions'] = qs_list[a:b]
                sub['labels'] = labels_list[a:b]
                sub['continued'] = (not is_first)
                if not is_first:
                    sub['instructions'] = ''
                sub['marks'] = total_marks if is_last else 0
                sub['outro'] = outro if is_last else ''
                sub['suppress_total'] = (not is_last)
                _expanded.append(sub)
        qgroups = _expanded
        # Per-section question-total overrides stored in the section JSON
        # (e.g. Business Studies Q1 prints [30] while its objective items
        # carry no individual marks). Merged over the CAT-specific defaults.
        _sec_qmarks = sec.get('qmarks') or {}
        if isinstance(_sec_qmarks, dict):
            for _k, _v in _sec_qmarks.items():
                try:
                    _force_q_marks = dict(_force_q_marks)
                    _force_q_marks[int(_k)] = int(_v)
                except (TypeError, ValueError):
                    pass
        if _force_q_marks:
            for _g in qgroups:
                # Skip continued (non-last) pagination chunks — their marks were
                # deliberately zeroed (the question total belongs on the LAST
                # chunk only). Re-forcing them here would double-count the
                # question in the section/grand totals.
                if _g.get('suppress_total'):
                    continue
                try:
                    _qn = int(_g.get('qn') or 0)
                except Exception:
                    _qn = 0
                if _qn in _force_q_marks:
                    _g['marks'] = _force_q_marks[_qn]
        is_tf = _is_true_false_section(sec.get('title', ''), qs)
        # Auto-splitting MCQ/Matching into separate Questions is disabled — the
        # editor's `splits` array is now the single source of truth for
        # question numbering, so the editor and the printed paper agree.
        resolved.append({'title': sec.get('title', 'Section'),
                         'sub_title': '',
                         'instructions': sec.get('instructions', ''),
                         'memo_intro': sec.get('memo_intro', ''),
                         'memo_breakdown': sec.get('memo_breakdown'),
                         'memo_front_pages': sec.get('memo_front_pages'),
                         'scenario': sec.get('scenario', ''),
                         'scenarios': sec.get('scenarios') or {},
                         'questions': qs,
                         'qgroups': qgroups,
                         # Sum from qgroups (which already account for
                         # parsed sub-item "(N)" marks when the bank
                         # item itself stores 0). Falling back to raw
                         # q.marks understates papers whose marks live
                         # inside the question body.
                         # `counted_marks` overrides the physical sum for
                         # choice sections (e.g. Business Studies "answer
                         # any TWO of the three questions": 3x40 printed
                         # but only 80 counted).
                         'marks': (int(sec.get('counted_marks'))
                                   if sec.get('counted_marks')
                                   else sum(int(g.get('marks') or 0) for g in qgroups)),
                         'is_tf': is_tf,
                         'is_split_child': False,
                         'mod_title': bool(sec.get('mod_title')),
                         'mod_instr': bool(sec.get('mod_instr')),
                         'mod_old_title': sec.get('mod_old_title') or '',
                         'mod_old_instr': sec.get('mod_old_instr') or '',
                         'mod_qids': set(sec.get('mod_questions') or [])})
    # Header overrides drive the strikethrough-old + green-new pair on the
    # cover/header. They only make sense for the "moderated" diff view.
    # For "original" we build a lightweight read-only view of the paper
    # whose header fields reflect the pre-moderation snapshot — so the
    # cover/header shows what the teacher actually sent for review,
    # without mutating the live DB row. For "final" we keep the live
    # header (which already carries the accepted values) and pass no
    # overrides. For "moderated" we expose the diff map.
    paper_view = _paper_render_copy(paper, sanitize_cover_note=True)
    if version == 'original':
        try:
            _orig_hdr = json.loads(paper.header_original or '{}')
        except Exception:
            _orig_hdr = {}
        if isinstance(_orig_hdr, dict) and _orig_hdr:
            from datetime import date as _date
            paper_view = _paper_render_copy(paper, sanitize_cover_note=True)
            # Then overlay the snapshotted header values.
            for _f, _v in _orig_hdr.items():
                if _f not in _PAPER_HEADER_FIELDS:
                    continue
                try:
                    if _f == 'exam_date':
                        if isinstance(_v, str) and _v:
                            setattr(paper_view, _f, _date.fromisoformat(_v[:10]))
                        elif not _v:
                            setattr(paper_view, _f, None)
                    elif _f in ('duration_minutes', 'total_marks', 'grade'):
                        setattr(paper_view, _f, int(_v or 0))
                    else:
                        setattr(paper_view, _f, _v if _v is not None else '')
                except Exception:
                    pass
        _ov = {}
    elif version == 'moderated':
        _ov = _safe_loads_dict(paper.moderator_overrides)
        # Fallback: if the moderated paper's displayed MARKS value changed
        # but the stored override map missed `total_marks`, synthesize it so
        # the print view can still render old (struck) + new (green).
        if 'total_marks' not in _ov:
            try:
                _orig_hdr = json.loads(paper.header_original or '{}')
            except Exception:
                _orig_hdr = {}
            _old_marks = _orig_hdr.get('total_marks') if isinstance(_orig_hdr, dict) else None
            _new_marks = paper.total_marks if paper.total_marks not in (None, '') else grand_marks
            try:
                _old_marks_i = int(_old_marks) if _old_marks not in (None, '') else None
            except Exception:
                _old_marks_i = None
            try:
                _new_marks_i = int(_new_marks) if _new_marks not in (None, '') else None
            except Exception:
                _new_marks_i = None
            if (_old_marks_i is not None and _new_marks_i is not None
                    and _old_marks_i != _new_marks_i):
                _ov['total_marks'] = {
                    'old': str(_old_marks_i),
                    'new': str(_new_marks_i),
                    'old_raw': _old_marks_i,
                    'new_raw': _new_marks_i,
                }
    elif version == 'final':
        _ov = {}
    else:
        _ov = _safe_loads_dict(paper.moderator_overrides)

    # Appendix sheets are part of the candidate paper package, not the
    # marker memo printout.
    appendices = []
    if not with_memo:
        # Detect & peel HTML TAG SHEET / INPUT MASK CHARACTER SHEET appendices
        # out of the trailing group's outro (captured as raw PDF text on
        # import). Render them as their own structured pages.
        appendices = _extract_appendices(resolved)
        # Force-include reference appendices for CAT P1 Nov 2025 papers,
        # whose outro markers were removed during text cleanup.
        try:
            _ptitle = (getattr(paper, 'title', '') or '')
        except Exception:
            _ptitle = ''
        if not appendices and ('Nov 2025' in _ptitle or 'November 2025' in _ptitle) and ('P1' in _ptitle):
            appendices = [_APPENDIX_HTML_TAG_SHEET, _APPENDIX_INPUT_MASK]
        # CAT P1 Nov 2022 likewise carries the HTML tag sheet + input-mask
        # character sheet annexures, but their cover does not reference them
        # by name, so trigger on the paper title directly.
        if not appendices and ('Nov 2022' in _ptitle or 'November 2022' in _ptitle) and ('P1' in _ptitle):
            appendices = [_APPENDIX_HTML_TAG_SHEET, _APPENDIX_INPUT_MASK]
        if not appendices:
            try:
                _pno = str(getattr(paper, 'paper_number', '') or '').strip().upper()
            except Exception:
                _pno = ''
            _instr = (
                (getattr(paper, 'instructions', '') or '')
                + '\n' + _ptitle
                + '\n' + (getattr(paper, 'cover_extra_note', '') or '')
            ).upper()
            _mentions_annexure_sheet = (
                'HTML TAG SHEET' in _instr
                or 'INPUT MASK CHARACTER SHEET' in _instr
                or 'ANNEXURE A' in _instr
                or 'ANNEXURE B' in _instr
            )
            # Many imported CAT P1 papers lose trailing appendix marker text
            # during cleanup; if cover instructions reference annexure sheets,
            # include both structured appendix pages at the end.
            if (_pno in ('1', 'P1')) and _mentions_annexure_sheet:
                appendices = [_APPENDIX_HTML_TAG_SHEET, _APPENDIX_INPUT_MASK]
        # Substitute the year-specific HTML TAG SHEET variant where the
        # default expanded sheet does not match the source paper (e.g. the
        # reduced CAT P1 May/June 2021 sheet).
        if appendices:
            _tag_variant = _select_html_tag_sheet(paper)
            if _tag_variant is not None:
                appendices = [
                    (_tag_variant if a is _APPENDIX_HTML_TAG_SHEET else a)
                    for a in appendices
                ]
        # Append the candidate INFORMATION SHEET as the very last page. Some
        # covers describe it as a "separate information sheet", so it remains
        # part of the downloaded package but is excluded from the stated
        # question-paper page count.
        info_app = _build_info_sheet_appendix(paper, resolved)
        if info_app is not None:
            appendices.append(info_app)

    # Re-derive grand_marks from the resolved section totals so it matches
    # the printed [N] footers (the per-question loop only saw raw q.marks
    # which is 0 for items whose marks live inside "(N)" sub-item markers).
    try:
        grand_marks = sum(int(s.get('marks') or 0) for s in resolved)
    except Exception:
        pass
    # Keep the printed main total dynamic from the live section totals. Only
    # fall back to stored total_marks when the computed sum is missing/zero.
    try:
        if (not grand_marks or int(grand_marks) <= 0) and getattr(paper, 'total_marks', 0) and int(paper.total_marks) > 0:
            grand_marks = int(paper.total_marks)
    except Exception:
        pass

    # Union of forced page-break qids across all sections (for the
    # preview-edit UI to seed each toggle's state).
    _forced_breaks_all = set()
    _no_breaks_all = set()
    try:
        for _s in (paper.sections and json.loads(paper.sections) or []):
            if isinstance(_s, dict):
                for _q in (_s.get('forced_breaks') or []):
                    if _q:
                        _forced_breaks_all.add(_q)
                for _q in (_s.get('no_breaks') or []):
                    if _q:
                        _no_breaks_all.add(_q)
    except Exception:
        pass

    return {'paper': paper_view, 'sections': resolved, 'with_memo': with_memo,
            'grand_marks': grand_marks,
            'appendices': appendices,
            'forced_breaks': _forced_breaks_all,
            'no_breaks': _no_breaks_all,
            'preview_overrides': _load_preview_overrides(paper),
            'mod_overrides': _ov}


def _load_preview_overrides(paper):
    """Return the paper's WYSIWYG override map as a plain dict."""
    raw = (paper.preview_overrides or '').strip()
    if not raw:
        return {}
    try:
        v = json.loads(raw)
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}

_TF_DETECT_RE = re.compile(r'\(indicate\s+true\s+or\s+false', re.IGNORECASE)

def _is_true_false_section(sec_title, questions):
    """Return True if this section is a True/False section."""
    title_lower = (sec_title or '').lower()
    if 'true' in title_lower and 'false' in title_lower:
        return True
    tf_like = 0
    answered = 0
    for q in questions:
        if (getattr(q, 'question_type', '') or '') == 'true_false':
            return True
        if _TF_DETECT_RE.search(getattr(q, 'question_text', '') or ''):
            return True
        # Answer-pattern detection: many imported TF items are stored as
        # 'short_answer' with answers like "True", "True \u2713" or
        # "False, motherboard \u2713". Strip tick/cross marks and inspect the
        # leading token.
        ans_clean = re.sub(r'[\u2713\u2717\u2714\u2718]', '', getattr(q, 'answer_text', '') or '').strip().upper()
        if ans_clean:
            answered += 1
            if ans_clean in ('T', 'F') or ans_clean.startswith('TRUE') or ans_clean.startswith('FALSE'):
                tf_like += 1
    # Treat the group as True/False when most of its answered questions look
    # like True/False answers (and there are at least two such items).
    if answered >= 2 and tf_like >= 2 and tf_like * 2 >= answered:
        return True
    return False





_MATCH_INTRO_RE = re.compile(
    r"^\s*Match the following description with the correct term from the list:\s*",
    re.IGNORECASE,
)


def _is_matching_item(q):
    if (q.question_type or '').lower() == 'match_columns':
        return True
    text = (q.question_text or '').lstrip()
    return bool(_MATCH_INTRO_RE.match(text))
def _annotate_matching_runs(qs):
    """Attach a structured matching-table payload to each run of matching items.

    For each maximal run of consecutive matching items, the FIRST item in the
    run gets ``match_table = {'rows': [(label, description, marks), ...],
    'options': [(letter, term), ...], 'total_marks': N, 'count': N}`` and is
    flagged ``match_run_first = True``. All subsequent items in that run get
    ``match_skip = True`` so the template renders the table only once.
    Non-matching items just get ``display_text = question_text``.
    """
    # Numbering of matching runs follows the surrounding question numbering,
    # which the template controls. Here we only record per-row labels relative
    # to the run (1, 2, ... N); the template will compose the final "Q.subN".
    i = 0
    while i < len(qs):
        q = qs[i]
        if not _is_matching_item(q):
            try:
                q.display_text = q.question_text
                q.match_skip = False
                q.match_run_first = False
            except Exception:
                pass
            i += 1
            continue
        # Collect the run
        run_start = i
        rows = []           # list of (description, marks)
        options = []        # list of (letter, term)
        ans_list = []       # each row's raw answer_text (for COLUMN B fallback)
        run_ids = []        # qids of every row in the run, in order
        while i < len(qs) and _is_matching_item(qs[i]):
            text = qs[i].question_text or ''
            body = text
            opts_tail = ''
            if 'Options:' in text:
                body, _, opts_tail = text.partition('Options:')
            description = _MATCH_INTRO_RE.sub('', body).strip()
            rows.append((description, qs[i].marks or 0))
            ans_list.append(qs[i].answer_text or '')
            run_ids.append(getattr(qs[i], 'id', None))
            if not options and opts_tail:
                # Parse "A) WiMAX\nB) Information overload\n..." from the FIRST
                # item in the run that carries an Options block. (Usually that
                # is run_start, but if run_start was swapped to a matching
                # sub-item that lacks options, fall back to a later item so the
                # shared COLUMN B does not vanish.)
                for line in opts_tail.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    m = re.match(r'^([A-Z])[\)\.\:\-]\s*(.+)$', line)
                    if m:
                        options.append((m.group(1), m.group(2).strip()))
            try:
                qs[i].display_text = description
                qs[i].match_skip = (i != run_start)
                qs[i].match_run_first = (i == run_start)
            except Exception:
                pass
            i += 1
        # ---- COLUMN B resolution + per-row keys -------------------------
        # A matching KEY is the COLUMN B letter for that row's term. Because
        # rows can be SWAPPED in from a different source matching question,
        # the stored answer_text letter is POSITIONAL against a *different*
        # COLUMN B and almost never lines up with THIS paper's shared COLUMN B.
        # So we resolve every row by its TERM instead of its stale letter:
        #   * if the row's term is already in COLUMN B  -> key = that letter
        #   * if the term is NOT in COLUMN B (a freshly
        #     swapped-in item)                         -> append it as a new
        #                                                  lettered option and
        #                                                  key = the new letter
        #   * bare-letter rows (no term)               -> keep the stale letter
        # This makes the correct letter AND term "come over" with a swap while
        # preserving the original distractor terms already in COLUMN B. When
        # there was no Options block at all, COLUMN B is rebuilt purely from the
        # rows' terms. Per-row keys are emitted so the template renders the
        # resolved letter (not the stale answer_text letter), and a memo_answer
        # is stamped on any row whose resolved letter differs from its stored
        # letter so the marking guideline matches the paper.
        def _norm_term(t):
            t = re.sub(r'[\u2713\u2717\u2714\u2718\u00B7\u2022]', '', t or '')
            return re.sub(r'\s+', '', t).strip().lower()

        match_keys = None
        if ans_list:
            norm_map = {}           # normalised term -> letter (existing COLUMN B)
            used = set()
            for L, term in options:
                used.add(L)
                norm_map.setdefault(_norm_term(term), L)
            keys = []               # per-row resolved letter ('' when unknown)
            row_terms = []          # per-row display term ('' when none)

            def _next_free(pref):
                if pref and pref not in used:
                    return pref
                for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                    if c not in used:
                        return c
                return ''

            for a in ans_list:
                m = re.match(r'^\s*([A-Z])(?:[\)\.\:\-]|\s)\s*(.*)$', a or '')
                if not m:
                    keys.append('')
                    row_terms.append('')
                    continue
                stale = m.group(1)
                term = re.sub(r'[\u2713\u2717\u2714\u2718\u00B7\u2022]', '', m.group(2)).strip()
                if not term:
                    # Bare letter: best effort against the existing COLUMN B.
                    keys.append(stale if stale in used else '')
                    row_terms.append('')
                    continue
                row_terms.append(term)
                nt = _norm_term(term)
                if nt in norm_map:
                    keys.append(norm_map[nt])
                    continue
                # Term not in COLUMN B yet (swapped-in item): add it.
                L = _next_free(stale)
                if not L:
                    keys.append('')
                    continue
                used.add(L)
                norm_map[nt] = L
                options.append((L, term))
                keys.append(L)
            options = sorted(options, key=lambda x: x[0])
            match_keys = keys
            # Stamp a memo answer wherever the resolved letter differs from the
            # stored answer_text letter, so the marking guideline shows the same
            # letter the question paper does.
            run_items = qs[run_start:i]
            for k, it in enumerate(run_items):
                if k >= len(keys) or not keys[k] or not row_terms[k]:
                    continue
                stored = (it.answer_text or '').strip()[:1].upper()
                if keys[k] != stored:
                    try:
                        it.memo_answer = '%s %s \u2713' % (keys[k], row_terms[k])
                    except Exception:
                        pass
        # Attach the table to the first item in the run
        try:
            _tbl = {
                'rows': rows,
                'options': options,
                'count': len(rows),
                'total_marks': sum(m for _, m in rows),
                'row_ids': run_ids,
            }
            if match_keys is not None:
                _tbl['row_keys'] = match_keys
            qs[run_start].match_table = _tbl
        except Exception:
            pass
    return qs


@app.route('/teacher/generator/figure-width', methods=['POST'])
@teacher_required
def teacher_paper_figure_width():
    """Persist a per-question figure width (percent, 10-100).

    Body JSON: { qid: str, width: int }. Only the paper owner (or admin) may
    change an item's width when it's referenced by their own draft; we still
    enforce ownership of the bank item itself.
    """
    data = request.get_json(silent=True) or {}
    qid = (data.get('qid') or '').strip()
    if not qid:
        return jsonify({'ok': False, 'error': 'missing_qid'}), 400
    q = QuestionBankItem.query.get(qid)
    if not q:
        return jsonify({'ok': False, 'error': 'not_found'}), 404
    if not (current_user.is_admin or q.owner_id == current_user.id):
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    # Record prior image fields onto the owning paper's Undo stack (the
    # editor passes paper_id). Width drags coalesce into one Undo step.
    _push_qbi_edit_history((data.get('paper_id') or '').strip(), q, coalesce=True)
    if 'width' in data:
        try:
            width = int(data.get('width') or 0)
        except (TypeError, ValueError):
            return jsonify({'ok': False, 'error': 'bad_width'}), 400
        if width and (width < 10 or width > 100):
            return jsonify({'ok': False, 'error': 'out_of_range'}), 400
        q.image_width = width
    if 'offset' in data:
        try:
            offset = int(data.get('offset') or 0)
        except (TypeError, ValueError):
            return jsonify({'ok': False, 'error': 'bad_offset'}), 400
        if offset < -100 or offset > 100:
            return jsonify({'ok': False, 'error': 'out_of_range'}), 400
        q.image_offset = offset
    db.session.commit()
    return jsonify({'ok': True, 'qid': qid, 'width': q.image_width, 'offset': q.image_offset})


@app.route('/teacher/generator/figure-crop', methods=['POST'])
@teacher_required
def teacher_paper_figure_crop():
    """Crop a question's figure to a rectangular region.

    Body JSON: { qid: str, x: float, y: float, w: float, h: float } where
    x/y/w/h are FRACTIONS (0-1) of the currently displayed image (x,y =
    top-left of the selection; w,h = its width/height).

    The crop is applied to the actual image file with Pillow. The first
    crop of an image saves a one-time backup (``<name>.orig.<ext>``) so the
    original is never lost, then writes the cropped result to a NEW
    uniquely-named file and points ``image_path`` at it. Re-cropping
    therefore operates on the currently-shown (already cropped) image,
    matching what the user sees.
    """
    data = request.get_json(silent=True) or {}
    qid = (data.get('qid') or '').strip()
    if not qid:
        return jsonify({'ok': False, 'error': 'missing_qid'}), 400
    q = QuestionBankItem.query.get(qid)
    if not q:
        return jsonify({'ok': False, 'error': 'not_found'}), 404
    if not (current_user.is_admin or q.owner_id == current_user.id):
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    if not q.image_path:
        return jsonify({'ok': False, 'error': 'no_image'}), 400

    # Parse + validate the fractional crop rectangle.
    try:
        fx = float(data.get('x'))
        fy = float(data.get('y'))
        fw = float(data.get('w'))
        fh = float(data.get('h'))
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'error': 'bad_rect'}), 400
    # Clamp to [0,1] and require a non-trivial selection.
    fx = max(0.0, min(1.0, fx))
    fy = max(0.0, min(1.0, fy))
    fw = max(0.0, min(1.0 - fx, fw))
    fh = max(0.0, min(1.0 - fy, fh))
    if fw < 0.02 or fh < 0.02:
        return jsonify({'ok': False, 'error': 'selection_too_small'}), 400

    ext = (q.image_path.rsplit('.', 1)[-1] if '.' in q.image_path else '').lower()
    if ext == 'svg':
        return jsonify({'ok': False, 'error': 'svg_not_supported'}), 400

    abs_src = os.path.join(app.static_folder, q.image_path.replace('/', os.sep))
    if not os.path.isfile(abs_src):
        return jsonify({'ok': False, 'error': 'file_missing'}), 404

    try:
        from PIL import Image
    except Exception:
        return jsonify({'ok': False, 'error': 'pillow_unavailable'}), 500

    try:
        with Image.open(abs_src) as im:
            im.load()
            W, H = im.size
            left = int(round(fx * W))
            top = int(round(fy * H))
            right = int(round((fx + fw) * W))
            bottom = int(round((fy + fh) * H))
            # Guard against degenerate boxes after rounding.
            right = max(left + 1, min(W, right))
            bottom = max(top + 1, min(H, bottom))
            cropped = im.crop((left, top, right, bottom))

            # One-time backup of the very first (uncropped) source.
            base, dot, real_ext = q.image_path.rpartition('.')
            backup_rel = f"{base}.orig.{real_ext}" if dot else None
            if backup_rel:
                abs_backup = os.path.join(app.static_folder, backup_rel.replace('/', os.sep))
                if not os.path.exists(abs_backup):
                    try:
                        im.save(abs_backup)
                    except Exception:
                        pass

            # Write the cropped result to a new uniquely-named file in the
            # same folder so browser/proxy caches never serve a stale image.
            folder_rel = q.image_path.rsplit('/', 1)[0] if '/' in q.image_path else ''
            stem = (q.image_path.rsplit('/', 1)[-1].rsplit('.', 1)[0])
            # Strip any prior crop suffix so names don't grow unbounded.
            import re as _re
            stem = _re.sub(r'_c[0-9a-f]{6}$', '', stem)
            new_name = f"{stem}_c{uuid.uuid4().hex[:6]}.{real_ext or ext or 'png'}"
            new_rel = f"{folder_rel}/{new_name}" if folder_rel else new_name
            abs_dst = os.path.join(app.static_folder, new_rel.replace('/', os.sep))
            save_kwargs = {}
            if cropped.mode in ('RGBA', 'P') and (real_ext or ext) in ('jpg', 'jpeg'):
                cropped = cropped.convert('RGB')
            cropped.save(abs_dst, **save_kwargs)
    except Exception as exc:
        app.logger.warning('figure crop failed for %s: %s', qid, exc)
        return jsonify({'ok': False, 'error': 'crop_failed'}), 500

    # Record the prior image (uncropped) onto the paper's Undo stack before
    # repointing. Each crop is a distinct, deliberate Undo step (no coalesce).
    _push_qbi_edit_history((data.get('paper_id') or '').strip(), q, coalesce=False)
    q.image_path = new_rel
    db.session.commit()
    return jsonify({
        'ok': True,
        'qid': qid,
        'image_path': new_rel,
        'url': url_for('static', filename=new_rel),
    })


@app.route('/teacher/generator/figure-replace', methods=['POST'])
@teacher_required
def teacher_paper_figure_replace():
    """Replace a question's figure with a freshly-uploaded image.

    Multipart form: ``qid`` (str) + ``image`` (file). The uploaded image is
    saved to ``static/uploads/questions`` under a unique name and the item's
    ``image_path`` is repointed at it. The previous image file is left on
    disk untouched (it may be shared/backed up), so nothing is lost.
    """
    qid = (request.form.get('qid') or '').strip()
    if not qid:
        return jsonify({'ok': False, 'error': 'missing_qid'}), 400
    q = QuestionBankItem.query.get(qid)
    if not q:
        return jsonify({'ok': False, 'error': 'not_found'}), 404
    if not (current_user.is_admin or q.owner_id == current_user.id):
        return jsonify({'ok': False, 'error': 'forbidden'}), 403

    img = request.files.get('image')
    if not img or not img.filename:
        return jsonify({'ok': False, 'error': 'no_file'}), 400

    new_rel, _size = _save_upload(img, 'questions', TEACHER_LOGO_EXTS)
    if not new_rel:
        return jsonify({'ok': False, 'error': 'bad_format'}), 415

    # Record the prior image onto the paper's Undo stack before repointing.
    _push_qbi_edit_history((request.form.get('paper_id') or '').strip(), q, coalesce=False)
    q.image_path = new_rel
    db.session.commit()
    return jsonify({
        'ok': True,
        'qid': qid,
        'image_path': new_rel,
        'url': url_for('static', filename=new_rel),
    })


@app.route('/teacher/generator/<paper_id>/page-break', methods=['POST'])
@teacher_required
def teacher_paper_page_break(paper_id):
    """Toggle or shift a manual page-break for a given item.

    Body JSON: { qid: str, on: bool }  → toggle break BEFORE qid.
              { qid: str, action: 'up' | 'down' }
                  'up'   = pin qid to the previous page. Stores qid in
                           `no_breaks` so the auto-paginator is FORBIDDEN
                           from inserting a break before it (even if the
                           page-height budget is exceeded). Also removes
                           any forced break that was on qid.
                  'down' = force a break BEFORE qid (adds to
                           `forced_breaks`) and removes it from
                           `no_breaks`.
    """
    paper = GeneratedPaper.query.get_or_404(paper_id)
    if not (current_user.is_admin or paper.owner_id == current_user.id):
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    data = request.get_json(silent=True) or {}
    qid = (data.get('qid') or '').strip()
    action = (data.get('action') or '').strip().lower()
    on = bool(data.get('on'))
    if not qid:
        return jsonify({'ok': False, 'error': 'missing_qid'}), 400
    try:
        secs = json.loads(paper.sections or '[]')
    except Exception:
        secs = []
    if not isinstance(secs, list):
        return jsonify({'ok': False, 'error': 'bad_sections'}), 500
    _prior_sections = paper.sections or '[]'
    changed = False
    for sec in secs:
        if not isinstance(sec, dict):
            continue
        fb = list(sec.get('forced_breaks') or [])
        nb = list(sec.get('no_breaks') or [])
        qids = list(sec.get('question_ids') or [])
        try:
            idx = qids.index(qid)
        except ValueError:
            idx = -1
        if idx < 0:
            continue
        if action == 'up':
            # Pin qid to the previous page: forbid any break before qid.
            # Click again to un-pin (toggle).
            if qid in nb:
                nb = [x for x in nb if x != qid]
                changed = True
            else:
                if qid in fb:
                    fb = [x for x in fb if x != qid]
                    changed = True
                nb.append(qid)
                changed = True
        elif action == 'down':
            # Force a break before qid. Click again to un-force (toggle).
            if qid in fb:
                fb = [x for x in fb if x != qid]
                changed = True
            else:
                if qid in nb:
                    nb = [x for x in nb if x != qid]
                    changed = True
                fb.append(qid)
                changed = True
        else:
            if on:
                if qid not in fb:
                    fb.append(qid)
                    changed = True
                if qid in nb:
                    nb = [x for x in nb if x != qid]
                    changed = True
            else:
                if qid in fb:
                    fb = [x for x in fb if x != qid]
                    changed = True
                if qid in nb:
                    nb = [x for x in nb if x != qid]
                    changed = True
        if changed:
            sec['forced_breaks'] = fb
            sec['no_breaks'] = nb
    if changed:
        paper.sections = json.dumps(secs)
        # Record the prior page-break layout for one-step Undo.
        _push_edit_history(paper, {'t': 'sections', 'prev': _prior_sections})
        db.session.commit()
    return jsonify({'ok': True, 'qid': qid})


@app.route('/teacher/generator/<paper_id>/preview-edit', methods=['POST'])
@teacher_required
def teacher_paper_preview_edit(paper_id):
    """Persist a single in-preview WYSIWYG edit.

    Body JSON: { key: str, html?: str, deleted?: bool, clear?: bool }
        key       — stable element path (assigned by the client).
        html      — replacement innerHTML (Bold/Italic/font-size etc.).
        deleted   — when truthy, hides the element on subsequent renders.
        clear     — when truthy, removes any existing override for `key`.
    """
    paper = GeneratedPaper.query.get_or_404(paper_id)
    if not (current_user.is_admin or paper.owner_id == current_user.id
            or _can_moderate(paper)):
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    data = request.get_json(silent=True) or {}
    key = (data.get('key') or '').strip()
    if not key or len(key) > 600:
        return jsonify({'ok': False, 'error': 'bad_key'}), 400
    overrides = _load_preview_overrides(paper)
    # Capture the element's PRIOR override (or None if it had none) so the
    # unified Undo can roll this single edit back. Rapid edits to the SAME
    # element collapse into one Undo step via coalesce_on='key'.
    import copy as _copy
    _prev_override = _copy.deepcopy(overrides.get(key)) if key in overrides else None
    _push_edit_history(paper, {'t': 'text', 'key': key, 'prev': _prev_override},
                       coalesce_on='key')
    if data.get('clear'):
        overrides.pop(key, None)
    else:
        entry = overrides.get(key) if isinstance(overrides.get(key), dict) else {}
        if 'html' in data:
            html_val = data.get('html')
            if html_val is None:
                entry.pop('html', None)
            else:
                # Cap length defensively to keep a single override sane.
                entry['html'] = str(html_val)[:20000]
        if 'deleted' in data:
            if data.get('deleted'):
                entry['deleted'] = True
            else:
                entry.pop('deleted', None)
        if entry:
            overrides[key] = entry
        else:
            overrides.pop(key, None)
    paper.preview_overrides = json.dumps(overrides)
    db.session.commit()
    return jsonify({'ok': True, 'count': len(overrides)})


@app.route('/teacher/generator/<paper_id>/preview-edit/clear-all', methods=['POST'])
@teacher_required
def teacher_paper_preview_edit_clear_all(paper_id):
    paper = GeneratedPaper.query.get_or_404(paper_id)
    if not (current_user.is_admin or paper.owner_id == current_user.id
            or _can_moderate(paper)):
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    paper.preview_overrides = ''
    db.session.commit()
    return jsonify({'ok': True})


def _locate_qid_in_paper(paper, qid):
    """Return (sections_list, sec_idx, position) where the qid sits in
    paper.sections, or (None, None, None) if not found."""
    try:
        secs = json.loads(paper.sections or '[]')
    except Exception:
        return None, None, None
    if not isinstance(secs, list):
        return None, None, None
    for si, sec in enumerate(secs):
        if not isinstance(sec, dict):
            continue
        qids = sec.get('question_ids') or []
        if qid in qids:
            return secs, si, qids.index(qid)
    return None, None, None


@app.route('/teacher/generator/<paper_id>/bank-search', methods=['GET'])
@teacher_required
def teacher_paper_bank_search(paper_id):
    """Lightweight question-bank search used by the in-preview picker.
    Returns up to `limit` items matching the query in question_text/topic/subtopic.
    Scoped by the paper's grade+subject by default; pass `all=1` to widen.
    """
    paper = GeneratedPaper.query.get_or_404(paper_id)
    if not (current_user.is_admin or paper.owner_id == current_user.id
            or _can_moderate(paper)):
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    q = (request.args.get('q') or '').strip()
    limit = max(1, min(int(request.args.get('limit') or 50), 200))
    widen = (request.args.get('all') or '') in ('1', 'true', 'yes')
    types_raw = (request.args.get('type') or '').strip().lower()
    base = QuestionBankItem.query
    if not current_user.is_admin:
        base = base.filter(_bank_visible_filter())
    if not widen:
        if paper.grade:
            base = base.filter(QuestionBankItem.grade == paper.grade)
        if paper.subject:
            base = base.filter(db.func.lower(QuestionBankItem.subject) == (paper.subject or '').lower())
    if types_raw and types_raw != 'any':
        # The DB's `question_type` column stores topic-area labels
        # (short_answer, database, spreadsheet, …) — NOT format labels —
        # so we filter by answer shape for mcq / true_false, and by the
        # 'matching' label for matching items. "Structured" means anything
        # that ISN'T mcq / TF / matching.
        from sqlalchemy import func as _sqlfn
        _ans = _sqlfn.upper(_sqlfn.trim(QuestionBankItem.answer_text))
        _ans_len = _sqlfn.length(_sqlfn.trim(QuestionBankItem.answer_text))
        _qt_lower = _sqlfn.lower(QuestionBankItem.question_type)

        if types_raw == 'mcq':
            base = base.filter(_ans_len == 1, _ans.in_(['A', 'B', 'C', 'D', 'E']))
        elif types_raw == 'true_false':
            base = base.filter(
                db.or_(
                    _ans.in_(['TRUE', 'FALSE', 'T', 'F']),
                    _ans.like('TRUE,%'),
                    _ans.like('FALSE,%'),
                    _ans.like('TRUE %'),
                    _ans.like('FALSE %'),
                )
            )
        elif types_raw in ('match_columns', 'matching'):
            base = base.filter(_qt_lower == 'matching')
        elif types_raw in ('structured', 'short_answer', 'practical', 'stem'):
            # Exclude mcq / TF / matching from the "structured" pool.
            base = base.filter(_qt_lower != 'matching')
            base = base.filter(db.not_(db.and_(_ans_len == 1, _ans.in_(['A', 'B', 'C', 'D', 'E']))))
            base = base.filter(db.not_(_ans.in_(['TRUE', 'FALSE', 'T', 'F'])))
            base = base.filter(db.not_(_ans.like('TRUE,%')))
            base = base.filter(db.not_(_ans.like('FALSE,%')))
    if q:
        like = f'%{q}%'
        base = base.filter(db.or_(
            QuestionBankItem.question_text.ilike(like),
            QuestionBankItem.topic.ilike(like),
            QuestionBankItem.subtopic.ilike(like),
        ))
    base = base.order_by(QuestionBankItem.topic, QuestionBankItem.created_at.desc())
    rows = base.limit(limit).all()
    items = []
    for r in rows:
        snippet = (r.question_text or '').strip().replace('\n', ' ')
        if len(snippet) > 220:
            snippet = snippet[:217] + '...'
        items.append({
            'id': r.id,
            'snippet': snippet,
            'marks': r.marks or 0,
            'topic': r.topic or '',
            'subtopic': r.subtopic or '',
            'type': r.question_type or '',
        })
    return jsonify({'ok': True, 'items': items, 'count': len(items)})


_UNDO_STACK_LIMIT = 20
_EDIT_HISTORY_LIMIT = 60


def _push_edit_history(paper, record, coalesce_on=None):
    """Append a typed undo-record to the paper's unified edit-history.

    `record` is a small dict with a `t` (type) key plus the PRIOR state
    needed to revert one edit. When `coalesce_on` is given and the most
    recent record has the same type AND the same value for that field, the
    new record is skipped — so a burst of rapid edits to the SAME element
    (e.g. dragging a figure's width, or typing in one text box) collapses
    into a single Undo step back to the state before the burst began.
    """
    try:
        hist = json.loads(paper.edit_history or '[]')
        if not isinstance(hist, list):
            hist = []
    except Exception:
        hist = []
    if coalesce_on and hist:
        last = hist[-1]
        if (isinstance(last, dict) and last.get('t') == record.get('t')
                and last.get(coalesce_on) == record.get(coalesce_on)):
            return
    hist.append(record)
    if len(hist) > _EDIT_HISTORY_LIMIT:
        hist = hist[-_EDIT_HISTORY_LIMIT:]
    paper.edit_history = json.dumps(hist, ensure_ascii=False)


def _push_qbi_edit_history(paper_id, q, coalesce=False):
    """Record a figure item's CURRENT image fields onto the owning paper's
    edit-history before they are mutated by a width/crop/replace edit.

    `paper_id` is supplied by the editor so the per-paper Undo can later
    restore image_width / image_offset / image_path in one step. No-op when
    paper_id is missing or the caller can't edit that paper. The caller is
    responsible for committing the session.
    """
    if not paper_id:
        return
    paper = GeneratedPaper.query.get(paper_id)
    if not paper:
        return
    if not (current_user.is_admin or paper.owner_id == current_user.id
            or _can_moderate(paper)):
        return
    _push_edit_history(paper, {
        't': 'qbi',
        'qid': q.id,
        'w': int(q.image_width or 0),
        'o': int(q.image_offset or 0),
        'img': q.image_path or '',
    }, coalesce_on='qid' if coalesce else None)


def _push_undo_snapshot(paper):
    """Push the current paper.sections onto the undo stack (capped)."""
    try:
        stack = json.loads(paper.sections_undo_stack or '[]')
        if not isinstance(stack, list):
            stack = []
    except Exception:
        stack = []
    stack.append(paper.sections or '[]')
    if len(stack) > _UNDO_STACK_LIMIT:
        stack = stack[-_UNDO_STACK_LIMIT:]
    paper.sections_undo_stack = json.dumps(stack, ensure_ascii=False)
    # Also feed the unified edit-history so structural inserts are undoable
    # from the same Undo button as text/figure/page-break edits.
    _push_edit_history(paper, {'t': 'sections', 'prev': paper.sections or '[]'})


@app.route('/teacher/generator/<paper_id>/undo', methods=['POST'])
@teacher_required
def teacher_paper_undo(paper_id):
    """Pop the most-recent snapshot off the undo stack and restore it."""
    paper = GeneratedPaper.query.get_or_404(paper_id)
    if not (current_user.is_admin or paper.owner_id == current_user.id
            or _can_moderate(paper)):
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    try:
        stack = json.loads(paper.sections_undo_stack or '[]')
        if not isinstance(stack, list):
            stack = []
    except Exception:
        stack = []
    if not stack:
        return jsonify({'ok': False, 'error': 'nothing_to_undo'}), 400
    prev = stack.pop()
    paper.sections = prev or '[]'
    paper.sections_undo_stack = json.dumps(stack, ensure_ascii=False)
    db.session.commit()
    return jsonify({'ok': True, 'remaining': len(stack)})


@app.route('/teacher/generator/<paper_id>/undo-status', methods=['GET'])
@teacher_required
def teacher_paper_undo_status(paper_id):
    paper = GeneratedPaper.query.get_or_404(paper_id)
    if not (current_user.is_admin or paper.owner_id == current_user.id
            or _can_moderate(paper)):
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    try:
        stack = json.loads(paper.sections_undo_stack or '[]')
        n = len(stack) if isinstance(stack, list) else 0
    except Exception:
        n = 0
    return jsonify({'ok': True, 'count': n})


@app.route('/teacher/generator/<paper_id>/edit-history-status', methods=['GET'])
@teacher_required
def teacher_paper_edit_history_status(paper_id):
    """Return how many edits are on the unified Undo stack."""
    paper = GeneratedPaper.query.get_or_404(paper_id)
    if not (current_user.is_admin or paper.owner_id == current_user.id
            or _can_moderate(paper)):
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    try:
        hist = json.loads(paper.edit_history or '[]')
        n = len(hist) if isinstance(hist, list) else 0
    except Exception:
        n = 0
    return jsonify({'ok': True, 'count': n})


@app.route('/teacher/generator/<paper_id>/edit-undo', methods=['POST'])
@teacher_required
def teacher_paper_edit_undo(paper_id):
    """Undo the most-recent in-preview edit of ANY kind.

    Pops the last record off the unified edit-history and restores the prior
    state it captured: a text override, a figure's image fields
    (width/offset/crop/replace), the page-break layout, or a structural
    insert — whichever was the last change the teacher made.
    """
    paper = GeneratedPaper.query.get_or_404(paper_id)
    if not (current_user.is_admin or paper.owner_id == current_user.id
            or _can_moderate(paper)):
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    try:
        hist = json.loads(paper.edit_history or '[]')
        if not isinstance(hist, list):
            hist = []
    except Exception:
        hist = []
    if not hist:
        return jsonify({'ok': False, 'error': 'nothing_to_undo'}), 400
    rec = hist.pop()
    kind = (rec or {}).get('t')
    try:
        if kind == 'text':
            overrides = _load_preview_overrides(paper)
            key = rec.get('key') or ''
            prev = rec.get('prev')
            if prev is None:
                overrides.pop(key, None)
            else:
                overrides[key] = prev
            paper.preview_overrides = json.dumps(overrides)
        elif kind == 'qbi':
            q = QuestionBankItem.query.get(rec.get('qid'))
            if q and (current_user.is_admin or q.owner_id == current_user.id):
                q.image_width = int(rec.get('w') or 0)
                q.image_offset = int(rec.get('o') or 0)
                q.image_path = rec.get('img') or ''
        elif kind == 'qtxt':
            q = QuestionBankItem.query.get(rec.get('qid'))
            if q and (current_user.is_admin or q.owner_id == current_user.id):
                q.question_text = rec.get('qt') or ''
                q.answer_text = rec.get('ans') or ''
                q.question_type = rec.get('ty') or ''
                try:
                    q.marks = max(0, int(rec.get('m') or 0))
                except Exception:
                    q.marks = 0
        elif kind == 'sections':
            paper.sections = rec.get('prev') or '[]'
        # Unknown record types are simply discarded (already popped).
    except Exception as exc:
        app.logger.warning('edit-undo failed for %s: %s', paper_id, exc)
        return jsonify({'ok': False, 'error': 'undo_failed'}), 500
    paper.edit_history = json.dumps(hist, ensure_ascii=False)
    db.session.commit()
    return jsonify({'ok': True, 'type': kind, 'remaining': len(hist)})


@app.route('/teacher/generator/<paper_id>/insert-question', methods=['POST'])
@teacher_required
def teacher_paper_insert_question(paper_id):
    """Insert a question from the bank into a section.

    Body JSON: { question_id, after_qid? | before_qid? | section_idx? }
        - after_qid : insert immediately after that qid (same section/group).
        - before_qid: insert immediately before that qid.
        - section_idx: append to end of that section (used when there is no anchor).
    Splits/groups are kept consistent: any split index >= insertion_idx is bumped by 1.
    """
    paper = GeneratedPaper.query.get_or_404(paper_id)
    if not (current_user.is_admin or paper.owner_id == current_user.id
            or _can_moderate(paper)):
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    data = request.get_json(silent=True) or {}
    new_qid = (data.get('question_id') or '').strip()
    if not new_qid:
        return jsonify({'ok': False, 'error': 'missing_question_id'}), 400
    if not QuestionBankItem.query.get(new_qid):
        return jsonify({'ok': False, 'error': 'question_not_found'}), 404
    try:
        secs = json.loads(paper.sections or '[]')
    except Exception:
        secs = []
    if not isinstance(secs, list) or not secs:
        return jsonify({'ok': False, 'error': 'no_sections'}), 400

    after_qid = (data.get('after_qid') or '').strip()
    before_qid = (data.get('before_qid') or '').strip()
    section_idx = data.get('section_idx')

    sec_idx = None
    insertion_idx = None
    if after_qid:
        for si, sec in enumerate(secs):
            qids = (sec.get('question_ids') or [])
            if after_qid in qids:
                sec_idx = si
                insertion_idx = qids.index(after_qid) + 1
                break
    elif before_qid:
        for si, sec in enumerate(secs):
            qids = (sec.get('question_ids') or [])
            if before_qid in qids:
                sec_idx = si
                insertion_idx = qids.index(before_qid)
                break
    elif isinstance(section_idx, int) and 0 <= section_idx < len(secs):
        sec_idx = section_idx
        insertion_idx = len(secs[sec_idx].get('question_ids') or [])

    if sec_idx is None or insertion_idx is None:
        return jsonify({'ok': False, 'error': 'anchor_not_found'}), 404

    _push_undo_snapshot(paper)
    sec = secs[sec_idx]
    qids = list(sec.get('question_ids') or [])
    qids.insert(insertion_idx, new_qid)
    sec['question_ids'] = qids

    splits = list(sec.get('splits') or [0])
    new_splits = []
    for s in splits:
        try:
            si_v = int(s)
        except Exception:
            continue
        new_splits.append(si_v + 1 if si_v >= insertion_idx else si_v)
    if not new_splits or new_splits[0] != 0:
        new_splits = [0] + [s for s in new_splits if s != 0]
    sec['splits'] = sorted(set(new_splits))

    paper.sections = json.dumps(secs, ensure_ascii=False)
    db.session.commit()
    return jsonify({'ok': True, 'section_idx': sec_idx, 'position': insertion_idx})


@app.route('/teacher/generator/<paper_id>/preview')
@teacher_required
def teacher_paper_preview(paper_id):
    paper = GeneratedPaper.query.get_or_404(paper_id)
    requested_version = (request.args.get('version') or '').strip().lower()
    if requested_version:
        version = requested_version
    else:
        # When the moderator returns/signs off a paper, default to the
        # diff view so green edits + struck old text are visible.
        if ((paper.moderation_status or '') in ('rejected', 'signed_off')
                and (paper.sections_original or '').strip()):
            version = 'moderated'
        else:
            version = 'current'
    if version not in ('current', 'original', 'moderated', 'final'):
        version = 'current'
    # Owner / admin / moderator can always preview their own draft.
    # Other teachers & HODs may preview any paper read-only once it is signed off.
    is_owner = paper.owner_id == current_user.id
    if not (is_owner or current_user.is_admin or _can_moderate(paper)):
        if not _can_view_paper(paper):
            abort(404)
        if not _can_print_paper(paper):
            flash('This paper has not been signed off yet, so a preview is not available.',
                  'info')
            return redirect(url_for('teacher_papers_generated'))
    ctx = _build_paper_context(paper, with_memo=False, version=version)
    ctx['version'] = version
    _inject_force_page_count(ctx, paper, with_memo=False, version=version)
    _pv = Response(render_template('teacher/paper_print.html', **ctx))
    # Never serve a stale cached preview: the editor's iframe must always
    # reflect the latest saved sections after a swap/add/undo.
    _pv.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    _pv.headers['Pragma'] = 'no-cache'
    _pv.headers['Expires'] = '0'
    return _pv


@app.route('/teacher/generator/<paper_id>/memo')
@teacher_required
def teacher_paper_memo(paper_id):
    paper = GeneratedPaper.query.get_or_404(paper_id)
    requested_version = (request.args.get('version') or '').strip().lower()
    if requested_version:
        version = requested_version
    else:
        # Keep memo behavior aligned with preview for moderator-returned papers.
        if ((paper.moderation_status or '') in ('rejected', 'signed_off')
                and (paper.sections_original or '').strip()):
            version = 'moderated'
        else:
            version = 'current'
    if version not in ('current', 'original', 'moderated', 'final'):
        version = 'current'
    is_owner = paper.owner_id == current_user.id
    if not (is_owner or current_user.is_admin or _can_moderate(paper)):
        if not _can_view_paper(paper):
            abort(404)
        if not _can_print_paper(paper):
            flash('This memo will be available once the paper has been signed off.',
                  'info')
            return redirect(url_for('teacher_papers_generated'))
    ctx = _build_paper_context(paper, with_memo=True, version=version)
    ctx['version'] = version
    _inject_force_page_count(ctx, paper, with_memo=True, version=version)
    _resp = Response(render_template('teacher/paper_print.html', **ctx))
    _resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    _resp.headers['Pragma'] = 'no-cache'
    _resp.headers['Expires'] = '0'
    return _resp


# =====================================================================
#  EDITABLE WORD (.docx) EXPORT  — question paper + marking guideline
# =====================================================================
def _docx_strip(text):
    """Flatten rendered/marker HTML into plain text for a Word run.

    Removes the custom ``[[MARKER]]`` box tokens, turns ``[[BR]]``/<br>
    and block-level closing tags into newlines, drops all remaining HTML
    tags and unescapes entities.
    """
    if not text:
        return ''
    import html as _html
    s = str(text)
    # Remove the synthetic auto-generated header line "[Auto] Section X — <label>"
    # (e.g. "[Auto] Section C — Integrated Scenario"): it duplicates the section
    # heading / question title and must never appear as instruction body text.
    s = re.sub(r'(?im)^\s*\[Auto\]\s*Section\b[^\n]*[\u2014\u2013-][^\n]*(?:\n|$)', '', s, count=1)
    # Strip any remaining internal '[Auto] ' auto-fill marker (start of block or
    # any line); it must never appear in the exported document.
    s = re.sub(r'(?im)^\s*\[Auto\]\s*', '', s)
    s = s.replace('[[BR]]', '\n')
    # Bullet + line markers used inside answer bodies.
    s = re.sub(r'(?i)<\s*br\s*/?>', '\n', s)
    s = re.sub(r'(?i)</\s*(p|li|div|tr|h[1-6])\s*>', '\n', s)
    s = re.sub(r'(?i)<\s*li[^>]*>', '\u2022 ', s)
    # Any remaining bracket tokens (box openers/closers, icons).
    s = re.sub(r'\[\[/?[A-Za-z0-9_]+\]\]', '', s)
    # Strip the rest of the HTML.
    s = re.sub(r'<[^>]+>', '', s)
    s = _html.unescape(s)
    # Collapse excess blank lines.
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()


def _docx_add_runs(paragraph, text, bold=False, italic=False):
    """Append runs to ``paragraph`` honouring inline **bold** / __underline__
    and HTML <b>/<strong> bold tags."""
    if text is None:
        text = ''
    # Normalise HTML bold tags to the **markdown** form so they render as
    # real bold runs (instead of showing the literal <b>…</b> tags).
    text = re.sub(r'</?(?:b|strong)\s*>', '**', str(text), flags=re.I)
    for tok in re.split(r'(\*\*.+?\*\*|__.+?__)', str(text)):
        if not tok:
            continue
        if len(tok) >= 4 and tok.startswith('**') and tok.endswith('**'):
            run = paragraph.add_run(tok[2:-2]); run.bold = True
        elif len(tok) >= 4 and tok.startswith('__') and tok.endswith('__'):
            run = paragraph.add_run(tok[2:-2]); run.underline = True
        else:
            run = paragraph.add_run(tok)
        if bold:
            run.bold = True
        if italic:
            run.italic = True


def _paper_to_docx(paper, with_memo=False, version='current'):
    """Build an editable Word document (BytesIO) for the paper or memo.

    Data-driven from the same resolved context the print view uses. Word
    cannot render the paper's CSS-grid/flex layout, so the tabular parts
    (the question + marks columns, matching COLUMN A/COLUMN B tables, and
    memo comparison tables) are rebuilt as REAL, editable Word tables so
    tables, layout and formatting are preserved."""
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
    from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT

    RIGHT = WD_ALIGN_PARAGRAPH.RIGHT
    CENTER = WD_ALIGN_PARAGRAPH.CENTER

    ctx = _build_paper_context(paper, with_memo=with_memo, version=version)
    pv = ctx.get('paper')
    sections = ctx.get('sections') or []
    grand_marks = ctx.get('grand_marks')

    doc = Document()
    normal = doc.styles['Normal']
    normal.font.name = 'Arial'
    normal.font.size = Pt(11)

    def _para(text, *, bold=False, italic=False, align=None, size=None,
              space_after=None, indent=False):
        p = doc.add_paragraph()
        if align is not None:
            p.alignment = align
        if indent:
            p.paragraph_format.left_indent = Inches(0.35)
        if space_after is not None:
            p.paragraph_format.space_after = Pt(space_after)
        _docx_add_runs(p, text, bold=bold, italic=italic)
        if size is not None:
            for run in p.runs:
                run.font.size = Pt(size)
        return p

    def _cell_para(cell, *, first=False):
        """Return a paragraph in a table cell, reusing the empty default
        first paragraph the first time so cells don't start with a blank
        line."""
        p0 = cell.paragraphs[0]
        if first and not p0.runs and not (p0.text or '').strip():
            return p0
        return cell.add_paragraph()

    def _cell_text(cell, text, *, bold=False, italic=False, align=None,
                   size=None, first=False):
        p = _cell_para(cell, first=first)
        if align is not None:
            p.alignment = align
        _docx_add_runs(p, text, bold=bold, italic=italic)
        if size is not None:
            for r in p.runs:
                r.font.size = Pt(size)
        return p

    # A leading number (1, 1.1, 1.1.1, 1) / bracketed (1) / bullet marker.
    _MARK_RE = re.compile(
        r'^\s*(\d+(?:\.\d+)*[.)]?|\(\d+\)|[\u2022\u25AA\u25CF\u2023\u2043\u25E6\-])\s+(.*)$',
        re.S)

    def _apply_hang(p, marker_base, text_off):
        """Set a hanging indent so a wrapped line aligns with the text after
        the marker (never under the number/bullet)."""
        left = marker_base + text_off
        pf = p.paragraph_format
        pf.left_indent = Inches(left)
        pf.first_line_indent = Inches(-text_off)
        pf.space_after = Pt(4)
        pf.line_spacing = 1.15
        try:
            pf.tab_stops.add_tab_stop(Inches(left), WD_TAB_ALIGNMENT.LEFT)
        except Exception:
            pass

    def _hang_line(p, marker, text, marker_base, text_off, *, bold_marker=False):
        """Render `marker<TAB>text` in paragraph `p` with a hanging indent."""
        _apply_hang(p, marker_base, text_off)
        if marker:
            r = p.add_run(str(marker))
            r.bold = bold_marker
            p.add_run('\t')
        _docx_add_runs(p, text)
        return p

    def _ends_sentence(t):
        """True if line `t` looks like the end of a sentence/paragraph (so the
        next line should NOT be merged into it). Trailing quotes/brackets are
        ignored; an ellipsis is treated as a mid-sentence continuation."""
        t = re.sub(r'[\'"\)\]\u2019\u201d]+$', '', (t or '').rstrip()).rstrip()
        if not t:
            return False
        if t.endswith('\u2026') or t.endswith('...'):
            return False
        return t[-1] in '.!?:'

    def _segments(text, reflow=True):
        """Split text into logical paragraphs. When `reflow` is on, physical
        line-breaks that are just PDF word-wrap artifacts (previous line did
        not end a sentence and the next line is not a list marker) are merged
        back into one flowing paragraph — so the Word copy wraps naturally
        like the printed paper instead of breaking mid-sentence.

        Multiple-choice option lines (``A  ...``, ``B  ...`` — a single letter
        followed by 2+ spaces) are ALWAYS kept on their own line so options do
        not run together."""
        _opt_re = re.compile(r'^[A-H]\s{2,}\S')
        segs = []
        prev_opt = False
        for ln in str(text or '').split('\n'):
            s = ln.strip()
            if not s:
                continue
            is_opt = bool(_opt_re.match(s))
            if (not segs or not reflow or _MARK_RE.match(s)
                    or is_opt or prev_opt or _ends_sentence(segs[-1])):
                segs.append(s)
            else:
                segs[-1] = segs[-1] + ' ' + s
            prev_opt = is_opt
        return segs
        return segs

    def _render_one(p, s, base, justify):
        """Render a single logical paragraph `s` into paragraph `p`."""
        if justify:
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        m = _MARK_RE.match(s)
        if m:
            marker, rest = m.group(1), m.group(2)
            is_num = any(c.isdigit() for c in marker)
            depth = marker.count('.') if is_num else 0
            # DBE nesting: a top-level sub-question (x.x, depth 1) sits at the
            # left margin; each deeper level (x.x.x, x.x.x.x) indents so its
            # NUMBER aligns under the parent item's TEXT (one text-offset per
            # level). Non-numbered/bulleted lines keep the base indent.
            if is_num:
                off = 0.5
                mb = base + off * max(0, depth - 1)
            else:
                off = 0.3
                mb = base
            _hang_line(p, marker, rest, mb, off)
        else:
            pf = p.paragraph_format
            pf.left_indent = Inches(base)
            pf.space_after = Pt(4)
            pf.line_spacing = 1.15
            _docx_add_runs(p, s)
        return p

    def _render_block(new_para, text, base=0.0, justify=True, reflow=True):
        """Render a (possibly multi-line) block. Numbered/bulleted lines get a
        hanging indent; wrap-artifact lines are reflowed into flowing
        paragraphs (see `_segments`)."""
        for s in _segments(text, reflow=reflow):
            _render_one(new_para(), s, base, justify)

    def _render_instructions(text):
        """Render the 'INSTRUCTIONS AND INFORMATION' list: items are separated
        by a blank line and NUMBERED 1., 2., 3., ... with a hanging indent. A
        run of `* *filename* * type` bullets (the data-files list) becomes a
        bordered file-list box."""
        norm = str(text or '').replace('\r\n', '\n').replace('\r', '\n')
        items = re.split(r'\n\s*\n', norm) if '\n\n' in norm else norm.split('\n')

        def _fileitem(s):
            # A "<b>filename</b> type" or "**filename** type" data-file line.
            fm = re.match(
                r'^\s*(?:\*\*|<b>|<strong>)(.+?)(?:\*\*|</b>|</strong>)\s*(.*)$',
                s.strip(), re.I)
            return (fm.group(1).strip(), fm.group(2).strip()) if fm else None

        num = 0
        off = 0.45
        for item in items:
            lines = []
            for raw in item.split('\n'):
                s = raw.strip()
                if not s or s.startswith('[Auto]'):
                    continue
                s = re.sub(r'^\s*\d{1,2}\s*[.)]\s+', '', s)
                lines.append(s)
            if not lines:
                continue
            num += 1
            # Group into paragraph vs bullet-run blocks.
            blocks = []
            for s in lines:
                if s[:1] in '\u2022\u25AA\u25CF\u2023\u2043\u25E6-':
                    b = s[1:].strip()
                    if blocks and blocks[-1][0] == 'bullets':
                        blocks[-1][1].append(b)
                    else:
                        blocks.append(['bullets', [b]])
                else:
                    blocks.append(['p', s])
            numbered = False
            for kind, payload in blocks:
                if kind == 'p':
                    p = doc.add_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    if not numbered:
                        _hang_line(p, f'{num}.', payload, 0.0, off)
                        numbered = True
                    else:
                        pf = p.paragraph_format
                        pf.left_indent = Inches(off)
                        pf.space_after = Pt(4)
                        pf.line_spacing = 1.15
                        _docx_add_runs(p, payload)
                else:
                    if not numbered:
                        _hang_line(doc.add_paragraph(), f'{num}.', '', 0.0, off)
                        numbered = True
                    fitems = [_fileitem(b) for b in payload]
                    if fitems and all(fitems):
                        # DBE data-file list: ONE bordered box (no internal
                        # grid lines) with bullet | filename | type aligned
                        # into columns via tab stops.
                        box = _bordered_table(1)
                        bx = box.add_row().cells[0]
                        for _fi, (name, typ) in enumerate(fitems):
                            fp = _cell_para(bx, first=(_fi == 0))
                            pf = fp.paragraph_format
                            pf.left_indent = Inches(0.45)
                            pf.first_line_indent = Inches(-0.3)
                            pf.space_after = Pt(2)
                            pf.line_spacing = 1.1
                            try:
                                pf.tab_stops.add_tab_stop(
                                    Inches(0.45), WD_TAB_ALIGNMENT.LEFT)
                                pf.tab_stops.add_tab_stop(
                                    Inches(2.0), WD_TAB_ALIGNMENT.LEFT)
                            except Exception:
                                pass
                            fp.add_run('\u2022')
                            fp.add_run('\t')
                            fp.add_run(name)
                            fp.add_run('\t')
                            fp.add_run(typ)
                    else:
                        for b in payload:
                            _hang_line(doc.add_paragraph(), '\u2022', b, off, 0.28)

    def _add_image(cell, q):
        img_rel = (getattr(q, 'image_path', '') or '').strip()
        if not img_rel:
            return
        img_abs = os.path.join(app.static_folder, img_rel.replace('/', os.sep))
        if not os.path.isfile(img_abs):
            return
        # Available content width inside the body cell (inches). The body
        # cell (~5.9") plus the marks cell (~0.6") is wider than the 6.0"
        # printable area, so a full 5.9" image spills past the right margin
        # and gets clipped. Cap a bit narrower so figures stay fully visible.
        avail = 5.3
        # Natural width at 96 dpi — used so small figures/icons are NOT
        # upscaled (which would blur them), while large diagrams/screenshots
        # are allowed to fill the column.
        nat_w = None
        try:
            from PIL import Image as _PILImage
            with _PILImage.open(img_abs) as _im:
                nat_w = _im.size[0] / 96.0
        except Exception:
            nat_w = None
        try:
            width_pct = getattr(q, 'image_width', 0) or 0
            if width_pct:
                # Explicit width set in the editor: honour it as a % of the
                # available column width.
                w_in = width_pct / 100.0 * avail
            else:
                # Default: fill the available column width (as in the printed
                # paper, where diagrams span the text column) instead of a
                # fixed 60% that leaves wide images cramped/unreadable.
                w_in = avail
            if nat_w:
                w_in = min(w_in, nat_w)
            w_in = max(1.0, min(avail, w_in))
            cell.add_paragraph().add_run().add_picture(img_abs, width=Inches(w_in))
        except Exception:
            pass

    def _new_marks_table():
        """A borderless 2-column table: content | right-aligned marks. This
        reproduces the paper's body/marks column layout."""
        t = doc.add_table(rows=0, cols=2)
        t.autofit = False
        t.allow_autofit = False
        return t

    def _marks_row(t):
        row = t.add_row()
        bc, mc = row.cells
        bc.width = Inches(5.9)
        mc.width = Inches(0.6)
        mc.vertical_alignment = WD_ALIGN_VERTICAL.TOP
        return bc, mc

    def _bordered_table(ncols):
        t = doc.add_table(rows=0, cols=ncols)
        t.style = 'Table Grid'
        t.autofit = True
        return t

    def _render_cmp_table(ct):
        """Render a memo comparison table (list-of-rows, each a list of
        column cells) as a bordered Word table."""
        rows = [r for r in (ct or []) if r]
        if not rows:
            return
        ncol = max(len(r) for r in rows)
        t = _bordered_table(ncol)
        for r in rows:
            cells = t.add_row().cells
            for ci in range(ncol):
                val = r[ci] if ci < len(r) else ''
                _cell_text(cells[ci], _docx_strip(str(val)), first=True)

    # ---- Cover page (DBE layout) -----------------------------------
    _title = getattr(pv, 'title', '') or ''
    authority = (getattr(pv, 'cover_authority', '') or
                 'SENIOR CERTIFICATE EXAMINATIONS/\n'
                 'NATIONAL SENIOR CERTIFICATE EXAMINATIONS')
    for ln in authority.replace('\r', '').split('\n'):
        if ln.strip():
            _para(ln.strip(), bold=True, align=CENTER, size=12)

    doc.add_paragraph()

    # Boxed subject + sitting (bordered, centred).
    subj = (getattr(pv, 'subject', '') or '').strip()
    subj = re.sub(r'(?i)\s*[/\-]?\s*(?:paper\s*\d+|p\s*\d+)\s*$', '', subj).strip()
    subj = re.sub(r'^(.+?)\1+$', r'\1', subj) or subj
    pno = (str(getattr(pv, 'paper_number', '') or '').strip()
           or ('2' if ('P2' in _title or 'Paper 2' in _title)
               else '3' if ('P3' in _title or 'Paper 3' in _title) else '1'))
    pno = re.sub(r'(?i)^p(?:aper)?\s*', '', pno) or '1'
    exam_date = getattr(pv, 'exam_date', None)
    month = year = ''
    if exam_date:
        try:
            month = exam_date.strftime('%B')
            year = exam_date.strftime('%Y')
        except Exception:
            pass
    if not year:
        _ym = re.search(r'(20\d{2})', _title)
        year = _ym.group(1) if _ym else ''
    box = doc.add_table(rows=1, cols=1)
    box.style = 'Table Grid'
    box.alignment = WD_TABLE_ALIGNMENT.CENTER
    bcell = box.rows[0].cells[0]
    bcell.width = Inches(4.7)
    _sp = bcell.paragraphs[0]
    _sp.alignment = CENTER
    _sp.paragraph_format.space_before = Pt(20)
    _r = _sp.add_run(f'{subj.upper()} P{pno}'.strip())
    _r.bold = True
    _r.font.size = Pt(13)
    _dp = bcell.add_paragraph()
    _dp.alignment = CENTER
    _dp.paragraph_format.space_before = Pt(10)
    _dp.paragraph_format.space_after = Pt(20)
    _dtxt = (f'{month} {year}' if (month and not with_memo) else year).strip().upper()
    if _dtxt:
        _r = _dp.add_run(_dtxt)
        _r.bold = True
        _r.font.size = Pt(13)
    if with_memo:
        _mgp = bcell.add_paragraph()
        _mgp.alignment = CENTER
        _mgp.paragraph_format.space_after = Pt(16)
        _r = _mgp.add_run((getattr(pv, 'memo_title', '') or 'MARKING GUIDELINES').upper())
        _r.bold = True

    doc.add_paragraph()

    # Sum each question's marks ONCE. Pagination `continued` chunks repeat a
    # group's marks (a question may carry its full total on both chunks), so
    # `grand_marks`/section marks can be inflated — count a chunk only when it
    # is the LAST of its question (matches the per-question [N] totals).
    def _section_marks(_sec):
        _gs = _sec.get('qgroups') or []
        if not _gs:
            return _sec.get('marks') or 0
        _sm = 0
        for _i, _g in enumerate(_gs):
            _last = (_i + 1 >= len(_gs)
                     or not bool(_gs[_i + 1].get('continued')))
            if _last:
                _sm += _g.get('marks') or 0
        return _sm

    _computed_total = sum(_section_marks(_s) for _s in sections)
    total = (getattr(pv, 'total_marks', 0) or 0) or _computed_total or grand_marks
    if total:
        _para(f'MARKS:  {total}', bold=True, align=RIGHT)
    dur = getattr(pv, 'duration_minutes', 0) or 0
    if dur and not with_memo:
        hrs = dur // 60
        mins = dur % 60
        if mins == 0:
            dur_txt = f'{hrs} hour' + ('s' if hrs != 1 else '')
        else:
            dur_txt = (f'{hrs} hour' + ('s' if hrs != 1 else '')
                       + f' {mins} min' + ('s' if mins != 1 else ''))
        _para(f'TIME:  {dur_txt}', bold=True, align=RIGHT)

    doc.add_paragraph()

    note = _docx_strip(getattr(pv, 'cover_extra_note', '') or '')
    if not note:
        _n = len(sections) + 2
        note = ((f'These marking guidelines consist of {_n} pages.') if with_memo
                else (f'This question paper consists of {_n} pages.'))
    _para(note, bold=True, align=CENTER)

    doc.add_page_break()

    # ---- MEMO: reproduce the official Marking Guideline PDF ---------
    # When exporting a memo AND the DBE Marking Guideline PDF for this paper
    # is on disk, rebuild its headers + criteria grid as real Word tables so
    # the Word memo matches the MG exactly (No./Criteria/Maximum Mark/
    # Candidate Mark layout). Falls back to the data-driven memo otherwise.
    def _render_mg_pdf(mg_path):
        try:
            import fitz  # PyMuPDF
        except Exception:
            return False
        _chrome = ('computer applications technology', 'nsc – marking',
                   'nsc - marking', 'copyright reserved', 'please turn over',
                   'dbe stamp', 'examination', 'marking guidelines',
                   'dbe/november', 'dbe/ november')

        def _is_chrome(t):
            s = (t or '').strip().lower()
            if not s:
                return True
            if s.isdigit():
                return True
            if s in ('number', 'centre'):
                return True
            return any(c in s for c in _chrome)

        # Map Symbol/Wingdings private-use-area glyphs (which the DBE PDF uses
        # for circled numbers / sub-bullets and which render as empty boxes in
        # Word) to real Unicode; strip any other unknown PUA chars.
        _pua = {
            '\uf0b7': '\u2022', '\uf0a7': '\u25aa', '\uf0a8': '\u25aa',
            '\uf0a9': '\u25aa', '\uf0fc': '\u2713', '\uf0fb': '\u2713',
            '\uf0e0': '\u2192',
            '\uf081': '\u2460', '\uf082': '\u2461', '\uf083': '\u2462',
            '\uf084': '\u2463', '\uf085': '\u2464', '\uf086': '\u2465',
            '\uf087': '\u2466', '\uf088': '\u2467', '\uf089': '\u2468',
        }

        def _mg_clean(s):
            if not s:
                return s
            out = []
            for ch in s:
                if ch in _pua:
                    out.append(_pua[ch])
                elif 0xE000 <= ord(ch) <= 0xF8FF:
                    out.append('')  # drop unknown private-use glyphs (tofu)
                else:
                    out.append(ch)
            return ''.join(out)

        try:
            mdoc = fitz.open(mg_path)
        except Exception:
            return False
        rendered_any = False
        # Scanned/image-only Marking Guideline (no extractable text or tables):
        # embed each page as a full-width image so the generated memo still
        # faithfully shows the official MG.
        try:
            _scan_txt = sum(len((mdoc[_p].get_text() or '').strip())
                            for _p in range(mdoc.page_count))
        except Exception:
            _scan_txt = 1
        if _scan_txt < 40 and mdoc.page_count > 0:
            for _p in range(1, mdoc.page_count):  # skip MG cover grid (page 0)
                try:
                    _pix = mdoc[_p].get_pixmap(dpi=150)
                    _ibuf = io.BytesIO(_pix.tobytes('png'))
                    doc.add_picture(_ibuf, width=Inches(6.3))
                    rendered_any = True
                    if _p < mdoc.page_count - 1:
                        doc.add_page_break()
                except Exception:
                    pass
            return rendered_any
        for pno in range(1, mdoc.page_count):  # skip cover grid (page 0)
            page = mdoc[pno]
            try:
                tabs = [t for t in page.find_tables().tables
                        if t.col_count >= 4 and t.row_count >= 2]
            except Exception:
                tabs = []
            tbbox = [t.bbox for t in tabs]

            def _in_table(y):
                return any(bb[1] - 2 <= y <= bb[3] + 2 for bb in tbbox)

            # Group non-chrome text lines (outside tables) into visual lines.
            # Collect non-table, non-chrome text lines, then group them into
            # VISUAL lines with a y-tolerance (a bullet marker and its text
            # sit on the same visual line but have a small baseline offset —
            # a fixed y/4 bucket wrongly split them, producing empty "•"
            # lines). Wrapped continuation lines are merged into their bullet.
            try:
                d = page.get_text('dict')
            except Exception:
                d = {'blocks': []}
            _raw = []
            for blk in d.get('blocks', []):
                for ln in blk.get('lines', []):
                    txt = ''.join(sp.get('text', '') for sp in ln.get('spans', []))
                    if not txt.strip():
                        continue
                    y0 = ln['bbox'][1]
                    x0 = ln['bbox'][0]
                    if _in_table(y0) or _is_chrome(txt):
                        continue
                    _raw.append((y0, x0, txt.strip()))
            _raw.sort()
            # Group into visual lines (within ~6pt).
            _vl = []  # each: [y, [(x, txt), ...]]
            for y0, x0, txt in _raw:
                if _vl and abs(y0 - _vl[-1][0]) <= 6:
                    _vl[-1][1].append((x0, txt))
                else:
                    _vl.append([y0, [(x0, txt)]])
            # Build (y, min_x, text) per visual line.
            _lines = []
            for y0, parts in _vl:
                parts.sort()
                _minx = min(p[0] for p in parts)
                _txt = ' '.join(p[1] for p in parts)
                _lines.append([y0, _minx, _txt])
            # Merge wrapped continuations: a line that does NOT start with a
            # bullet and is indented (min_x >= 55) folds into the previous
            # line (which is a bullet/note), not a left-margin header.
            _merged_lines = []
            for y0, minx, txt in _lines:
                _isbul = txt.lstrip().startswith(('•', '\u2022'))
                if (_merged_lines and not _isbul and minx >= 55):
                    _merged_lines[-1][2] = _merged_lines[-1][2] + ' ' + txt
                else:
                    _merged_lines.append([y0, minx, txt])

            items = []
            for y0, minx, txt in _merged_lines:
                items.append((y0, 'text', _mg_clean(txt)))
            for t in tabs:
                items.append((t.bbox[1], 'table', t))
            items.sort(key=lambda it: it[0])

            for _y, kind, payload in items:
                if kind == 'text':
                    _low = payload.lower()
                    _italic = _low.startswith('check the accuracy')
                    _isbul = payload.lstrip().startswith(('•', '\u2022'))
                    if _isbul:
                        # Marking-note bullet: hanging indent, not bold.
                        _bp = doc.add_paragraph()
                        _btxt = payload.lstrip()[1:].strip()
                        _hang_line(_bp, '\u2022', _btxt, 0.1, 0.2)
                    else:
                        _para(payload, bold=not _italic, italic=_italic,
                              space_after=3)
                else:
                    data = payload.extract()
                    if not data:
                        continue
                    ncol = max(len(r) for r in data)
                    if ncol < 3:
                        continue
                    data = [list(r) + [''] * (ncol - len(r)) for r in data]

                    def _col_has(ci):
                        return any((data[ri][ci] or '').strip()
                                   for ri in range(len(data)))

                    # Canonical 6-column DBE grid, mapped by ROLE so every
                    # question table has the SAME columns regardless of how
                    # find_tables fragments them:
                    #   No. | Criteria | per-bullet Max | (box) | item-total
                    #   Max | Candidate Mark.
                    # Raw tables are 6 or 8 cols = [No, Criteria, per-bullet,
                    # spacer(s), item-total, Candidate].
                    _marks = [ci for ci in range(2, ncol - 1) if _col_has(ci)]
                    _per_c = _marks[0] if _marks else 2
                    _tot_c = _marks[-1] if len(_marks) >= 2 else None
                    _sep_c = None
                    _hi = _tot_c if _tot_c is not None else (ncol - 1)
                    for ci in range(_per_c + 1, _hi):
                        _sep_c = ci
                        break
                    keep = [0, 1, _per_c, _sep_c, _tot_c, ncol - 1]
                    _mm_pos = 2  # per-bullet column position in the 6-col grid

                    t = _bordered_table(6)
                    t.autofit = False
                    t.allow_autofit = False
                    _wid = [0.5, 3.3, 0.45, 0.3, 0.5, 0.85]

                    from docx.oxml import OxmlElement
                    from docx.oxml.ns import qn as _qn2

                    def _cell_bd(cell, **edges):
                        _tcPr = cell._tc.get_or_add_tcPr()
                        _bd = _tcPr.find(_qn2('w:tcBorders'))
                        if _bd is None:
                            _bd = OxmlElement('w:tcBorders')
                            _tcPr.append(_bd)
                        for _e, _v in edges.items():
                            _el = _bd.find(_qn2('w:' + _e))
                            if _el is None:
                                _el = OxmlElement('w:' + _e)
                                _bd.append(_el)
                            if _v == 'nil':
                                _el.set(_qn2('w:val'), 'nil')
                            else:
                                _el.set(_qn2('w:val'), 'single')
                                _el.set(_qn2('w:sz'), '4')
                                _el.set(_qn2('w:color'), '000000')

                    _BUL = ('•', '\u2022', 'o ', '\uf0b7')

                    for ri, row in enumerate(data):
                        cvals = [_mg_clean((row[ci] if ci is not None else '')
                                           or '') for ci in keep]
                        # Skip fully-empty spacer rows.
                        if ri > 0 and not any(v.strip() for v in cvals):
                            continue
                        # Header row.
                        if ri == 0:
                            cells = t.add_row().cells
                            for pos in range(6):
                                try:
                                    cells[pos].width = Inches(_wid[pos])
                                except Exception:
                                    pass
                                _cell_text(cells[pos], cvals[pos].strip(),
                                           bold=True, align=CENTER, first=True)
                            continue
                        # A full-width sub-header/label row (e.g. "Graph
                        # worksheet", "Table: tbl5_1", "Query: qry5_3").
                        _is_label = (cvals[0].strip()
                                     and not any(cvals[k].strip()
                                                 for k in (1, 2, 3, 4, 5)))
                        if _is_label:
                            cells = t.add_row().cells
                            _cell_text(cells[0], cvals[0].strip(), bold=True,
                                       first=True)
                            try:
                                _r = len(t.rows) - 1
                                t.cell(_r, 0).merge(t.cell(_r, 5))
                            except Exception:
                                pass
                            continue
                        # --- Item: emit ONE Word row per logical criteria line
                        # so the box column (col 3) shows a split per mark, like
                        # the MG. Internal horizontal borders of the other
                        # columns are hidden so they read as single tall cells.
                        # Keep the criteria lines as-is (formula lines, OR
                        # separators, Concepts, and each bullet stay on their
                        # own line) — do NOT merge non-bullet lines together.
                        _cl_lines = [l.strip() for l in cvals[1].split('\n')
                                     if l.strip()] or ['']
                        _mk_vals = [l.strip() for l in cvals[2].split('\n')
                                    if l.strip()]
                        _tot = cvals[4].strip()
                        _no = cvals[0].strip()
                        # (text, is_bullet, mark) per logical criteria line.
                        _linfo = []
                        _mi = 0
                        for _cl in _cl_lines:
                            _isb = _cl.lstrip().startswith(_BUL)
                            _mk = ''
                            if _isb and _mi < len(_mk_vals):
                                _mk = _mk_vals[_mi]
                                _mi += 1
                            _linfo.append((_cl, _isb, _mk))
                        _L = len(_linfo) or 1
                        # The DBE MG divides the box column into ONE box per
                        # MARK, i.e. the item's total marks. Group the criteria
                        # lines into `_nbox` rows (ceil-first, so a heading
                        # folds in with the first mark) → `_nbox` equal boxes.
                        try:
                            _nbox = int(re.sub(r'[^0-9]', '', _tot) or '0')
                        except Exception:
                            _nbox = 0
                        _nbox = max(1, _nbox)
                        # A "Total for QUESTION N" summary row is NOT a marked
                        # item — render it as ONE plain row (no candidate-box
                        # division, no padded empty rows).
                        _first_txt = (_linfo[0][0] if _linfo else '').strip().lower()
                        if (_first_txt.startswith('total for question')
                                or _first_txt.startswith('total q')):
                            _nbox = 1
                        _groups = []
                        if _nbox >= _L:
                            _groups = [[x] for x in _linfo]
                            while len(_groups) < _nbox:
                                _groups.append([])
                        else:
                            import math as _math
                            _idx = 0
                            _rem = _L
                            for _g in range(_nbox):
                                _take = _math.ceil(_rem / (_nbox - _g))
                                _groups.append(_linfo[_idx:_idx + _take])
                                _idx += _take
                                _rem -= _take
                        _r0 = len(t.rows)
                        for _gi, _grp in enumerate(_groups):
                            cells = t.add_row().cells
                            for pos in range(6):
                                try:
                                    cells[pos].width = Inches(_wid[pos])
                                except Exception:
                                    pass
                            _cell_text(cells[0], _no if _gi == 0 else '',
                                       first=True)
                            if _grp:
                                _f = True
                                for (_txt, _isb, _mk) in _grp:
                                    _cell_text(cells[1], _txt,
                                               bold=(not _isb), first=_f)
                                    _f = False
                                _f = True
                                for (_txt, _isb, _mk) in _grp:
                                    _cell_text(cells[2], _mk, align=CENTER,
                                               first=_f)
                                    _f = False
                            else:
                                _cell_text(cells[1], '', first=True)
                                _cell_text(cells[2], '', first=True)
                            _cell_text(cells[3], '', first=True)
                            _cell_text(cells[4], _tot if _gi == 0 else '',
                                       align=CENTER, first=True)
                            _cell_text(cells[5], '', first=True)
                        _r1 = len(t.rows) - 1
                        # Hide internal horizontal borders for the unified
                        # columns (No./Criteria/per-bullet/item-total/
                        # Candidate) so they read as single tall cells; the box
                        # column (col 3) keeps its borders = one box per mark.
                        if _r1 > _r0:
                            for _c in (0, 1, 2, 4, 5):
                                for _r in range(_r0, _r1 + 1):
                                    _ed = {}
                                    if _r > _r0:
                                        _ed['top'] = 'nil'
                                    if _r < _r1:
                                        _ed['bottom'] = 'nil'
                                    if _ed:
                                        try:
                                            _cell_bd(t.cell(_r, _c), **_ed)
                                        except Exception:
                                            pass
                    # Span "Maximum Mark" across the per-bullet + box +
                    # item-total columns of the HEADER row.
                    if len(t.rows) > 0 and 'maximum' in (
                            t.cell(0, 2).text or '').lower():
                        try:
                            _merged = t.cell(0, 2).merge(t.cell(0, 4))
                            for _mp in list(_merged.paragraphs):
                                _mp._element.getparent().remove(_mp._element)
                            _np = _merged.add_paragraph()
                            _np.alignment = CENTER
                            _mr = _np.add_run('Maximum Mark')
                            _mr.bold = True
                        except Exception:
                            pass
                    rendered_any = True
            if pno < mdoc.page_count - 1 and rendered_any:
                doc.add_paragraph()
        return rendered_any

    if with_memo:
        _mg_path = None
        try:
            _title = getattr(paper, 'title', '') or ''
            _pm = re.search(r'\bP\s*([12])\b', _title, re.IGNORECASE)
            _sm = re.search(r'((?:May[-\s]?June|Nov(?:ember)?|June)\s*\d{4})',
                            _title, re.IGNORECASE)
            if _pm and _sm:
                _pn = _pm.group(1)
                _tok = re.sub(r'\s+', ' ', _sm.group(1))
                _tok = re.sub(r'November', 'Nov', _tok, flags=re.IGNORECASE)
                _yr = _tok.split()[-1]
                _mon = ' '.join(_tok.split()[:-1]).lower()
                _updir = os.path.join(app.static_folder, 'uploads')
                _best = None
                for _n in os.listdir(_updir):
                    _nl = _n.lower()
                    if not _nl.endswith('.pdf'):
                        continue
                    if f'p{_pn}' not in _nl or _yr not in _n or ' mg ' not in _nl:
                        continue
                    if _mon and _mon not in _nl:
                        continue
                    # Reject files whose CONTENT is the wrong paper (e.g. a
                    # file named "…P2…MG…" that actually holds the P1 memo).
                    _fpno = _pdf_header_pno(os.path.join(_updir, _n))
                    if _fpno is not None and _fpno != _pn:
                        continue
                    if _best is None or len(_n) < len(_best):
                        _best = _n
                if _best:
                    _cand = os.path.join(_updir, _best)
                    if os.path.isfile(_cand):
                        _mg_path = _cand
        except Exception:
            _mg_path = None
        if _mg_path and _render_mg_pdf(_mg_path):
            buf = io.BytesIO()
            doc.save(buf)
            buf.seek(0)
            return buf

    if not with_memo:
        instr = getattr(pv, 'instructions', '') or ''
        if instr.strip():
            _para('INSTRUCTIONS AND INFORMATION', bold=True, size=12)
            _render_instructions(instr)
            doc.add_page_break()

    # ---- Sections ---------------------------------------------------
    # Each QUESTION starts on its own page (universally). `_q_rendered`
    # tracks whether any question has been emitted yet so we don't create a
    # leading blank page after the instructions page.
    _q_rendered = False
    for _si, sec in enumerate(sections):
        if _q_rendered:
            doc.add_page_break()
        sec_title = _docx_strip(sec.get('title') or 'SECTION')
        if sec_title:
            _para(sec_title, bold=True, size=13, space_after=6)
        # Section-level instructions are NOT shown as a standalone block under
        # the section heading (that duplicates the auto-combined text). Like
        # the print view, they are only a FALLBACK intro for the first
        # question group that has no instructions of its own.
        sec_instr = _docx_strip(sec.get('instructions') or '')
        # The section scenario is rendered as a bordered box directly under the
        # first question's heading (see below) — not under the section title.
        sec_scn = _docx_strip(sec.get('scenario') or '')

        _first_group_seen = False
        _qgroups = sec.get('qgroups') or []
        for _gi, grp in enumerate(_qgroups):
            # `continued` chunks are pagination splits of the SAME question
            # (created for the HTML print view). They repeat the qn/title, so
            # skip the heading + intro for them — Word paginates on its own.
            _continued = bool(grp.get('continued'))
            # This chunk is the LAST piece of its question when the NEXT chunk
            # is not a continuation — the group total/outro must render only
            # here (else e.g. Q5's [35] wrongly repeats after a mid-question
            # pagination split).
            _is_last_chunk = (_gi + 1 >= len(_qgroups)
                              or not bool(_qgroups[_gi + 1].get('continued')))
            if not _continued:
                # Start every question after the first (in this section) on a
                # new page. The first question shares the page with the
                # section heading; the new-section page break is handled above.
                _is_first_grp = not _first_group_seen
                if _first_group_seen:
                    doc.add_page_break()
                qn = grp.get('qn')
                gtitle = _docx_strip(grp.get('title') or '')
                head = f'QUESTION {qn}' if qn else 'QUESTION'
                if gtitle:
                    head = f'{head}: {gtitle}'
                _para(head, bold=True, size=12, space_after=4)
                # Section scenario: a bordered box shown directly beneath the
                # first question's heading (DBE Section C layout).
                _has_scn_box = False
                if _is_first_grp and sec_scn and not with_memo:
                    _sbox = _bordered_table(1)
                    _scell = _sbox.add_row().cells[0]
                    _render_block(lambda c=_scell: _cell_para(c, first=True),
                                  sec_scn, base=0.0, justify=False, reflow=True)
                    _has_scn_box = True
                ginstr = _docx_strip(grp.get('instructions') or '')
                # First group with no own instructions falls back to the
                # section-level instructions (matches the print view) — but NOT
                # when a scenario box already conveys the section intro.
                if not ginstr and _is_first_grp and sec_instr and not _has_scn_box:
                    ginstr = sec_instr
                _first_group_seen = True
                _q_rendered = True
                if ginstr and not with_memo:
                    _render_block(lambda: doc.add_paragraph(), ginstr)

                # True/False groups: DBE "EXAMPLES:" table (the "NO mark…" note
                # is already part of the instruction text above). Rendered as a
                # real bordered Word table with QUESTION | ANSWER columns.
                if grp.get('is_tf') and not with_memo:
                    _para('EXAMPLES:', bold=True, space_after=4)
                    _tf_ex = grp.get('tf_examples') or [
                        {'q': 'Computer program instructions are executed by the __CPU__.',
                         'a': 'True'},
                        {'q': 'An __NIC__ has slots for hardware components, such as the CPU.',
                         'a': 'False, motherboard'},
                    ]
                    _et = _bordered_table(2)
                    _eh = _et.add_row().cells
                    _cell_text(_eh[0], 'QUESTION', bold=True, first=True)
                    _cell_text(_eh[1], 'ANSWER', bold=True, first=True)
                    for _ex in _tf_ex:
                        _er = _et.add_row().cells
                        _cell_text(_er[0], _docx_strip(str(_ex.get('q') or '')), first=True)
                        _cell_text(_er[1], _docx_strip(str(_ex.get('a') or '')), first=True)

            group_qs = grp.get('questions') or []
            labels = grp.get('labels') or []

            # A matching run: reproduce the DBE COLUMN A / COLUMN B table.
            _match_q = next((q for q in group_qs
                             if getattr(q, 'match_run_first', False)
                             and getattr(q, 'match_table', None)), None)

            mt = None  # per-item marks table (paper/memo); None for matching
            if with_memo:
                rows = grp.get('memo_rows') or []
                if rows:
                    mt = _new_marks_table()
                    for _ri, row in enumerate(rows):
                        lbl = (row.get('sub') or '').strip()
                        heading = _docx_strip(row.get('clean_heading') or '')
                        body = _docx_strip(row.get('clean_body') or '')
                        q = row.get('q')
                        marks = row.get('cmp_marks')
                        if not marks and q is not None:
                            marks = getattr(q, 'marks', 0) or 0
                        bc, mc = _marks_row(mt)
                        depth = lbl.count('.') if lbl else 0
                        off = 0.5
                        mb = off * max(0, depth - 1)
                        gap = Pt(10 if _ri else 2)
                        hp = _cell_para(bc, first=True)
                        if lbl:
                            _hang_line(hp, lbl, heading, mb, off, bold_marker=True)
                            text_indent = mb + off
                        else:
                            _docx_add_runs(hp, heading)
                            hp.paragraph_format.space_after = Pt(4)
                            text_indent = 0.0
                        hp.paragraph_format.space_before = gap
                        if body:
                            _render_block(lambda c=bc: c.add_paragraph(), body,
                                           base=text_indent, justify=False,
                                           reflow=False)
                        if marks:
                            mpar = _cell_text(mc, f'({marks})', align=RIGHT,
                                              first=True)
                            mpar.paragraph_format.space_before = gap
                    # Comparison tables render after their marks table so the
                    # bordered grid is not swallowed into a cell.
                    for row in rows:
                        if row.get('cmp_table'):
                            _render_cmp_table(row.get('cmp_table'))
            elif _match_q is not None:
                mtbl = getattr(_match_q, 'match_table', {}) or {}
                mrows = mtbl.get('rows') or []
                opts = mtbl.get('options') or []
                t = _bordered_table(2)
                hdr = t.add_row().cells
                _cell_text(hdr[0], 'COLUMN A', bold=True, first=True)
                _cell_text(hdr[1], 'COLUMN B', bold=True, first=True)
                body_row = t.add_row().cells
                for i, (desc, _mk) in enumerate(mrows):
                    lbl = labels[i] if i < len(labels) else str(i + 1)
                    p = _cell_para(body_row[0], first=(i == 0))
                    _hang_line(p, lbl, _docx_strip(desc), 0.0, 0.45)
                for j, (letter, term) in enumerate(opts):
                    p = _cell_para(body_row[1], first=(j == 0))
                    _hang_line(p, letter, _docx_strip(term), 0.0, 0.3)
                cnt = mtbl.get('count') or len(mrows)
                tot = mtbl.get('total_marks') or cnt
                _para(f'({cnt} x 1)   [{tot}]', align=RIGHT)
            else:
                mt = _new_marks_table()
                for idx, q in enumerate(group_qs):
                    lbl = (labels[idx] if idx < len(labels) else '').strip()
                    qtext = _docx_strip(getattr(q, 'display_text', '')
                                        or getattr(q, 'question_text', '') or '')
                    marks = getattr(q, 'marks', 0) or 0
                    segs = _segments(qtext, reflow=True) or ['']
                    bc, mc = _marks_row(mt)
                    depth = lbl.count('.') if lbl else 0
                    off = 0.5
                    mb = off * max(0, depth - 1)
                    gap = Pt(10 if idx else 2)
                    p = _cell_para(bc, first=True)
                    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    if lbl:
                        _hang_line(p, lbl, segs[0], mb, off, bold_marker=True)
                        text_indent = mb + off
                    else:
                        _docx_add_runs(p, segs[0])
                        p.paragraph_format.space_after = Pt(4)
                        p.paragraph_format.line_spacing = 1.15
                        text_indent = 0.0
                    p.paragraph_format.space_before = gap
                    for seg in segs[1:]:
                        _render_one(bc.add_paragraph(), seg, text_indent, True)
                    _add_image(bc, q)
                    # Per-item post_text (a NOTE / "Modify…" / "Save and close…"
                    # closer the PDF places BELOW the figure). Render each line
                    # below the image; if a line carries an inline "(N)" marks
                    # token, move it into the marks column of THAT row and
                    # suppress the item's own marks box (avoids a duplicate).
                    post = _docx_strip(getattr(q, 'post_text', '') or '')
                    post_segs = _segments(post, reflow=False) if post else []
                    _post_mark_re = re.compile(r'\s*\((\d+)\)\s*$')
                    _post_has_marks = any(_post_mark_re.search(ps)
                                          for ps in post_segs)
                    if marks and not _post_has_marks:
                        mpar = _cell_text(mc, f'({marks})', align=RIGHT, first=True)
                        mpar.paragraph_format.space_before = gap
                    for ps in post_segs:
                        pm = _post_mark_re.search(ps)
                        ptxt = ps[:pm.start()].rstrip() if pm else ps
                        pbc, pmc = _marks_row(mt)
                        _pp = _cell_para(pbc, first=True)
                        _pp.paragraph_format.space_before = Pt(8)
                        _render_one(_pp, ptxt, text_indent, True)
                        if pm:
                            _pm = _cell_text(pmc, f'({pm.group(1)})',
                                             align=RIGHT, first=True)
                            _pm.paragraph_format.space_before = Pt(8)

            outro = _docx_strip(grp.get('outro') or '')
            gmarks = grp.get('marks') or 0
            # The outro + question total belong at the END of the question, so
            # only emit them on the last chunk (not on mid-question pagination
            # splits, which would repeat the [N] total out of place).
            if not _is_last_chunk:
                outro = ''
                gmarks = 0
            if mt is not None:
                # Keep the outro and the question/section total in the SAME
                # marks table as the per-item rows so the total's [N] falls in
                # exactly the same column as the per-item marks above it.
                if outro:
                    obc, _omc = _marks_row(mt)
                    _render_block(lambda: _cell_para(obc, first=True), outro,
                                   base=0.0, justify=True, reflow=True)
                if gmarks:
                    _gb, _gm = _marks_row(mt)
                    tpar = _cell_text(_gm, f'[{gmarks}]', bold=True,
                                      align=RIGHT, first=True)
                    tpar.paragraph_format.space_before = Pt(6)
            else:
                # Matching group: no marks column; total already shown in the
                # "(N x 1) [N]" footer, so only the outro remains.
                if outro:
                    for ln in outro.split('\n'):
                        if ln.strip():
                            _para(ln.strip())

        # Per-section total (only for multi-section papers, e.g. CAT P2).
        if len(sections) > 1:
            _sec_letter = chr(65 + _si) if _si < 26 else str(_si + 1)
            _sm = _section_marks(sec)
            _para(f'TOTAL SECTION {_sec_letter}:   [{_sm}]', bold=True, align=RIGHT)

    # ---- Grand total at the very end --------------------------------
    _p1 = (pno == '1') or ('P1' in _title)
    _n25 = ('Nov 2025' in _title) or ('November 2025' in _title)
    _grand_label = 'TOTAL' if (_p1 or _n25) else 'GRAND TOTAL'
    if total:
        _para(f'{_grand_label}:   {total}', bold=True, align=RIGHT, size=12)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def _docx_download_name(paper, with_memo, version):
    base = re.sub(r'[^\w\- ]+', '', (paper.title or 'paper')).strip() or 'paper'
    base = base.replace('Nov ', 'November ')
    suffix = ' Memo' if with_memo else ' Paper'
    if version and version != 'current':
        suffix += f' ({version})'
    return f'{base}{suffix}.docx'


def _serve_paper_docx(paper_id, with_memo):
    paper = GeneratedPaper.query.get_or_404(paper_id)
    requested_version = (request.args.get('version') or '').strip().lower()
    version = requested_version if requested_version in (
        'current', 'original', 'moderated', 'final') else 'current'
    is_owner = paper.owner_id == current_user.id
    if not (is_owner or current_user.is_admin or _can_moderate(paper)):
        if not _can_view_paper(paper):
            abort(404)
        if not _can_print_paper(paper):
            flash('This paper has not been signed off yet, so a Word download is not available.',
                  'info')
            return redirect(url_for('teacher_papers_generated'))
    buf = _paper_to_docx(paper, with_memo=with_memo, version=version)
    return send_file(
        buf,
        as_attachment=True,
        download_name=_docx_download_name(paper, with_memo, version),
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )


@app.route('/teacher/generator/<paper_id>/download.docx')
@teacher_required
def teacher_paper_download_docx(paper_id):
    return _serve_paper_docx(paper_id, with_memo=False)


@app.route('/teacher/generator/<paper_id>/memo.docx')
@teacher_required
def teacher_paper_download_memo_docx(paper_id):
    return _serve_paper_docx(paper_id, with_memo=True)


# In-memory cache for computed paper page counts. Keyed by
# (paper_id, with_memo, version, signature) — signature is built from the
# paper fields that affect pagination so the cache invalidates on edits.
_PAPER_PAGE_COUNT_CACHE = {}


def _paper_pagination_signature(paper):
    parts = [
        paper.id,
        paper.title or '',
        paper.sections or '',
        paper.cover_authority or '',
        paper.cover_extra_note or '',
        paper.updated_at.isoformat() if getattr(paper, 'updated_at', None) else '',
    ]
    import hashlib
    h = hashlib.sha256()
    for p in parts:
        h.update(str(p).encode('utf-8', errors='ignore'))
        h.update(b'|')
    return h.hexdigest()


def _sanitize_cover_extra_note(note):
    # Verbatim rule: the cover must show exactly what the official DBE PDF
    # states (e.g. "...consists of 19 pages, an HTML tag sheet, ..."). Do not
    # strip the teacher-supplied cover note; render it as-is.
    return (note or '').strip()


def _inject_force_page_count(ctx, paper, with_memo, version):
    """Bake the exact converged page count into the render context so the
    cover line shows the right number on first paint (no JS flash).

    Skips the headless computation when the request is itself the embed /
    print render used during convergence (avoids recursion), or when the
    caller already baked `?pages=`. The result is cached so only the first
    browser visit pays the Chromium cost; later loads are instant.
    """
    try:
        if request.args.get('embed') or request.args.get('pages'):
            return
    except Exception:
        return
    try:
        ctx['force_page_count'] = _compute_paper_page_count(paper, with_memo, version)
    except Exception:
        app.logger.exception('Inline page-count computation failed; falling back to JS update')



def _paper_render_copy(paper, sanitize_cover_note=False):
    from types import SimpleNamespace
    copy = SimpleNamespace()
    try:
        cols = [c.name for c in paper.__table__.columns]
    except Exception:
        cols = []
    for col in cols:
        setattr(copy, col, getattr(paper, col, None))
    if sanitize_cover_note:
        try:
            copy.cover_extra_note = _sanitize_cover_extra_note(getattr(copy, 'cover_extra_note', ''))
        except Exception:
            pass
    return copy


def _count_pdf_pages(pdf_bytes):
    """Best-effort page count for generated PDF bytes.

    Primary path uses pypdf. If pypdf fails on a specific Chromium PDF,
    fall back to counting '/Type /Page' objects directly in raw bytes.
    """
    try:
        from pypdf import PdfReader
        n = len(PdfReader(io.BytesIO(pdf_bytes), strict=False).pages)
        if n > 0:
            return n
    except Exception:
        pass
    try:
        n = len(re.findall(rb'/Type\s*/Page\b', pdf_bytes))
        if n > 0:
            return n
    except Exception:
        pass
    return 0


def _converge_paper_pdf(page, base_url, path, version, pdf_options):
    """Iteratively render the preview page until the count baked into
    the cover (`?pages=N`) matches the PDF's actual page count.

    Returns (final_pdf_bytes, final_count). The returned PDF is the
    authoritative artifact: the cover number equals the document's
    actual length.
    """
    # Pass 0: natural render with no `pages=` baked in.
    url = f"{base_url}{path}?version={version}&embed=1&print=1"
    page.goto(url, wait_until='networkidle')
    page.emulate_media(media='print')
    pdf = page.pdf(**pdf_options)
    actual = _count_pdf_pages(pdf)
    if not actual:
        return pdf, 0

    # Iteratively bake `pages=N` and re-measure until N == actual.
    target = actual
    last_pdf = pdf
    last_actual = actual
    seen_pairs = set()  # (target, actual)
    for _ in range(8):
        url = f"{base_url}{path}?version={version}&embed=1&print=1&pages={target}"
        # Reset to screen media before navigating: layout-dependent
        # scripts in the page (e.g. the flow-memo paginator) must measure
        # against the on-screen 21cm page boxes, not the print stylesheet.
        page.emulate_media(media='screen')
        page.goto(url, wait_until='networkidle')
        page.emulate_media(media='print')
        pdf = page.pdf(**pdf_options)
        actual = _count_pdf_pages(pdf) or target
        last_pdf = pdf
        last_actual = actual
        if actual == target:
            return pdf, actual
        pair = (target, actual)
        if pair in seen_pairs:
            break
        seen_pairs.add(pair)
        target = actual

    # Final bounded attempts around the latest measured value. This handles
    # most 1-page oscillations while still preferring exact equality.
    for cand in (target, target + 1, max(1, target - 1)):
        url = f"{base_url}{path}?version={version}&embed=1&print=1&pages={cand}"
        # Reset to screen media before navigating: layout-dependent
        # scripts in the page (e.g. the flow-memo paginator) must measure
        # against the on-screen 21cm page boxes, not the print stylesheet.
        page.emulate_media(media='screen')
        page.goto(url, wait_until='networkidle')
        page.emulate_media(media='print')
        pdf = page.pdf(**pdf_options)
        actual = _count_pdf_pages(pdf) or cand
        last_pdf = pdf
        last_actual = actual
        if actual == cand:
            return pdf, actual

    # Bounded fallthrough: return the last measured PDF/count.
    return last_pdf, last_actual


def _compute_paper_page_count(paper, with_memo, version):
    """Run headless Chromium with the same iterative convergence the
    PDF download uses, so the on-screen count and the downloaded PDF
    always agree.

    Cached by paper signature so repeated screen previews are instant.
    """
    sig = _paper_pagination_signature(paper)
    key = (paper.id, bool(with_memo), version or 'current', sig)
    cached = _PAPER_PAGE_COUNT_CACHE.get(key)
    if cached is not None:
        return cached

    from playwright.sync_api import sync_playwright
    from urllib.parse import urlparse

    if with_memo:
        path = url_for('teacher_paper_memo', paper_id=paper.id)
    else:
        path = url_for('teacher_paper_preview', paper_id=paper.id)
    base_url = request.url_root.rstrip('/')

    parsed = urlparse(base_url)
    cookie_domain = parsed.hostname or 'localhost'
    cookies = []
    for name, value in request.cookies.items():
        cookies.append({'name': name, 'value': value,
                        'domain': cookie_domain, 'path': '/'})

    pdf_options = {
        'format': 'A4',
        'print_background': True,
        'margin': {'top': '0', 'right': '0', 'bottom': '0', 'left': '0'},
        'prefer_css_page_size': True,
    }

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            context = browser.new_context()
            if cookies:
                context.add_cookies(cookies)
            page = context.new_page()
            _, count = _converge_paper_pdf(
                page, base_url, path, version, pdf_options
            )
        finally:
            browser.close()

    _PAPER_PAGE_COUNT_CACHE[key] = count
    return count

@app.route('/teacher/generator/<paper_id>/page_count')
def teacher_paper_page_count(paper_id):
    paper = GeneratedPaper.query.get_or_404(paper_id)
    with_memo = (request.args.get('memo') == '1')
    version = (request.args.get('version') or 'current').strip().lower()
    if version not in ('current', 'original', 'moderated', 'final'):
        version = 'current'
    # Allow the client to force a fresh re-count (e.g. after the user
    # made edits and the cover number now looks wrong). Without this the
    # in-memory cache could keep returning a stale converged value.
    if request.args.get('refresh') == '1':
        try:
            sig = _paper_pagination_signature(paper)
            for k in list(_PAPER_PAGE_COUNT_CACHE.keys()):
                if k[0] == paper.id:
                    _PAPER_PAGE_COUNT_CACHE.pop(k, None)
        except Exception:
            pass
    is_owner = paper.owner_id == current_user.id
    if not (is_owner or current_user.is_admin or _can_moderate(paper)):
        if not _can_view_paper(paper):
            abort(404)
        if not _can_print_paper(paper):
            abort(403)
    try:
        count = _compute_paper_page_count(paper, with_memo, version)
    except Exception as e:
        app.logger.exception('Page-count computation failed')
        return jsonify({'ok': False, 'error': str(e)}), 500
    return jsonify({'ok': True, 'pages': count})


def _render_paper_pdf(paper, with_memo, version):
    """Render the paper preview HTML to a PDF using headless Chromium.

    Two-pass: the first render produces a PDF whose page count we read; the
    second render bakes that exact count into the cover line and is returned.

    The preview/memo URL on this Flask app is loaded via Playwright using the
    caller's session cookies so authentication and all relative `/static/`
    asset URLs resolve correctly.
    """
    from playwright.sync_api import sync_playwright
    from urllib.parse import urlparse

    pdf_options = {
        'format': 'A4',
        'print_background': True,
        'margin': {'top': '0', 'right': '0', 'bottom': '0', 'left': '0'},
        'prefer_css_page_size': True,
    }

    if with_memo:
        path = url_for('teacher_paper_memo', paper_id=paper.id)
    else:
        path = url_for('teacher_paper_preview', paper_id=paper.id)

    base_url = request.url_root.rstrip('/')

    parsed = urlparse(base_url)
    cookie_domain = parsed.hostname or 'localhost'
    cookies = []
    for name, value in request.cookies.items():
        cookies.append({
            'name': name,
            'value': value,
            'domain': cookie_domain,
            'path': '/',
        })

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            context = browser.new_context()
            if cookies:
                context.add_cookies(cookies)
            page = context.new_page()
            current_pdf, final_count = _converge_paper_pdf(
                page, base_url, path, version, pdf_options
            )
            # Stash the final count in the page-count cache so the screen
            # preview's "consists of N pages" line matches the downloaded
            # PDF exactly.
            try:
                sig = _paper_pagination_signature(paper)
                key = (paper.id, bool(with_memo), version or 'current', sig)
                _PAPER_PAGE_COUNT_CACHE[key] = final_count
            except Exception:
                pass
            return current_pdf
        finally:
            browser.close()


def _paper_pdf_filename(paper, with_memo):
    title = (paper.title or 'paper').strip()
    safe = re.sub(r'[^A-Za-z0-9._-]+', '_', title).strip('_') or 'paper'
    suffix = 'memo' if with_memo else 'paper'
    return f'{safe}_{suffix}.pdf'


def _generated_pdf_response(pdf_bytes, filename):
    response = send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=False,
        download_name=filename,
        conditional=False,
        max_age=0,
    )
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/teacher/generator/<paper_id>/pdf')
@teacher_required
def teacher_paper_pdf(paper_id):
    paper = GeneratedPaper.query.get_or_404(paper_id)
    requested_version = (request.args.get('version') or '').strip().lower()
    if requested_version:
        version = requested_version
    else:
        if ((paper.moderation_status or '') in ('rejected', 'signed_off')
                and (paper.sections_original or '').strip()):
            version = 'moderated'
        else:
            version = 'current'
    if version not in ('current', 'original', 'moderated', 'final'):
        version = 'current'
    is_owner = paper.owner_id == current_user.id
    if not (is_owner or current_user.is_admin or _can_moderate(paper)):
        if not _can_view_paper(paper):
            abort(404)
        if not _can_print_paper(paper):
            abort(403)
    try:
        pdf_bytes = _render_paper_pdf(paper, with_memo=False, version=version)
    except Exception as e:
        app.logger.exception('PDF generation failed')
        return Response(f'PDF generation failed: {e}', status=500)
    return _generated_pdf_response(
        pdf_bytes,
        _paper_pdf_filename(paper, with_memo=False),
    )


@app.route('/teacher/generator/<paper_id>/memo/pdf')
@teacher_required
def teacher_paper_memo_pdf(paper_id):
    paper = GeneratedPaper.query.get_or_404(paper_id)
    requested_version = (request.args.get('version') or '').strip().lower()
    if requested_version:
        version = requested_version
    else:
        if ((paper.moderation_status or '') in ('rejected', 'signed_off')
                and (paper.sections_original or '').strip()):
            version = 'moderated'
        else:
            version = 'current'
    if version not in ('current', 'original', 'moderated', 'final'):
        version = 'current'
    is_owner = paper.owner_id == current_user.id
    if not (is_owner or current_user.is_admin or _can_moderate(paper)):
        if not _can_view_paper(paper):
            abort(404)
        if not _can_print_paper(paper):
            abort(403)
    try:
        pdf_bytes = _render_paper_pdf(paper, with_memo=True, version=version)
    except Exception as e:
        app.logger.exception('Memo PDF generation failed')
        return Response(f'PDF generation failed: {e}', status=500)
    return _generated_pdf_response(
        pdf_bytes,
        _paper_pdf_filename(paper, with_memo=True),
    )


def _can_print_paper(paper):
    """Print/preview is gated behind HOD sign-off.

    Allowed when the paper is signed off, when the viewer is an admin, or
    when the viewer is the assigned moderator (so HODs can preview before
    signing off).
    """
    if paper.moderation_status == 'signed_off':
        return True
    if not current_user.is_authenticated:
        return False
    if current_user.is_admin:
        return True
    if current_user.is_hod and paper.moderator_id == current_user.id:
        return True
    return False


# ---------- Instruction templates (per-teacher saved instructions) -------
# Instructions taken verbatim from DBE NSC question papers (Computer
# Applications Technology, Grade 12). Grouped by usage so teachers can pick
# the right block for the paper / section they are building.
INSTRUCTION_LIBRARY = {
    # ---- Paper 2 (Theory) cover -- exact DBE wording (12 items). Item 1 has
    # an indented sub-list of section marks (rendered as continuation
    # paragraphs by paper_print.html).
    "Paper 2 — Theory (cover instructions)": [
        "This question paper consists of:\nSECTION A (25)\nSECTION B (75)\nSECTION C (50)",
        "Answer ALL the questions.",
        "Number the answers correctly according to the numbering system used in this question paper.",
        "Start EACH question on a NEW page.",
        "Do NOT write in the right-hand margin of the ANSWER BOOK.",
        "Leave a line after EACH subquestion.",
        "Generally, one mark is allocated per fact; therefore, a 2-mark question would require TWO facts, etc.",
        "Read the questions carefully. Do NOT give more answers than the question requires as it will NOT be marked.",
        "All answers MUST be related to Computer Applications Technology.",
        "Unless otherwise specified, answers such as 'cheaper', 'slower'/'faster', etc. will NOT be accepted.",
        "Do NOT use brand names in your answers, unless specifically required.",
        "Write neatly and legibly.",
    ],
    # ---- Paper 1 (Practical) cover -- exact DBE wording (20 items).
    # Item 20 has a "Do the following:" sub-list whose lines start with
    # the bullet character so paper_print.html renders them as <ul>.
    "Paper 1 — Practical (cover instructions)": [
        "Owing to the nature of this practical examination, it is important to note that, even if you complete the examination early, you will NOT be permitted to leave the examination room until all the administrative tasks associated with the examination have been finalised. During the examination, the standard examination rules regarding leaving the examination room apply.",
        "If you are working on the network, or the data files have been preloaded on your system, you must follow the instructions provided by the invigilator/teacher.",
        "At the end of the examination, you must make sure that ALL your answer files are saved on the network/computer as explained to you by the invigilator/teacher.",
        "Make absolutely sure that all files can be read. Do NOT save unnecessary files/folders and do NOT hand in duplicate answer files/folders. Do NOT delete any original files that you did not work on.",
        "The information sheet that has been provided with the question paper MUST BE COMPLETED AFTER THE THREE-HOUR EXAMINATION SESSION. Hand it to the invigilator at the end of the examination.",
        "A copy of the master files will be available from the invigilator. Should there be any problems with a file, you may request another copy from the invigilator.",
        "This question paper consists of SEVEN questions. Answer ALL the questions.",
        "Read through each question before answering or solving the problem. Do NOT do more than is required by the question.",
        "Ensure that you save each document using the file name given in the question paper. Save your work regularly as a precaution against possible power failures.",
        "You may NOT use any resource material.",
        "Accuracy will be taken into account.",
        "Ensure that the regional settings are set to South Africa and date and time settings, number settings and currency settings are correctly set.",
        "In all questions involving word processing, you should set the language to English (South Africa). The paper size is assumed to be A4 Portrait, unless instructed otherwise. Use centimetres as the unit of measurement.",
        "Ensure that the Developer tab and Ruler are activated.",
        "Ensure that the decimal symbol is set as a full stop ('.') and the list separator is set as a comma (',').",
        "Formulae and/or functions must be used for ALL calculations in questions involving spreadsheets. Use absolute cell references only where necessary to ensure that formulae are correct when you copy them to other cells in a spreadsheet.\nNOTE: All formulae and/or functions should be inserted in such a manner that the correct results will still be obtained even if changes are made to the existing data.",
        "You may NOT use a word processing program such as Word to answer the HTML question.",
        "Borders around images or screenshots in this question paper are intended for clarity. Do NOT insert borders unless you are instructed to do so.",
        "The examination data folder that you receive with this question paper contains the files listed below. Ensure that you have all the files before you begin with this examination.\n• **1Poster**\tZipped file\n• **1Tourism**\tWord processing file\n• **2Competition**\tWord processing file\n• **3Tourists**\tSpreadsheet\n• **4Sightings**\tSpreadsheet\n• **5Bookings**\tDatabase\n• **5Logo**\tImage\n• **6_1Beach**\tImage\n• **6_1Dolphin**\tHTML file\n• **6_2Flamingo**\tImage\n• **6_2Heritage**\tHTML file\n• **7BigFive**\tSpreadsheet\n• **7Map**\tWord processing file\n• **7Travellers**\tSpreadsheet\n• **7TravelMode**\tDatabase",
    ],
    "Section A — Multiple-choice": [
        "Various options are given as possible answers to the following questions. Choose the answer and write only the letter (A—D) next to the question numbers (1.1 to 1.10) in the ANSWER BOOK, e.g. 1.11 D.",
    ],
    "Section A — Matching items": [
        "Choose a term/concept from COLUMN B that matches the description in COLUMN A. Write only the letter (A—T) next to the question numbers (2.1 to 2.10) in the ANSWER BOOK, e.g. 2.11 U.",
        "Only ONE answer per question is allowed.",
    ],
    "Section A — True/False items": [
        "Indicate whether the following statements are TRUE or FALSE. Write 'true' or 'false' next to the question numbers (3.1 to 3.5) in the ANSWER BOOK.",
        "Correct the statement if it is FALSE by changing the underlined word(s) to make the statement TRUE. (Do NOT simply use the word 'NOT' to change the statement.)",
        "NO mark will be awarded if only FALSE is written.",
    ],
    "Section C — Integrated Scenario": [
        "The questions in this section are based on the scenario given below. Read the scenario carefully before attempting to answer the questions.",
        "Answer ALL the questions in this section.",
    ],
    "Web development (HTML)": [
        "An information sheet with HTML tags is provided as Annexure A.",
        "A text editor (e.g. Notepad++) MUST be used to answer the web development question.",
        "ANY HTML QUESTION ANSWERED USING A WORD PROCESSOR OR OTHER WEB DESIGN SOFTWARE (e.g. Dreamweaver, Wix, WordPress) WILL NOT BE MARKED.",
        "All changes made to web pages must be saved before the file is closed.",
    ],
    "Databases": [
        "An input mask character sheet is provided as Annexure B.",
        "Save the database after each subquestion to ensure that no work is lost.",
        "Do NOT add or remove records from the table unless asked to do so.",
    ],
    "General conduct & equipment": [
        "Write your name/examination number on every page of the ANSWER BOOK.",
        "The use of cell phones, smart watches or any other electronic devices is NOT permitted in the examination room.",
        "You may NOT borrow stationery or equipment from other candidates.",
        "Approved non-programmable, non-graphical scientific calculators may be used unless stated otherwise.",
        "Show ALL calculations and round answers to TWO decimal places where applicable.",
        "Diagrams are NOT necessarily drawn to scale.",
        "No marks will be awarded for answers that are NOT motivated, where required.",
        "Use a black or blue pen only. Pencil may only be used for diagrams.",
    ],
}

# Flattened list kept for backward compatibility with older clients of the
# /teacher/instruction-templates endpoint.
DEFAULT_INSTRUCTIONS = [text for group in INSTRUCTION_LIBRARY.values() for text in group]


@app.route('/teacher/instruction-templates', methods=['GET'])
@teacher_required
def teacher_instruction_templates_list():
    rows = (InstructionTemplate.query
            .filter_by(owner_id=current_user.id)
            .order_by(InstructionTemplate.created_at.desc()).all())
    # JSON response for API / AJAX callers
    if (request.accept_mimetypes.best_match(['application/json', 'text/html']) == 'application/json'
            or request.args.get('fmt') == 'json'):
        return jsonify({
            'defaults': DEFAULT_INSTRUCTIONS,
            'categories': [
                {'name': name, 'items': items}
                for name, items in INSTRUCTION_LIBRARY.items()
            ],
            'mine': [{'id': r.id, 'text': r.text} for r in rows],
        })
    categories = [{'name': name, 'instructions': items} for name, items in INSTRUCTION_LIBRARY.items()]
    return render_template('teacher/instruction_templates.html',
                           categories=categories,
                           my_templates=rows)


@app.route('/teacher/instruction-templates', methods=['POST'])
@teacher_required
def teacher_instruction_templates_create():
    text = (request.json or request.form).get('text', '').strip()
    if not text:
        return jsonify({'ok': False, 'error': 'Text is required'}), 400
    if len(text) > 1000:
        return jsonify({'ok': False, 'error': 'Too long (max 1000 chars)'}), 400
    # de-dup against this teacher's existing list
    existing = InstructionTemplate.query.filter_by(owner_id=current_user.id, text=text).first()
    if existing:
        return jsonify({'ok': True, 'id': existing.id, 'text': existing.text, 'duplicate': True})
    row = InstructionTemplate(owner_id=current_user.id, text=text)
    db.session.add(row)
    db.session.commit()
    return jsonify({'ok': True, 'id': row.id, 'text': row.text})


@app.route('/teacher/instruction-templates/<tid>', methods=['DELETE'])
@teacher_required
def teacher_instruction_templates_delete(tid):
    row = InstructionTemplate.query.get_or_404(tid)
    if row.owner_id != current_user.id and not current_user.is_admin:
        abort(403)
    db.session.delete(row)
    db.session.commit()
    return jsonify({'ok': True})


# ---------- Schedule / year planner -------------------------------------
@app.route('/teacher/planner')
@teacher_required
def teacher_planner():
    year = request.args.get('year', type=int) or 2026
    grade = request.args.get('grade', type=int) or 12
    if grade not in (10, 11, 12):
        grade = 12
    items = (TeacherSchedule.query.filter_by(owner_id=current_user.id)
             .filter(db.extract('year', TeacherSchedule.start_date) == year)
             .order_by(TeacherSchedule.start_date).all())
    by_term = {1: [], 2: [], 3: [], 4: [], 0: []}
    for it in items:
        by_term.setdefault(it.term or 0, []).append(it)
    return render_template('teacher/planner.html', items=items,
                           by_term=by_term, year=year, grade=grade)


@app.route('/teacher/planner/new', methods=['GET', 'POST'])
@app.route('/teacher/planner/<item_id>/edit', methods=['GET', 'POST'])
@teacher_required
def teacher_planner_edit(item_id=None):
    item = TeacherSchedule.query.get_or_404(item_id) if item_id else None
    if item and item.owner_id != current_user.id and not current_user.is_admin: abort(403)
    if request.method == 'POST':
        if not item:
            item = TeacherSchedule(owner_id=current_user.id,
                                   start_date=datetime.utcnow().date())
            db.session.add(item)
        item.title = request.form.get('title', '').strip()
        item.description = request.form.get('description', '').strip()
        item.grade = request.form.get('grade', type=int)
        item.kind = request.form.get('kind', 'lesson')
        item.term = request.form.get('term', type=int)
        item.color = request.form.get('color', '#0078D4')
        sd = request.form.get('start_date', '').strip()
        ed = request.form.get('end_date', '').strip()
        if sd: item.start_date = datetime.strptime(sd, '%Y-%m-%d').date()
        item.end_date = datetime.strptime(ed, '%Y-%m-%d').date() if ed else None
        if not item.title:
            flash('Title required.', 'danger')
        else:
            db.session.commit(); flash('Saved.', 'success')
            return redirect(url_for('teacher_planner'))
    return render_template('teacher/planner_edit.html', item=item)


@app.route('/teacher/planner/<item_id>/delete', methods=['POST'])
@teacher_required
def teacher_planner_delete(item_id):
    item = TeacherSchedule.query.get_or_404(item_id)
    if item.owner_id != current_user.id and not current_user.is_admin: abort(403)
    db.session.delete(item); db.session.commit()
    flash('Removed.', 'info')
    return redirect(url_for('teacher_planner'))


# =====================================================================
#  ADMIN ROUTES
# =====================================================================
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated: abort(403)
        # Staff only: super admin (owner), admin, HOD, or teacher.
        # Plain students are never allowed into the admin area.
        if not (getattr(current_user, 'is_super_admin', False)
                or current_user.is_admin
                or getattr(current_user, 'is_hod', False)
                or current_user.is_teacher):
            abort(403)
        return f(*args, **kwargs)
    return decorated


def super_admin_required(f):
    """Owner-only routes. Only the super admin may modify other staff."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_super_admin', False):
            abort(403)
        return f(*args, **kwargs)
    return decorated

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    if getattr(current_user, 'is_super_admin', False):
        user_count = User.query.count()
    elif getattr(current_user, 'is_hod', False):
        user_count = User.query.filter(db.or_(
            User.id == current_user.id,
            User.hod_id == current_user.id,
        )).count()
    elif current_user.is_admin:
        user_count = User.query.count()
    else:
        user_count = 1
    stats = {'users': user_count}
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_user_new():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        first_name = (request.form.get('first_name') or '').strip()
        last_name = (request.form.get('last_name') or '').strip()
        password = request.form.get('password') or ''
        role = (request.form.get('role') or 'teacher').strip().lower()
        grade = (request.form.get('grade') or '').strip() or None
        school_name = (request.form.get('school_name') or '').strip()
        subjects_raw = request.form.getlist('subjects')
        if not subjects_raw:
            subjects_raw = [request.form.get('subjects', '')]
        subjects_list = []
        for s in subjects_raw:
            for part in (s or '').split(','):
                part = part.strip()
                if part:
                    subjects_list.append(part)
        subjects_csv = ','.join(subjects_list)

        if not username or not email or not password:
            flash('Username, email and password are required.', 'danger')
            return render_template('admin/user_new.html', form=request.form)
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('admin/user_new.html', form=request.form)
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return render_template('admin/user_new.html', form=request.form)
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('admin/user_new.html', form=request.form)

        is_super = False
        is_admin_flag = False
        is_hod = False
        is_teacher = False
        if role == 'super_admin':
            if not getattr(current_user, 'is_super_admin', False):
                flash('Only the super admin can create another super admin.', 'danger')
                return render_template('admin/user_new.html', form=request.form)
            is_super = True; is_admin_flag = True
        elif role == 'admin':
            is_admin_flag = True
        elif role == 'hod':
            is_hod = True; is_teacher = True
        elif role == 'student':
            pass
        else:
            is_teacher = True

        user = User(
            username=username, email=email,
            first_name=first_name, last_name=last_name,
            grade=grade, school_name=school_name, subjects=subjects_csv,
            is_super_admin=is_super, is_admin=is_admin_flag,
            is_hod=is_hod, is_teacher=is_teacher,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(f'User {username} created.', 'success')
        return redirect(url_for('admin_user_profile', user_id=user.id))
    return render_template('admin/user_new.html', form={})

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    # Scope:
    #  - Super admin: see all staff.
    #  - HOD (even if also flagged Admin): only themselves + their department teachers.
    #  - Admin (non-HOD): see all staff.
    #  - Plain teacher: see only themselves.
    if getattr(current_user, 'is_super_admin', False):
        # Super admin sees every user in the system.
        users = User.query.order_by(User.created_at.desc()).all()
    elif getattr(current_user, 'is_hod', False):
        users = (User.query
                 .filter(db.or_(
                     User.id == current_user.id,
                     User.hod_id == current_user.id,
                 ))
                 .order_by(User.created_at.desc())
                 .all())
    elif current_user.is_admin:
        users = (User.query
                 .filter(db.or_(
                     User.is_super_admin == True,
                     User.is_admin == True,
                     User.is_hod == True,
                     User.is_teacher == True,
                 ))
                 .order_by(User.created_at.desc())
                 .all())
    else:
        users = [current_user]
    return render_template('admin/users.html', users=users)

@app.route('/admin/user/<user_id>/toggle-admin', methods=['POST'])
@login_required
@super_admin_required
def admin_toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_super_admin:
        flash('The super admin role cannot be changed here.', 'danger')
        return redirect(url_for('admin_user_profile', user_id=user.id))
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f'{"Admin granted" if user.is_admin else "Admin revoked"} for {user.username}.','success')
    return redirect(url_for('admin_user_profile', user_id=user.id))

@app.route('/admin/user/<user_id>/toggle-teacher', methods=['POST'])
@login_required
@super_admin_required
def admin_toggle_teacher(user_id):
    user = User.query.get_or_404(user_id)
    user.is_teacher = not bool(user.is_teacher)
    db.session.commit()
    flash(f'{"Teacher access granted" if user.is_teacher else "Teacher access revoked"} for {user.username}.','success')
    return redirect(url_for('admin_user_profile', user_id=user.id))

@app.route('/admin/user/<user_id>/toggle-hod', methods=['POST'])
@login_required
@super_admin_required
def admin_toggle_hod(user_id):
    user = User.query.get_or_404(user_id)
    user.is_hod = not bool(getattr(user, 'is_hod', False))
    db.session.commit()
    flash(f'{"HOD access granted" if user.is_hod else "HOD access revoked"} for {user.username}.','success')
    return redirect(url_for('admin_user_profile', user_id=user.id))


@app.route('/admin/user/<user_id>/toggle-subscription', methods=['POST'])
@login_required
@super_admin_required
def admin_toggle_subscription(user_id):
    user = User.query.get_or_404(user_id)
    user.subscription_active = not bool(getattr(user, 'subscription_active', False))
    db.session.commit()
    flash(
        f'{"Subscription activated" if user.subscription_active else "Subscription deactivated"} for {user.username}.',
        'success'
    )
    return redirect(url_for('admin_user_profile', user_id=user.id))


@app.route('/admin/user/<user_id>')
@login_required
@admin_required
def admin_user_profile(user_id):
    user = User.query.get_or_404(user_id)
    # Access control:
    #  - Super admin: any staff profile.
    #  - HOD (even if also Admin): only themselves or a teacher in their department.
    #  - Admin (non-HOD): any staff profile.
    #  - Plain teacher: only themselves.
    if getattr(current_user, 'is_super_admin', False):
        pass
    elif getattr(current_user, 'is_hod', False):
        if user.id != current_user.id and getattr(user, 'hod_id', None) != current_user.id:
            abort(403)
    elif current_user.is_admin:
        pass
    else:
        if user.id != current_user.id:
            abort(403)
    return render_template('admin/user_profile.html', user=user)


@app.route('/admin/user/<user_id>/update', methods=['POST'])
@login_required
@admin_required
def admin_user_update(user_id):
    user = User.query.get_or_404(user_id)
    # Permission:
    #  - Anyone may edit their OWN personal info (name, username, email, grade).
    #  - Super admin may edit anyone.
    #  - HOD may edit teachers in their department.
    #  - Admin (non-HOD) may edit anyone.
    is_self = (user.id == current_user.id)
    is_super = bool(getattr(current_user, 'is_super_admin', False))
    is_hod = bool(getattr(current_user, 'is_hod', False))
    if not is_self and not is_super:
        if is_hod:
            if getattr(user, 'hod_id', None) != current_user.id:
                abort(403)
        elif not current_user.is_admin:
            abort(403)
    # Role/status fields (is_admin, is_hod, is_super_admin, is_teacher) are NOT editable here.
    username = (request.form.get('username') or '').strip()
    email = (request.form.get('email') or '').strip()
    first_name = (request.form.get('first_name') or '').strip()
    last_name = (request.form.get('last_name') or '').strip()
    grade_raw = (request.form.get('grade') or '').strip()

    if not username or not email:
        flash('Username and email are required.', 'danger')
        return redirect(url_for('admin_user_profile', user_id=user.id))

    clash = User.query.filter(User.username == username, User.id != user.id).first()
    if clash:
        flash('That username is already taken.', 'danger')
        return redirect(url_for('admin_user_profile', user_id=user.id))
    clash = User.query.filter(User.email == email, User.id != user.id).first()
    if clash:
        flash('That email is already in use.', 'danger')
        return redirect(url_for('admin_user_profile', user_id=user.id))

    user.username = username
    user.email = email
    user.first_name = first_name
    user.last_name = last_name
    try:
        user.grade = int(grade_raw) if grade_raw else None
    except ValueError:
        user.grade = None
    db.session.commit()
    flash('Profile updated.', 'success')
    return redirect(url_for('admin_user_profile', user_id=user.id))


@app.route('/admin/user/<user_id>/password', methods=['POST'])
@login_required
@admin_required
def admin_user_password(user_id):
    user = User.query.get_or_404(user_id)
    is_self = (user.id == current_user.id)
    is_super = bool(getattr(current_user, 'is_super_admin', False))
    is_hod = bool(getattr(current_user, 'is_hod', False))
    if not is_self and not is_super:
        if is_hod:
            if getattr(user, 'hod_id', None) != current_user.id:
                abort(403)
        elif not current_user.is_admin:
            abort(403)
    pw = request.form.get('password') or ''
    pw2 = request.form.get('password_confirm') or ''
    if len(pw) < 6:
        flash('Password must be at least 6 characters.', 'danger')
        return redirect(url_for('admin_user_profile', user_id=user.id))
    if pw != pw2:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('admin_user_profile', user_id=user.id))
    user.set_password(pw)
    db.session.commit()
    flash('Password updated.', 'success')
    return redirect(url_for('admin_user_profile', user_id=user.id))


@app.route('/admin/user/<user_id>/avatar', methods=['POST'])
@login_required
@admin_required
def admin_user_avatar(user_id):
    user = User.query.get_or_404(user_id)
    is_self = (user.id == current_user.id)
    is_super = bool(getattr(current_user, 'is_super_admin', False))
    is_hod = bool(getattr(current_user, 'is_hod', False))
    if not is_self and not is_super:
        if is_hod:
            if getattr(user, 'hod_id', None) != current_user.id:
                abort(403)
        elif not current_user.is_admin:
            abort(403)
    f = request.files.get('avatar')
    if not f or not f.filename:
        flash('Please choose an image to upload.', 'danger')
        return redirect(url_for('admin_user_profile', user_id=user.id))
    rel, _size = _save_upload(f, 'avatars', TEACHER_LOGO_EXTS)
    if not rel:
        flash('Unsupported image type. Use PNG, JPG, GIF, WEBP or SVG.', 'danger')
        return redirect(url_for('admin_user_profile', user_id=user.id))
    # Best-effort cleanup of the previous avatar file
    old = (user.profile_pic or '').strip()
    if old:
        try:
            old_abs = os.path.join('static', old)
            if os.path.exists(old_abs):
                os.remove(old_abs)
        except Exception:
            pass
    user.profile_pic = rel
    db.session.commit()
    flash('Profile picture updated.', 'success')
    return redirect(url_for('admin_user_profile', user_id=user.id))


@app.route('/admin/user/<user_id>/toggle-block', methods=['POST'])
@login_required
@super_admin_required
def admin_toggle_block(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot block your own account.', 'danger')
        return redirect(url_for('admin_user_profile', user_id=user.id))
    if user.is_super_admin:
        flash('The super admin account cannot be blocked.', 'danger')
        return redirect(url_for('admin_user_profile', user_id=user.id))
    user.is_blocked = not bool(user.is_blocked)
    db.session.commit()
    flash(f'{"Account blocked" if user.is_blocked else "Account unblocked"} for {user.username}.', 'success')
    return redirect(url_for('admin_user_profile', user_id=user.id))


@app.route('/admin/user/<user_id>/delete', methods=['POST'])
@login_required
@super_admin_required
def admin_user_delete(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin_user_profile', user_id=user.id))
    if user.is_super_admin:
        flash('The owner account cannot be deleted.', 'danger')
        return redirect(url_for('admin_user_profile', user_id=user.id))
    confirm = (request.form.get('confirm_username') or '').strip()
    if confirm != user.username:
        flash('Type the exact username to confirm deletion.', 'danger')
        return redirect(url_for('admin_user_profile', user_id=user.id))
    # Best-effort cleanup of avatar file
    try:
        old = (user.profile_pic or '').strip()
        if old:
            old_abs = os.path.join('static', old)
            if os.path.exists(old_abs):
                os.remove(old_abs)
    except Exception:
        pass
    uname = user.username
    try:
        db.session.delete(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Could not delete {uname}: this user has linked records. Block the account instead. ({type(e).__name__})', 'danger')
        return redirect(url_for('admin_user_profile', user_id=user.id))
    flash(f'User {uname} has been deleted.', 'success')
    return redirect(url_for('admin_users'))

# =====================================================================
#  ERROR HANDLERS
# =====================================================================
@app.errorhandler(404)
def not_found(e): return render_template('error.html', error_code=404, error_message='Page not found'), 404
@app.errorhandler(403)
def forbidden(e): return render_template('error.html', error_code=403, error_message='Access denied'), 403
@app.errorhandler(500)
def server_error(e): return render_template('error.html', error_code=500, error_message='Server error'), 500

# =====================================================================
#  SEED DATA
# =====================================================================
def seed_data():
    grades_data = [
        {'number':10,'name':'Grade 10','description':'Computer Applications Technology — CAPS Grade 10'},
        {'number':11,'name':'Grade 11','description':'Computer Applications Technology — CAPS Grade 11'},
        {'number':12,'name':'Grade 12','description':'Computer Applications Technology — CAPS Grade 12'},
    ]
    for gd in grades_data:
        if not Grade.query.filter_by(number=gd['number']).first():
            db.session.add(Grade(**gd))
    db.session.commit()

def init_db(seed_demo_users=True):
    with app.app_context():
        db.create_all()
        # Lightweight in-place migration: add columns introduced after the
        # initial schema was deployed. Safe to run on every startup.
        from sqlalchemy import inspect, text
        try:
            insp = inspect(db.engine)
            cols = {c['name'] for c in insp.get_columns('question_bank_items')}
            if 'image_path' not in cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE question_bank_items ADD COLUMN image_path VARCHAR(400) DEFAULT ''"
                    ))
                print("Migrated: question_bank_items.image_path added")
            if 'image_width' not in cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE question_bank_items ADD COLUMN image_width INTEGER DEFAULT 0"
                    ))
                print("Migrated: question_bank_items.image_width added")
            if 'image_offset' not in cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE question_bank_items ADD COLUMN image_offset INTEGER DEFAULT 0"
                    ))
                print("Migrated: question_bank_items.image_offset added")
            if 'subject' not in cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE question_bank_items ADD COLUMN subject VARCHAR(120) DEFAULT ''"
                    ))
                print("Migrated: question_bank_items.subject added")
            if 'share_scope' not in cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE question_bank_items ADD COLUMN share_scope VARCHAR(20) DEFAULT 'private'"
                    ))
                    # Back-fill from legacy is_shared flag so previously-shared items remain public.
                    conn.execute(text(
                        "UPDATE question_bank_items SET share_scope='public' WHERE is_shared=1"
                    ))
                print("Migrated: question_bank_items.share_scope added (back-filled from is_shared)")
            gp_cols = {c['name'] for c in insp.get_columns('generated_papers')}
            if 'share_scope' not in gp_cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE generated_papers ADD COLUMN share_scope VARCHAR(20) DEFAULT 'private'"
                    ))
                print("Migrated: generated_papers.share_scope added")
            if 'data_files' not in gp_cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE generated_papers ADD COLUMN data_files TEXT DEFAULT ''"
                    ))
                print("Migrated: generated_papers.data_files added")
            if 'preview_overrides' not in gp_cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE generated_papers ADD COLUMN preview_overrides TEXT DEFAULT ''"
                    ))
                print("Migrated: generated_papers.preview_overrides added")
            if 'edit_history' not in gp_cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE generated_papers ADD COLUMN edit_history TEXT DEFAULT ''"
                    ))
                print("Migrated: generated_papers.edit_history added")
            if 'is_library' not in gp_cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE generated_papers ADD COLUMN is_library BOOLEAN DEFAULT 0"
                    ))
                    # Back-fill: every paper that already exists (and is not a
                    # user clone) is part of the seeded official library, so
                    # protect it from deletion. Clones stay deletable.
                    conn.execute(text(
                        "UPDATE generated_papers SET is_library = 1 "
                        "WHERE LOWER(COALESCE(title, '')) NOT LIKE 'copy of %'"
                    ))
                print("Migrated: generated_papers.is_library added (back-filled existing papers as library)")
            user_cols = {c['name'] for c in insp.get_columns('users')}
            if 'is_blocked' not in user_cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN is_blocked BOOLEAN DEFAULT 0"
                    ))
                print("Migrated: users.is_blocked added")
            if 'is_hod' not in user_cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN is_hod BOOLEAN DEFAULT 0"
                    ))
                print("Migrated: users.is_hod added")
            # Back-fill: every HOD must also be flagged as a teacher so the
            # teacher_required decorator lets them into the workspace.
            with db.engine.begin() as conn:
                conn.execute(text(
                    "UPDATE users SET is_teacher=1 WHERE is_hod=1 AND (is_teacher IS NULL OR is_teacher=0)"
                ))
            if 'is_super_admin' not in user_cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN is_super_admin BOOLEAN DEFAULT 0"
                    ))
                print("Migrated: users.is_super_admin added")
            if 'profile_pic' not in user_cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN profile_pic VARCHAR(400) DEFAULT ''"
                    ))
                print("Migrated: users.profile_pic added")
            if 'school_name' not in user_cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN school_name VARCHAR(200) DEFAULT ''"
                    ))
                print("Migrated: users.school_name added")
            for _col, _ddl in (
                ('school_district', "ALTER TABLE users ADD COLUMN school_district VARCHAR(200) DEFAULT ''"),
                ('province',        "ALTER TABLE users ADD COLUMN province VARCHAR(50) DEFAULT ''"),
                ('town',            "ALTER TABLE users ADD COLUMN town VARCHAR(120) DEFAULT ''"),
                ('suburb',          "ALTER TABLE users ADD COLUMN suburb VARCHAR(120) DEFAULT ''"),
                ('subjects',        "ALTER TABLE users ADD COLUMN subjects VARCHAR(400) DEFAULT ''"),
            ):
                if _col not in user_cols:
                    with db.engine.begin() as conn:
                        conn.execute(text(_ddl))
                    print(f"Migrated: users.{_col} added")
            if 'hod_id' not in user_cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN hod_id VARCHAR(36)"
                    ))
                print("Migrated: users.hod_id added")
            if 'subscription_active' not in user_cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN subscription_active BOOLEAN DEFAULT 0"
                    ))
                print("Migrated: users.subscription_active added")
            paper_cols = {c['name'] for c in insp.get_columns('generated_papers')}
            if 'moderation_status' not in paper_cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE generated_papers ADD COLUMN moderation_status VARCHAR(20) DEFAULT 'draft'"
                    ))
                print("Migrated: generated_papers.moderation_status added")
            if 'moderator_id' not in paper_cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE generated_papers ADD COLUMN moderator_id VARCHAR(36)"
                    ))
                print("Migrated: generated_papers.moderator_id added")
            if 'moderator_notes' not in paper_cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE generated_papers ADD COLUMN moderator_notes TEXT DEFAULT ''"
                    ))
                print("Migrated: generated_papers.moderator_notes added")
            if 'flagged_at' not in paper_cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE generated_papers ADD COLUMN flagged_at DATETIME"
                    ))
                print("Migrated: generated_papers.flagged_at added")
            if 'signed_off_at' not in paper_cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE generated_papers ADD COLUMN signed_off_at DATETIME"
                    ))
                print("Migrated: generated_papers.signed_off_at added")
            for _vcol in ('sections_original', 'sections_moderated', 'sections_final'):
                if _vcol not in paper_cols:
                    with db.engine.begin() as conn:
                        conn.execute(text(
                            f"ALTER TABLE generated_papers ADD COLUMN {_vcol} TEXT DEFAULT ''"
                        ))
                    print(f"Migrated: generated_papers.{_vcol} added")
            for _vcol in ('header_original', 'moderator_overrides', 'sections_undo_stack'):
                if _vcol not in paper_cols:
                    with db.engine.begin() as conn:
                        conn.execute(text(
                            f"ALTER TABLE generated_papers ADD COLUMN {_vcol} TEXT DEFAULT ''"
                        ))
                    print(f"Migrated: generated_papers.{_vcol} added")
        except Exception as _mig_err:
            print(f"Schema migration error: {_mig_err}")
            raise  # Re-raise so we see the actual error
        
        # ---- Bootstrap & Backfill (now safe after migrations) ----
        try:
            # Bootstrap a super admin: promote the earliest admin if none
            # has been designated yet. The owner can later transfer this
            # role manually in the database if needed.
            try:
                if not User.query.filter_by(is_super_admin=True).first():
                    owner = (User.query.filter_by(is_admin=True)
                             .order_by(User.created_at.asc()).first())
                    if owner:
                        owner.is_super_admin = True
                        db.session.commit()
                        print(f"Bootstrapped super admin: {owner.username}")
            except Exception as _boot_err:
                print(f"Super admin bootstrap skipped: {_boot_err}")
        except Exception as _post_err:
            print(f"Post-migration setup error: {_post_err}")
        # Backfill empty subject from topic. Many legacy bank rows were
        # ingested before the subject column existed, so they have subject=''.
        # Without a subject, the new Subject filter on the bank page hides
        # them entirely. Map each known topic keyword to its CAPS subject so
        # picking a Subject actually shows the relevant questions.
        try:
            topic_to_subject_keywords = [
                # Computer Applications Technology
                ('Computer Applications Technology', [
                    'system technologies', 'systems technologies', 'social implications',
                    'information management', 'internet and network', 'internet & network',
                    'internet and www', 'spreadsheet', 'word processing', 'database',
                    'html', 'web design', 'integrated scenario', 'multiple choice',
                    'matching', 'true/false', 'section a', 'networks',
                    'solution development', 'pat', 'file management', 'hardware',
                    'software', 'presentations',
                ]),
                # Information Technology (only if it specifically mentions IT topics)
                ('Information Technology', [
                    'delphi', 'pascal', 'object-oriented', 'object oriented',
                    'gui components', 'algorithm', 'sql',
                ]),
                # Mathematics
                ('Mathematics', [
                    'algebra', 'calculus', 'trigonometry', 'euclidean',
                    'analytical geometry', 'functions & graphs', 'sequences & series',
                ]),
            ]
            unlabelled = QuestionBankItem.query.filter(
                (QuestionBankItem.subject == None) | (QuestionBankItem.subject == '')
            ).all()
            backfilled = 0
            for item in unlabelled:
                topic = (item.topic or '').lower().strip()
                if not topic:
                    continue
                matched = None
                for subj, keywords in topic_to_subject_keywords:
                    if any(kw in topic for kw in keywords):
                        matched = subj
                        break
                if matched:
                    item.subject = matched
                    backfilled += 1
            if backfilled:
                db.session.commit()
                print(f"Backfilled subject for {backfilled} bank items")
        except Exception as _bf_err:
            db.session.rollback()
            print(f"Subject backfill skipped: {_bf_err}")
        if seed_demo_users:
            admin = User.query.filter_by(username='admin').first()
            if not admin and not User.query.filter_by(email='admin@catcaps.edu.za').first():
                admin = User(username='admin', email='admin@catcaps.edu.za', first_name='Admin', last_name='User', is_admin=True)
                admin.set_password('admin123'); db.session.add(admin); db.session.commit()
                print('Admin created (admin / admin123)')
            student = User.query.filter_by(username='student').first()
            if not student and not User.query.filter_by(email='student@catcaps.edu.za').first():
                student = User(username='student', email='student@catcaps.edu.za', first_name='Test', last_name='Student', grade=12)
                student.set_password('student123'); db.session.add(student); db.session.commit()
                print('Student created (student / student123)')
        seed_data()
        print('Database initialized successfully')

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5004))
    app.run(debug=True, host='0.0.0.0', port=port)
