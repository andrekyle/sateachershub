# -*- coding: utf-8 -*-
"""Re-extract CAT P1 May/June 2023 figures from the original PDF at high DPI,
using exact placement bboxes so nothing is cut off. Backs up old PNGs first."""
import fitz, os, shutil, datetime

PDF = 'static/uploads/Computer Applications Technology P1 May-June 2023 Eng.pdf'
FOLDER = 'static/uploads/cat_p1_mj23'
DPI = 300
src = fitz.open(PDF)

# figure -> (page index, source) where source is ('xref', n) for raster placement
# or ('rect', fitz.Rect) for a vector region.
P = lambda *a: fitz.Rect(*a)
FIGS = {
    'q1_3_footnote':  (3,  ('xref', 32)),
    'q1_4_columns':   (3,  ('xref', 33)),
    'q1_8_funicular': (4,  ('xref', 36)),
    'q2_3_pagenum':   (5,  ('xref', 39)),
    'q2_4_toc':       (5,  ('xref', 40)),
    'q2_9_map':       (6,  ('xref', 43)),
    'q4_1_banner':    (9,  ('xref', 55)),
    'q4_6_chart':     (10, ('rect', P(82.35, 332.57, 524.85, 583.82))),
    'q5_4_query':     (12, ('rect', P(231.0, 343.0, 375.5, 458.0))),
    'q5_6_report':    (13, ('xref', 94)),
    'q6_1_web':       (14, ('xref', 97)),
    'q6_2_web':       (16, ('xref', 104)),
    'q7_1_2_heading': (17, ('xref', 117)),
}

# backup
stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup = os.path.join(FOLDER, f'_backup_cut_{stamp}')
os.makedirs(backup, exist_ok=True)

for name, (pno, (kind, val)) in FIGS.items():
    page = src[pno]
    if kind == 'xref':
        infos = {inf['xref']: inf for inf in page.get_image_info(xrefs=True)}
        inf = infos.get(val)
        if not inf:
            print('MISSING xref', name, pno, val); continue
        b = inf['bbox']
        clip = fitz.Rect(b[0]-2, b[1]-2, b[2]+2, b[3]+2)
    else:
        clip = val
    pix = page.get_pixmap(dpi=DPI, clip=clip)
    dst = os.path.join(FOLDER, name + '.png')
    if os.path.exists(dst):
        shutil.copy2(dst, os.path.join(backup, name + '.png'))
    pix.save(dst)
    print(f'{name:16} {pix.width}x{pix.height} AR {pix.width/pix.height:.3f}')

print('backup ->', backup)
