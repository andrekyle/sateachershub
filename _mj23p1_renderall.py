"""Render PDF question pages to PNGs + current paper to standalone HTML."""
import os, pathlib
import pdfplumber
from flask import render_template
from app import app, db, GeneratedPaper, _build_paper_context

PID = '4cc75484-e298-41f3-bd08-e3d1db11ee71'
PDF = r'data/all_uploads/Computer Applications Technology P1 May-June 2023 Eng.pdf'
outdir = pathlib.Path('_mj23p1_audit')
outdir.mkdir(exist_ok=True)

# 1. PDF pages 1-23 -> PNG (cover+instructions+all questions+appendices)
with pdfplumber.open(PDF) as pdf:
    for pno in range(1, len(pdf.pages) + 1):
        page = pdf.pages[pno - 1]
        page.to_image(resolution=150).save(str(outdir / f'pdf_p{pno:02d}.png'))
print("PDF pages rendered ->", outdir)

# 2. Current paper -> standalone HTML
root = pathlib.Path(os.getcwd())
static_uri = (root / 'static').as_uri()
with app.app_context():
    paper = db.session.get(GeneratedPaper, PID)
    with app.test_request_context(f'/teacher/generator/{PID}/preview'):
        ctx = _build_paper_context(paper, with_memo=False, version='current')
        ctx['version'] = 'current'
        html = render_template('teacher/paper_print.html', **ctx)
    html = html.replace('/static/', static_uri + '/')
    out = outdir / 'current_preview.html'
    out.write_text(html, encoding='utf-8')
    print("wrote", out)
