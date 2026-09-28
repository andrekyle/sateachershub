"""Extract just the paragraph-setting icon (and any other small images) from
the CAT P2 Nov 2025 paper, around Q1.8.

Strategy: render the page area where Q1.8 lives at 200dpi, then visually
crop the icon. We do that by finding the text "1.8" and the next "A " on
the same page; the icon sits between those two y-coordinates.
"""
import fitz, os, re

PDF = r"static/uploads/Computer Applications Technology P2 Nov 2025 Eng.pdf"
OUT_DIR = r"static/uploads/cat_p2_n25"
os.makedirs(OUT_DIR, exist_ok=True)

doc = fitz.open(PDF)
print('pages:', doc.page_count)

# find page containing "1.8" and "paragraph setting"
target_page = None
for pno in range(min(doc.page_count, 10)):
    txt = doc[pno].get_text()
    if 'paragraph setting' in txt.lower() and '1.8' in txt:
        target_page = pno
        break
print('q1.8 page index:', target_page)
if target_page is None:
    raise SystemExit('not found')

page = doc[target_page]
# find bbox of "1.8" and bbox of first option marker "A " after it
hits_18 = page.search_for('1.8')
print('1.8 hits:', hits_18)
hits_19 = page.search_for('1.9')
print('1.9 hits:', hits_19)

# Use top-of-1.8 and top-of-1.9 to bound the question region
if not hits_18:
    raise SystemExit('no 1.8 found')
y_top = hits_18[0].y0 - 4
y_bot = hits_19[0].y0 - 4 if hits_19 else page.rect.y1

# region for icon = below text "document?" and above first option "A To adjust"
hits_doc = page.search_for('document?', clip=fitz.Rect(0, y_top, page.rect.x1, y_bot))
hits_A = page.search_for('To adjust alignment', clip=fitz.Rect(0, y_top, page.rect.x1, y_bot))
print('doc hits:', hits_doc, 'A hits:', hits_A)

if hits_doc and hits_A:
    icon_top = hits_doc[0].y1 + 6
    icon_bot = hits_A[0].y0 - 6
    icon_rect = fitz.Rect(118, icon_top, 175, icon_bot)
    print('icon rect:', icon_rect)
    pix = page.get_pixmap(clip=icon_rect, dpi=300)
    out_path = os.path.join(OUT_DIR, 'q1_8.png')
    pix.save(out_path)
    print('saved', out_path, pix.width, 'x', pix.height)

# Also try extracting embedded images intersecting the icon region
print('\n--- embedded images on page ---')
for img in page.get_images(full=True):
    xref = img[0]
    try:
        rects = page.get_image_rects(xref)
    except Exception:
        rects = []
    for r in rects:
        # only print images that fall within the question-1.8 region
        if r.y0 > y_top and r.y1 < y_bot:
            print(f'xref={xref} rect={r} size={img[2]}x{img[3]}')
            pixi = fitz.Pixmap(doc, xref)
            ext = 'png'
            out_p = os.path.join(OUT_DIR, f'_emb_x{xref}.{ext}')
            if pixi.colorspace and pixi.colorspace.n >= 4:
                pixi = fitz.Pixmap(fitz.csRGB, pixi)
            pixi.save(out_p)
            print('  saved', out_p)

# also save the whole question region for sanity check
sanity_rect = fitz.Rect(0, y_top, page.rect.x1, y_bot)
pix2 = page.get_pixmap(clip=sanity_rect, dpi=200)
pix2.save(os.path.join(OUT_DIR, '_q1_8_full.png'))
print('saved full region')
