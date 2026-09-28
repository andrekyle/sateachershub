# AUDIT BRIEF — CAT P1 May/June 2023 (verbatim fix vs original PDF)

## Identity
- PAPER ID (PID): `4cc75484-e298-41f3-bd08-e3d1db11ee71`
- Owner UID: `951c278b-2d76-4969-b0d4-6271479bf397`
- DB: SQLite `instance/brandcartel.db` (accessed via Flask app context)
- Original PDF: `data/all_uploads/Computer Applications Technology P1 May-June 2023 Eng.pdf` (23 pages)
- Memo PDF: `data/all_uploads/Computer Applications Technology P1 May-June 2023 MG Eng.pdf`
- Python: use `.\.venv\Scripts\python.exe`
- This is a CAT P1 PRACTICAL paper: NO sections banner, single section secs[0], TOTAL: 150.

## Goal
Make the generated paper render VERBATIM like the original PDF — wording, marks, headings,
numbering, embedded example figures, notes. Fix only YOUR question. Do NOT touch other questions.

## Section structure (secs[0])
- `question_ids`: list of 59 QuestionBankItem UUIDs (order matters)
- `splits` = [0, 9, 19, 26, 32, 42, 52] → CUMULATIVE start indices:
  - Q1 = items[0:9]   (1.1–1.9)   PDF pages 4–5
  - Q2 = items[9:19]  (2.1–2.10)  PDF pages 6–8
  - Q3 = items[19:26] (3.1–3.7)   PDF page 9
  - Q4 = items[26:32] (4.1–4.6)   PDF pages 10–11
  - Q5 = items[32:42] (5.1–5.6)   PDF pages 12–14
  - Q6 = items[42:52] (6.1–6.2)   PDF pages 15–17
  - Q7 = items[52:59] (7.1–7.2)   PDF page 18
- `qinstructions[qi]` = per-question intro paragraph (renders as `.q-intro` after the QUESTION heading)
- `qtitles[qi]` = per-question title (currently '' → template falls back to topic/DBE map; "QUESTION N: WORD PROCESSING" etc.)
- `qoutros[qi]` = the FINAL left-aligned closer for question qi (e.g. "Save and close the **1CapePoint** word processing document.")
- `qpost_texts[qid]` = per-item text rendered BELOW that item (and below its figure). Use for mid-question closers / NOTES that appear after a figure.
- `subitems` = indices that are depth-3 sub-items (e.g. 5.1.1)

## Rendered comparison artifacts (folder `_mj23p1_audit/`)
- `pdf_p01.png` … `pdf_p23.png` = original PDF pages (150 dpi)
- `cur_p01.png` … `cur_pNN.png` = CURRENT generated render (one image per `.page`). NOTE: app pagination
  differs from the PDF and page numbers SHIFT when you add content — always re-render and re-identify
  YOUR question's page(s) by content, not by fixed page number.

## How to inspect items (read-only)
```python
from app import app, db, GeneratedPaper, QuestionBankItem
import json
PID='4cc75484-e298-41f3-bd08-e3d1db11ee71'
with app.app_context():
    p=db.session.get(GeneratedPaper,PID); secs=json.loads(p.sections); sec=secs[0]
    qids=sec['question_ids']
    for idx in range(A,B):            # your range
        it=db.session.get(QuestionBankItem,qids[idx])
        print(idx, it.marks, repr(it.image_path), repr(it.image_width), it.tags)
        print('   ', repr(it.question_text))
```

## How to FIX
### A. Edit item text / marks (QuestionBankItem)
```python
it=db.session.get(QuestionBankItem,qids[idx])
it.question_text = "...verbatim text..."   # use \n for line breaks, \n\n for paragraph gaps
it.marks = 3
db.session.commit()
```
- Strip any trailing embedded `(N)` mark token and page-footer chrome (e.g. "20231", "Copyright reserved",
  "Please turn over", "Total ...") from question_text.
- Inline emphasis in question_text is converted by `_apply_inline`: `**bold**`, `__underline__`,
  whitelisted `<i>…</i>`/`<b>`; data-file names like `1CapePoint`/`tbl5_1`/`qry5_4` auto-bold.

### B. Attach an embedded example figure (crop from the PDF)
Most P1 example boxes are DRAWN (not raster), so crop by bbox with pdfplumber:
```python
import pdfplumber
PDF=r'data/all_uploads/Computer Applications Technology P1 May-June 2023 Eng.pdf'
with pdfplumber.open(PDF) as pdf:
    page=pdf.pages[PAGE-1]                       # PAGE is 1-based PDF page
    # find bbox via text anchors:
    # words=page.extract_words(); inspect tops/x to bound the figure
    crop=page.within_bbox((x0, top, x1, bottom)) # points; content width x0~86..532
    crop.to_image(resolution=220).save('static/uploads/cat_p1_mj23/qX_Y_name.png')
```
Then attach:
```python
it.image_path='uploads/cat_p1_mj23/qX_Y_name.png'
it.image_width=70        # % of column width (tune 38–98)
# add 'noborder' tag if the crop already includes its own black box border:
tags=[t.strip() for t in (it.tags or '').split(',')]
if 'noborder' not in tags: tags.append('noborder')
it.tags=', '.join(tags)
db.session.commit()
```
- `.q-figure img` already gets a black border by default; use `noborder` ONLY when the crop already
  contains the PDF's own border box (avoids double border).
- A NOTE that appears AFTER a figure goes into `qpost_texts[qid]` (so it renders below the image),
  NOT into question_text.

### C. Edit section-level fields (qinstructions / qoutros / qpost_texts / splits)
```python
secs=json.loads(p.sections); sec=secs[0]
sec['qinstructions'][qi] = "...intro...\nOpen the **NFile** ... document ..."
sec['qpost_texts'][qids[idx]] = "Save and close ..."
p.sections=json.dumps(secs, ensure_ascii=False); db.session.commit()
```

## How to RE-RENDER + screenshot to verify
```
.\.venv\Scripts\python.exe _mj23p1_renderall.py   # rebuilds _mj23p1_audit/current_preview.html + pdf pngs
.\.venv\Scripts\python.exe _mj23p1_shot.py        # rewrites _mj23p1_audit/cur_pNN.png
```
Then view the relevant `cur_pNN.png` and compare side-by-side with `pdf_pMM.png`.
(If you only changed data, you can re-run just these two scripts; they are safe and idempotent.)

## Verbatim rules
- Match wording, punctuation (straight quotes ' "), capitalisation (NOTE:, NOT, AND), numbering, and marks
  EXACTLY as the PDF.
- Do NOT invent content. Do NOT add auto-fill scaffolding.
- Per-item mark `(N)` appears at the END of the LAST sub-item of a group in the PDF — the group total `[NN]`
  is rendered by the template, do not bake it into text.

## ENCODING WARNING
When writing scripts, save as UTF-8. Do NOT use PowerShell Get-Content -Raw/Set-Content on the DB or
templates (corrupts UTF-8). Edit DB via Python only.

## Report back
List: (1) discrepancies found in your question, (2) exact fixes applied, (3) verification result
(did your re-rendered page match the PDF?).
