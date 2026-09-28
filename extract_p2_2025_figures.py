"""Extract figures from CAT P2 May-June 2025 PDF and attach to QuestionBankItems.

Mapping (qid -> list of (page_index_0based, bbox)):
  Q1.5  - HTML table screenshot
  Q1.10 - book spreadsheet
  Q4.1  - StellarX Pro advertisement (attach to the stem item)
  Q8.4  - Linked object (2 images side-by-side)
  Q8.5  - Circular reference error message
  Q8.7  - HTML code + web page (2 images side-by-side)
  Q9.5  - Database form
  Q10.6 - Spreadsheet quote
  Q10.8 - Snack Shack form layout

Renders the region from the PDF at 220 DPI and saves a PNG into
  static/uploads/paper_images/p2_2025/<qid>.png
then writes the relative path into the item's image_path column.
"""
import os, sys, io
import fitz
from PIL import Image
from app import app, GeneratedPaper, QuestionBankItem, db

PDF_PATH = r'C:\Users\hp\Pictures\southafricanteachershub - new - Copy (3)\static\uploads\Computer Applications Technology P2 May-June 2025 Eng.pdf'
OUT_DIR_REL = 'uploads/paper_images/p2_2025'  # relative to static/
OUT_DIR_ABS = os.path.join(
    r'C:\Users\hp\Pictures\southafricanteachershub - new - Copy (3)\static',
    *OUT_DIR_REL.split('/'),
)

# (qid, [(page_0based, (x0, top, x1, bottom)), ...])  bbox in pdfplumber/PDF coordinates (origin top-left)
MAPPING = [
    # Q1.5 page 3, single image
    ('57fe6ac3-4e2e-4398-aad6-a1204d802f93', [(2, (220, 615, 370, 700))]),
    # Q1.10 page 4
    ('7a6f3a3e-b77d-407b-824a-ef0fe36f1831', [(3, (140, 505, 475, 655))]),
    # Q4.1 stem page 7
    ('b5a57942-9152-4305-90b2-569933054aaa', [(6, (385, 190, 540, 345))]),
    # Q8.4 page 12 (two small images side-by-side -- crop the joined region)
    ('c575d1a6-fd61-40c6-94ae-842ebfb83833', [(11, (195, 250, 440, 320))]),
    # Q8.5 page 12
    ('b8856cae-aea3-493f-9ac6-398f4c8dc2a6', [(11, (135, 480, 495, 615))]),
    # Q8.7 page 13 (two images side-by-side)
    ('30d3b01f-3400-437d-bcd9-ff40e021ebfb', [(12, (85, 140, 560, 345))]),
    # Q9.5 page 15
    ('b80f121d-f5cf-43e5-9b56-a75c4a24d5f2', [(14, (175, 120, 450, 450))]),
    # Q10.6 page 18
    ('fee3fc9a-06ca-421f-b862-952365fb15f6', [(17, (155, 110, 475, 430))]),
    # Q10.8 page 19
    ('a66b3453-61ee-4de5-9091-e3f0a17aa375', [(18, (100, 115, 530, 270))]),
]


def render_region(doc, page_index, bbox, dpi=220):
    page = doc[page_index]
    rect = fitz.Rect(*bbox)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, clip=rect, alpha=False)
    return Image.frombytes('RGB', (pix.width, pix.height), pix.samples)


def main():
    os.makedirs(OUT_DIR_ABS, exist_ok=True)
    app.app_context().push()

    doc = fitz.open(PDF_PATH)
    print(f'PDF has {len(doc)} pages')

    updated = 0
    for qid, regions in MAPPING:
        q = QuestionBankItem.query.filter_by(id=qid).first()
        if not q:
            print(f'  ! qid {qid} not found, skipping')
            continue
        imgs = [render_region(doc, p, b) for (p, b) in regions]
        if len(imgs) == 1:
            final = imgs[0]
        else:
            h = max(im.height for im in imgs)
            scaled = []
            for im in imgs:
                if im.height != h:
                    new_w = int(im.width * (h / im.height))
                    im = im.resize((new_w, h), Image.LANCZOS)
                scaled.append(im)
            gap = 12
            total_w = sum(im.width for im in scaled) + gap * (len(scaled) - 1)
            final = Image.new('RGB', (total_w, h), 'white')
            x = 0
            for im in scaled:
                final.paste(im, (x, 0))
                x += im.width + gap
        out_name = f'{qid}.png'
        out_abs = os.path.join(OUT_DIR_ABS, out_name)
        final.save(out_abs, 'PNG', optimize=True)
        rel = f'{OUT_DIR_REL}/{out_name}'
        q.image_path = rel
        updated += 1
        print(f'  + {qid} -> {rel}  ({final.size[0]}x{final.size[1]})')

    db.session.commit()
    print(f'updated {updated} items')


if __name__ == '__main__':
    main()
