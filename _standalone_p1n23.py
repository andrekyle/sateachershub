# -*- coding: utf-8 -*-
"""Render preview to a standalone HTML with absolute file:// asset paths."""
import os, pathlib
from flask import render_template
from app import app, db, GeneratedPaper, _build_paper_context

PID = '06a40eac-5b21-4ef1-815c-698cecce89f2'
root = pathlib.Path(os.getcwd())
static_uri = (root / 'static').as_uri()  # file:///.../static
with app.app_context():
    paper = db.session.get(GeneratedPaper, PID)
    with app.test_request_context(f'/teacher/generator/{PID}/preview'):
        ctx = _build_paper_context(paper, with_memo=False, version='current')
        ctx['version'] = 'current'
        html = render_template('teacher/paper_print.html', **ctx)
    html = html.replace('/static/', static_uri + '/')
    out = root / '_p1n23_standalone.html'
    out.write_text(html, encoding='utf-8')
    print("wrote", out)
