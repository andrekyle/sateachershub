"""Restore database from data/*.csv backup files.

Reads CSV exports under ./data/ and inserts rows into the existing tables
(creating them via SQLAlchemy if missing). Existing rows with the same
primary key are skipped, so this script is safe to re-run.

Run with the project venv:  python restore_from_csv.py
"""
from __future__ import annotations

import csv
import os
from datetime import datetime, date

from app import (
    app, db,
    User, Grade, TeacherDocument, QuestionBankItem,
    GeneratedPaper, TeacherSchedule, InstructionTemplate,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


# ---------------------------------------------------------------- helpers
def _read_csv(name: str):
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        print(f"  skip (missing): {name}")
        return []
    with open(path, 'r', encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def _to_bool(v):
    if v is None:
        return False
    s = str(v).strip().lower()
    return s in ('1', 'true', 't', 'yes', 'y')


def _to_int(v, default=None):
    if v is None or str(v).strip() == '':
        return default
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _to_dt(v):
    if not v:
        return None
    s = str(v).strip()
    if not s:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _to_date(v):
    dt = _to_dt(v)
    if isinstance(dt, datetime):
        return dt.date()
    return None


def _restore(model, rows, builder, label, unique_cols=()):
    """unique_cols: iterable of (csv_column, model_attr) tuples."""
    added = skipped = 0
    with db.session.no_autoflush:
        for row in rows:
            pk = row.get('id')
            if pk and db.session.get(model, pk) is not None:
                skipped += 1
                continue
            existing = None
            for csv_col, attr in unique_cols:
                val = row.get(csv_col)
                if val in (None, ''):
                    continue
                col = getattr(model, attr)
                # Cast to int for integer-typed columns
                try:
                    if 'INTEGER' in str(col.type).upper():
                        val = int(float(val))
                except (TypeError, ValueError):
                    continue
                existing = db.session.query(model).filter(col == val).first()
                if existing is not None:
                    break
            if existing is not None:
                skipped += 1
                continue
            try:
                obj = builder(row)
            except Exception as exc:  # pragma: no cover
                print(f"  ! {label} row failed: {exc}")
                continue
            db.session.add(obj)
            added += 1
    db.session.commit()
    print(f"  {label}: +{added} added, {skipped} already present")


# ---------------------------------------------------------------- builders
def _build_user(r):
    return User(
        id=r['id'],
        username=r['username'],
        email=r['email'],
        password_hash=r['password_hash'],
        first_name=r.get('first_name', ''),
        last_name=r.get('last_name', ''),
        is_admin=_to_bool(r.get('is_admin')),
        is_teacher=_to_bool(r.get('is_teacher')),
        is_hod=_to_bool(r.get('is_hod')),
        is_super_admin=_to_bool(r.get('is_super_admin')),
        is_blocked=_to_bool(r.get('is_blocked')),
        grade=_to_int(r.get('grade')),
        profile_pic=r.get('profile_pic', '') or '',
        created_at=_to_dt(r.get('created_at')) or datetime.utcnow(),
    )


def _build_grade(r):
    return Grade(
        id=r['id'],
        number=_to_int(r.get('grade_number')) or 0,
        name=r.get('grade_name', '') or '',
        description=r.get('description', '') or '',
    )


def _build_teacher_doc(r):
    return TeacherDocument(
        id=r['id'],
        title=r.get('title', '') or '',
        description=r.get('description', '') or '',
        grade=_to_int(r.get('grade')),
        subject=r.get('subject') or 'CAT',
        paper_year=_to_int(r.get('paper_year')),
        paper_type=r.get('paper_type') or 'past_paper',
        paper_number=r.get('paper_number') or '',
        file_path=r.get('file_path', '') or '',
        file_size=_to_int(r.get('file_size')) or 0,
        uploaded_by=r.get('uploaded_by') or None,
        uploaded_at=_to_dt(r.get('uploaded_at')) or datetime.utcnow(),
        download_count=_to_int(r.get('download_count')) or 0,
    )


def _build_question(r):
    return QuestionBankItem(
        id=r['id'],
        owner_id=r['owner_id'],
        grade=_to_int(r.get('grade')) or 12,
        subject=r.get('subject', '') or '',
        topic=r.get('topic', '') or '',
        subtopic=r.get('subtopic', '') or '',
        difficulty=r.get('difficulty') or 'medium',
        question_type=r.get('question_type') or 'short_answer',
        question_text=r.get('question_text', '') or '',
        answer_text=r.get('answer_text', '') or '',
        marks=_to_int(r.get('marks')) or 1,
        tags=r.get('tags', '') or '',
        image_path=r.get('image_path', '') or '',
        is_shared=_to_bool(r.get('is_shared')),
        created_at=_to_dt(r.get('created_at')) or datetime.utcnow(),
    )


def _build_paper(r):
    return GeneratedPaper(
        id=r['id'],
        owner_id=r['owner_id'],
        title=r.get('title') or 'Examination Paper',
        school_name=r.get('school_name', '') or '',
        subject=r.get('subject') or 'Computer Applications Technology',
        grade=_to_int(r.get('grade')) or 12,
        exam_date=_to_date(r.get('exam_date')),
        duration_minutes=_to_int(r.get('duration_minutes')) or 180,
        total_marks=_to_int(r.get('total_marks')) or 150,
        examiner=r.get('examiner', '') or '',
        moderator=r.get('moderator', '') or '',
        instructions=r.get('instructions', '') or '',
        logo_path=r.get('logo_path', '') or '',
        paper_number=r.get('paper_number', '') or '',
        cover_authority=r.get('cover_authority', '') or '',
        cover_subtitle=r.get('cover_subtitle', '') or '',
        header_left=r.get('header_left', '') or '',
        header_right=r.get('header_right', '') or '',
        sub_header=r.get('sub_header', '') or '',
        footer_left=r.get('footer_left', '') or 'Copyright reserved',
        footer_center=r.get('footer_center', '') or '',
        footer_right=r.get('footer_right', '') or 'Please turn over',
        memo_title=r.get('memo_title', '') or 'MARKING GUIDELINES',
        cover_extra_note=r.get('cover_extra_note', '') or '',
        sections=r.get('sections_json', '') or '[]',
        created_at=_to_dt(r.get('created_at')) or datetime.utcnow(),
    )


def _build_schedule(r):
    sd = _to_date(r.get('start_date')) or date.today()
    return TeacherSchedule(
        id=r['id'],
        owner_id=r['owner_id'],
        title=r.get('title') or 'Untitled',
        description=r.get('description', '') or '',
        grade=_to_int(r.get('grade')),
        kind=r.get('kind') or 'lesson',
        start_date=sd,
        end_date=_to_date(r.get('end_date')),
        term=_to_int(r.get('term')),
        color=r.get('color') or '#0078D4',
        created_at=_to_dt(r.get('created_at')) or datetime.utcnow(),
    )


def _build_instruction(r):
    return InstructionTemplate(
        id=r['id'],
        owner_id=r['owner_id'],
        text=r.get('text_body', '') or '',
        created_at=_to_dt(r.get('created_at')) or datetime.utcnow(),
    )


def main():
    with app.app_context():
        db.create_all()
        print('Restoring data from', DATA_DIR)
        # Order respects foreign keys: users & grades first.
        _restore(User, _read_csv('APP_USERS.csv'), _build_user, 'Users',
                 unique_cols=(('username', 'username'), ('email', 'email')))
        _restore(Grade, _read_csv('APP_GRADES.csv'), _build_grade, 'Grades',
                 unique_cols=(('grade_number', 'number'),))
        _restore(TeacherDocument, _read_csv('APP_TEACHER_DOCUMENTS.csv'),
                 _build_teacher_doc, 'TeacherDocuments')
        _restore(QuestionBankItem, _read_csv('APP_QUESTION_BANK.csv'),
                 _build_question, 'QuestionBankItems')
        _restore(GeneratedPaper, _read_csv('APP_GENERATED_PAPERS.csv'),
                 _build_paper, 'GeneratedPapers')
        _restore(TeacherSchedule, _read_csv('APP_TEACHER_SCHEDULES.csv'),
                 _build_schedule, 'TeacherSchedules')
        _restore(InstructionTemplate, _read_csv('APP_INSTRUCTION_TEMPLATES.csv'),
                 _build_instruction, 'InstructionTemplates')
        print('Done.')


if __name__ == '__main__':
    main()
