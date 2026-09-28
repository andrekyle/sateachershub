import json
from app import app, db, GeneratedPaper, QuestionBankItem

P = 'b1721187-9537-4d66-845d-263a8d3c3d0b'
out = []
with app.app_context():
    paper = db.session.get(GeneratedPaper, P)
    out.append(f"TITLE={paper.title!r}")
    out.append(f"total_marks={paper.total_marks} exam_date={paper.exam_date} paper_number={paper.paper_number}")
    out.append(f"cover_subtitle={getattr(paper,'cover_subtitle',None)!r}")
    out.append(f"cover_extra_note={getattr(paper,'cover_extra_note',None)!r}")
    out.append(f"sub_header={getattr(paper,'sub_header',None)!r}")
    out.append(f"cover_title={getattr(paper,'cover_title',None)!r}")
    out.append(f"instructions={paper.instructions!r}")
    secs = json.loads(paper.sections)
    out.append(f"\nNUM SECTIONS={len(secs)}")
    for si, sec in enumerate(secs):
        out.append(f"\n###### SECTION {si}: title={sec.get('title')!r}")
        out.append(f"  instructions={sec.get('instructions')!r}")
        out.append(f"  splits={sec.get('splits')}")
        out.append(f"  qtitles={sec.get('qtitles')}")
        out.append(f"  qinstructions={sec.get('qinstructions')}")
        out.append(f"  subitems={sec.get('subitems')}")
        out.append(f"  qimages={sec.get('qimages')}")
        out.append(f"  scenario={sec.get('scenario')!r}")
        out.append(f"  tf_examples={sec.get('tf_examples')}")
        out.append(f"  tf_no_mark={sec.get('tf_no_mark')!r}")
        out.append(f"  qpost_texts={sec.get('qpost_texts')}")
        out.append(f"  qoutros={sec.get('qoutros')}")
        out.append(f"  subtables={sec.get('subtables')}")
        qids = sec.get('question_ids', [])
        out.append(f"  NUM ITEMS={len(qids)}")
        for idx, qid in enumerate(qids):
            it = db.session.get(QuestionBankItem, qid)
            if not it:
                out.append(f"   [{idx}] MISSING {qid}")
                continue
            out.append(f"   [{idx}] type={it.question_type} marks={it.marks} img={it.image_path!r}")
            out.append(f"        Q={it.question_text!r}")
            out.append(f"        A={it.answer_text!r}")
with open("_p2_db.txt","w",encoding="utf-8") as f:
    f.write("\n".join(out))
print("done")
