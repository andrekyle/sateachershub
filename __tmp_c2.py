# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from app import app, GeneratedPaper, _paper_to_docx
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn as Q
with app.app_context():
    p = GeneratedPaper.query.get('48c8c8d1-b356-490a-90a6-56868b67d10d')
    bio=_paper_to_docx(p,with_memo=True,version='current'); bio.seek(0)
    d=Document(bio)
    def blocks(parent):
        for c in parent.element.body.iterchildren():
            if c.tag==Q('w:p'): yield Paragraph(c,parent)
            elif c.tag==Q('w:tbl'): yield Table(c,parent)
    ti=0
    for blk in blocks(d):
        if isinstance(blk,Table):
            ti+=1
            hdr=[c.text.replace(chr(10),' ')[:14] for c in blk.rows[0].cells]
            print(f't{ti}: cols={len(blk.columns)} r0={hdr}')
            if ti in (3,9,10):  # fragment, Q5-related
                for row in blk.rows[:3]:
                    print('     ', [c.text.replace(chr(10),'/')[:16] for c in row.cells])
