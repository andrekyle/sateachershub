"""Extract figure images from a past-paper PDF and save them where the
paper editor's auto-attach logic expects them.

Folder convention (read by app.py around the "Auto-attach figure images
to sub-items" comment):

    static/uploads/paper_images/<paper_id>/<question_id>/<localkey>.<ext>

where <localkey> is the sub-item label minus its leading question number
(e.g. for Q5 sub-item "5.13" -> "13.png"; for Q1 sub-item "1.1.1" ->
"1.1.png").

Usage (one-off):
    python extract_paper_images.py <paper_id> <pdf_path>

The script reads the paper's sections JSON from the SQLite DB
(brandcartel.db) to figure out which QuestionBankItem.id corresponds to
which QUESTION number on the paper, then walks the PDF pages with
PyMuPDF to find figures and place them into the correct per-question
folder.
"""
import os
import re
import sys
import json
import sqlite3

import fitz  # PyMuPDF


# Filter: images smaller than this in BOTH dimensions are decorative
# (dotted-line stamps, bullet glyphs, etc.) and skipped.
MIN_W = 70
MIN_H = 40


def load_paper_qmap(db_path, paper_id):
    """Return {question_number: question_id} for the given paper.

    QUESTION 1 is the first id in the first section, QUESTION 2 the
    second, etc., walking sections in order — this matches how
    teacher_paper_use builds the paper.
    """
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute("SELECT sections FROM generated_papers WHERE id=?", (paper_id,))
        row = cur.fetchone()
        if not row:
            raise SystemExit(f"No paper {paper_id!r} in {db_path}")
        sections = json.loads(row[0] or '[]')
    finally:
        con.close()
    qmap = {}
    qnum = 0
    for sec in sections:
        for qid in sec.get('question_ids', []):
            qnum += 1
            qmap[qnum] = qid
    return qmap


# Sub-item label like "1.5", "1.11", "5.13", "1.1.1" sitting at the
# start of a span (left column).
_LABEL_RE = re.compile(r'^\s*(\d+\.\d+(?:\.\d+)?)\b')


def page_text_blocks(page):
    """Yield (text, bbox) for every text span on the page."""
    d = page.get_text("dict")
    for blk in d.get("blocks", []):
        if blk.get("type") != 0:  # 0 = text, 1 = image
            continue
        for line in blk.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "")
                bbox = span.get("bbox")
                if text and bbox:
                    yield text, bbox


def find_current_question(text_spans, image_top):
    """Return the most recent QUESTION N header at or above image_top."""
    qn = None
    for text, bbox in text_spans:
        if bbox[1] > image_top:  # span is below image
            continue
        m = re.match(r'\s*QUESTION\s+(\d+)\b', text, re.I)
        if m:
            qn = int(m.group(1))
    return qn


def find_nearest_label(text_spans, image_top, image_left):
    """Find the closest sub-item label like 1.5 / 1.11 / 1.1.1 sitting
    above the image. Returns the label string or None."""
    best = None
    best_y = -1
    for text, bbox in text_spans:
        if bbox[1] > image_top:
            continue
        # left-column-only: most labels sit at x ~ 70-100
        if bbox[0] > 130:
            continue
        m = _LABEL_RE.match(text)
        if not m:
            continue
        if bbox[1] > best_y:
            best = m.group(1)
            best_y = bbox[1]
    return best


def label_to_localkey(label, qnum):
    """Convert "5.13" -> "13", "1.1.1" -> "1.1", etc.
    Drops the leading Q-number segment."""
    parts = label.split('.', 1)
    if len(parts) != 2:
        return None
    if int(parts[0]) != qnum:
        # Label belongs to a different question — skip.
        return None
    return parts[1]


# Bullet glyphs commonly used in DBE past-paper advertisements / spec
# blocks (star, dot, check, arrow, etc.). When ≥3 consecutive lines in a
# sub-item region start with one of these, treat the whole block as a
# "stem caption" that should be rasterised together with the image and
# stripped from the printed question_text (so the ad isn't duplicated).
_BULLET_RE = re.compile(r'^\s*[\u2022\u25CF\u25CB\u25A0\u25A1\u25B2\u25BC'
                        r'\u25C6\u25C7\u2605\u2606\u2729\u272A\u2726\u2727'
                        r'\u2713\u2714\u2717\u2718\u2190-\u2199\u21D0-\u21D9'
                        r'\u261B\u261E\u2756\u2730\u2731\u2732\u2733\u2734'
                        r'\u2735\u2736\u2737\u2738\u2739\u273A\u273B\u273C'
                        r'\u273D\u273E\u273F\u2740\u2741\u2742\u2743\u2744'
                        r'\u2745\u2746\u2747\u2748\u2749\u274A\u274B'
                        r'\u2B50\u2B51\u2B55\u2B1B\u2B1C'
                        r'\-\*\u00B7]\s+')


def _find_caption_block(spans, raster_bbox, label_bbox, next_label_y,
                        page_rect, min_bullets=3):
    """Locate a contiguous "stem caption" block (advertisement spec list,
    bulleted feature list, etc.) inside the same sub-item region as the
    raster image. Returns (expanded_rect, list_of_caption_lines) or
    (None, []) when no qualifying block is found.

    Heuristic: look at every text span whose vertical centre sits
    between the sub-item label (label_bbox.y0) and the next sub-item
    label (next_label_y), excluding the sub-item label line itself.
    Group spans into lines (rounded y). If at least ``min_bullets``
    consecutive lines start with a bullet glyph, we have a caption.
    Optionally pull in the line immediately above the first bullet line
    when it is short and centred — that's typically the ad title
    (e.g. "Introducing the All-New StellarX 7000 SuperBook").
    """
    if not raster_bbox:
        return None, []
    region_top = (label_bbox.y1 if hasattr(label_bbox, 'y1') else label_bbox[3])
    region_bot = next_label_y if next_label_y else page_rect.height - 30
    # Group spans into lines, keyed by rounded y.
    lines = {}
    for text, bb in spans:
        if not text or not bb:
            continue
        y_mid = (bb[1] + bb[3]) / 2
        if y_mid < region_top + 1 or y_mid > region_bot - 1:
            continue
        # Skip the sub-item label span itself.
        if _LABEL_RE.match(text) and bb[0] < 130:
            continue
        key = round(bb[1] / 2.0) * 2  # 2-pt buckets
        lines.setdefault(key, []).append((bb, text))
    if not lines:
        return None, []
    # Compose lines: sort spans within each line by x.
    line_items = []
    for k in sorted(lines.keys()):
        parts = sorted(lines[k], key=lambda p: p[0][0])
        joined = ''.join(p[1] for p in parts).strip()
        if not joined:
            continue
        xs = [p[0][0] for p in parts] + [p[0][2] for p in parts]
        ys = [p[0][1] for p in parts] + [p[0][3] for p in parts]
        line_items.append({
            'text': joined,
            'rect': fitz.Rect(min(xs), min(ys), max(xs), max(ys)),
        })
    if not line_items:
        return None, []
    # Find the longest run of consecutive bullet lines.
    best_run = []
    cur = []
    for li in line_items:
        if _BULLET_RE.match(li['text']):
            cur.append(li)
            if len(cur) > len(best_run):
                best_run = list(cur)
        else:
            cur = []
    if len(best_run) < min_bullets:
        return None, []
    # Pull in the immediately-preceding short line as a title if it sits
    # right above the first bullet and is < 70 chars (typical ad title).
    first_y = best_run[0]['rect'].y0
    title_line = None
    for li in reversed(line_items):
        if li['rect'].y1 <= first_y and li is not best_run[0]:
            gap = first_y - li['rect'].y1
            if gap < 30 and len(li['text']) < 80:
                title_line = li
            break
    block_lines = ([title_line] if title_line else []) + best_run
    # Union of raster + all block-line rects.
    xs = [raster_bbox.x0, raster_bbox.x1]
    ys = [raster_bbox.y0, raster_bbox.y1]
    for li in block_lines:
        xs += [li['rect'].x0, li['rect'].x1]
        ys += [li['rect'].y0, li['rect'].y1]
    pad_x, pad_y = 6, 6
    expanded = fitz.Rect(
        max(page_rect.x0 + 10, min(xs) - pad_x),
        max(page_rect.y0 + 10, min(ys) - pad_y),
        min(page_rect.x1 - 10, max(xs) + pad_x),
        min(page_rect.y1 - 10, max(ys) + pad_y),
    )
    return expanded, [li['text'] for li in block_lines]


def _find_next_label_y(spans, label_bbox, qn, page_height):
    """Find the y-coord of the next sub-item label for the same question
    that sits below ``label_bbox``. Returns page_height - 60 if none."""
    best_y = page_height - 60
    found = False
    for text, bb in spans:
        if bb[0] > 130:
            continue
        m = _LABEL_RE.match(text)
        if not m:
            continue
        if not m.group(1).startswith(f'{qn}.'):
            continue
        if bb[1] <= label_bbox.y1 + 2:
            continue
        if not found or bb[1] < best_y:
            best_y = bb[1]
            found = True
    return best_y


def extract(pdf_path, paper_id, qmap, out_root='static/uploads/paper_images', dry_run=False):
    doc = fitz.open(pdf_path)
    saved = []
    skipped = []
    # Per-question caption strip data: {(qid, local_key): [text_lines]}
    # When set, the caller should remove these lines from the matching
    # QuestionBankItem.question_text to avoid duplicating the ad.
    caption_strip = {}
    # Carry the last seen QUESTION header forward across pages — figures
    # often sit on a page that doesn't repeat the QUESTION heading.
    running_qn = None
    for pno in range(len(doc)):
        page = doc[pno]
        spans = list(page_text_blocks(page))
        # Update running question from this page's headers (top-most wins).
        for text, bbox in spans:
            m = re.match(r'\s*QUESTION\s+(\d+)\b', text, re.I)
            if m:
                running_qn = int(m.group(1))
                break
        # Map xref -> bbox via page.get_image_bbox(item).
        for item in page.get_images(full=True):
            xref = item[0]
            try:
                bbox = page.get_image_bbox(item)
            except Exception:
                continue
            if bbox.is_empty or bbox.width < MIN_W or bbox.height < MIN_H:
                continue
            # Determine question for this image.
            qn = find_current_question(spans, bbox.y0) or running_qn
            if not qn:
                skipped.append((pno + 1, xref, 'no question header'))
                continue
            qid = qmap.get(qn)
            if not qid:
                skipped.append((pno + 1, xref, f'no qid for Q{qn}'))
                continue
            label = find_nearest_label(spans, bbox.y0, bbox.x0)
            if not label:
                skipped.append((pno + 1, xref, f'Q{qn}: no nearby sub-item label'))
                continue
            local = label_to_localkey(label, qn)
            if not local:
                skipped.append((pno + 1, xref, f'label {label} not in Q{qn}'))
                continue
            # Look for a "stem caption" (advertisement spec list / bulleted
            # feature block) around this image. When present, we render
            # the union as a single figure AND record the caption text so
            # the importer can strip it from the duplicated question_text.
            cap_rect, cap_lines = (None, [])
            try:
                # Find the sub-item label's bbox (we already have only
                # the label string from find_nearest_label; locate it
                # again to get its rect).
                label_bb = None
                for t, bb in spans:
                    if bb[0] > 130:
                        continue
                    m_lb = _LABEL_RE.match(t)
                    if m_lb and m_lb.group(1) == label:
                        rb = fitz.Rect(bb)
                        if label_bb is None or rb.y0 > label_bb.y0:
                            label_bb = rb
                if label_bb is None:
                    label_bb = fitz.Rect(bbox.x0 - 60, bbox.y0 - 18,
                                         bbox.x0 - 10, bbox.y0 - 2)
                next_y = _find_next_label_y(spans, label_bb, qn,
                                            page.rect.height)
                cap_rect, cap_lines = _find_caption_block(
                    spans, bbox, label_bb, next_y, page.rect)
            except Exception:
                cap_rect, cap_lines = (None, [])

            out_dir = os.path.join(out_root, paper_id, qid)
            if cap_rect is not None:
                # Rasterise the expanded rect as PNG so the printed
                # figure shows the whole ad (title + bullets + photo).
                out_path = os.path.join(out_dir, f'{local}.png')
                # Always record the caption lines (even in dry-run) so
                # callers can preview which text would be stripped.
                caption_strip[(qid, local)] = cap_lines
                if dry_run:
                    saved.append((pno + 1, qn, label, local,
                                  out_path + ' [+caption]'))
                    continue
                os.makedirs(out_dir, exist_ok=True)
                if not os.path.exists(out_path):
                    try:
                        pix = page.get_pixmap(clip=cap_rect, dpi=200,
                                              alpha=False)
                        pix.save(out_path)
                    except Exception as _e:
                        # Fall back to raw image bytes if the clip render fails.
                        try:
                            info = doc.extract_image(xref)
                            with open(out_path, 'wb') as f:
                                f.write(info.get('image') or b'')
                        except Exception:
                            skipped.append((pno + 1, xref,
                                            f'render+fallback failed: {_e}'))
                            continue
                saved.append((pno + 1, qn, label, local,
                              out_path + ' [+caption]'))
                continue

            # No caption block — save the raw embedded image as before.
            try:
                info = doc.extract_image(xref)
            except Exception as e:
                skipped.append((pno + 1, xref, f'extract failed: {e}'))
                continue
            ext = info.get('ext') or 'png'
            data = info.get('image')
            if not data:
                continue
            out_path = os.path.join(out_dir, f'{local}.{ext}')
            if dry_run:
                saved.append((pno + 1, qn, label, local, out_path))
                continue
            os.makedirs(out_dir, exist_ok=True)
            # Don't clobber an existing file (teacher may have hand-placed one).
            if not os.path.exists(out_path):
                with open(out_path, 'wb') as f:
                    f.write(data)
                # Cap the 5.1.3 Location dropdown screenshot only — it
                # renders very tall on the PDF and otherwise fills a full
                # printed column. All other figures are saved at original
                # size.
                if local == '1.3':
                    try:
                        from PIL import Image as _PILImage
                        with _PILImage.open(out_path) as _im:
                            _im.thumbnail((140, 140))
                            _im.save(out_path)
                    except Exception:
                        pass
            saved.append((pno + 1, qn, label, local, out_path))

        # ---- Vector-figure fallback ----------------------------------
        # Many CAT-style figures (tables, screenshots) are drawn as
        # vector graphics + text and therefore not picked up by
        # get_images(). Detect them by finding the vertical gap between
        # consecutive sub-item labels: if there's a tall band whose body
        # text only sits inside a sub-region (the figure box) and there
        # is no raster image already covering it, rasterize that band.
        try:
            page_qn = running_qn
            qid = qmap.get(page_qn) if page_qn else None
            if not qid:
                continue
            # Collect sub-item labels on this page (left column only).
            labels = []
            for text, bbox in spans:
                m = _LABEL_RE.match(text)
                if not m or bbox[0] > 130:
                    continue
                lbl = m.group(1)
                # only labels for this question
                if not lbl.startswith(f'{page_qn}.'):
                    continue
                labels.append((lbl, bbox))
            # Sort by y
            labels.sort(key=lambda lb: lb[1][1])
            # Page width / height
            pw, ph = page.rect.width, page.rect.height
            # Bottom margin where footer/copyright sits.
            footer_y = ph - 60
            # Existing raster image bboxes on this page (so we don't
            # double-extract).
            raster_boxes = []
            for item in page.get_images(full=True):
                try:
                    rb = page.get_image_bbox(item)
                    if not rb.is_empty:
                        raster_boxes.append(rb)
                except Exception:
                    pass
            for i, (lbl, lbb) in enumerate(labels):
                # Region: from the bottom of the LAST text line of this
                # sub-item (heuristic: this label's y + label_height +
                # the lines that follow on the same x-column) up to the
                # next sub-item label (or footer).
                next_y = labels[i + 1][1][1] if i + 1 < len(labels) else footer_y
                # Find spans that belong to this sub-item's body
                # (between this label and next_y, x > label.x0).
                body_spans = [(t, b) for t, b in spans
                              if b[1] >= lbb[1] and b[3] <= next_y - 2]
                if not body_spans:
                    continue
                # Locate the figure region: the LARGEST vertical gap
                # inside this sub-item region containing no left-column
                # text.
                #
                # Build vertical occupancy of left-column text only.
                left_text_ys = sorted({round(b[1]) for t, b in body_spans
                                       if b[0] < pw * 0.18})
                # Candidate: from after last left-col text -> next_y.
                if not left_text_ys:
                    fig_top = lbb[3] + 4
                else:
                    fig_top = max(left_text_ys[-1] + 12, lbb[3] + 4)
                fig_bottom = next_y - 4
                if fig_bottom - fig_top < 80:
                    continue
                # Skip if already covered by a raster image.
                covered = False
                for rb in raster_boxes:
                    if rb.y0 < fig_bottom and rb.y1 > fig_top:
                        covered = True
                        break
                if covered:
                    continue
                # Confirm there IS some content in the band (avoid
                # rasterising blank tail-of-page).
                band_spans = [(t, b) for t, b in body_spans
                              if b[1] >= fig_top and b[3] <= fig_bottom]
                if not band_spans:
                    continue
                # Tighten bbox to the actual content extent.
                xs = [b[0] for t, b in band_spans] + [b[2] for t, b in band_spans]
                ys = [b[1] for t, b in band_spans] + [b[3] for t, b in band_spans]
                clip = fitz.Rect(max(40, min(xs) - 8),
                                 max(fig_top, min(ys) - 8),
                                 min(pw - 40, max(xs) + 8),
                                 min(fig_bottom, max(ys) + 8))
                if clip.width < 100 or clip.height < 80:
                    continue
                local = label_to_localkey(lbl, page_qn)
                if not local:
                    continue
                out_dir = os.path.join(out_root, paper_id, qid)
                out_path = os.path.join(out_dir, f'{local}.png')
                if dry_run:
                    saved.append((pno + 1, page_qn, lbl, local,
                                  out_path + ' [vector]'))
                    continue
                if os.path.exists(out_path):
                    continue
                os.makedirs(out_dir, exist_ok=True)
                pix = page.get_pixmap(clip=clip, dpi=200, alpha=False)
                pix.save(out_path)
                saved.append((pno + 1, page_qn, lbl, local,
                              out_path + ' [vector]'))
        except Exception as e:
            skipped.append((pno + 1, 0, f'vector pass: {e}'))

    return saved, skipped, caption_strip


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    paper_id = sys.argv[1]
    pdf_path = sys.argv[2]
    dry = '--dry' in sys.argv[3:]
    db_path = os.path.join(os.path.dirname(__file__) or '.', 'brandcartel.db')
    if not os.path.exists(db_path):
        # try instance/
        alt = os.path.join('instance', 'brandcartel.db')
        if os.path.exists(alt):
            db_path = alt
    qmap = load_paper_qmap(db_path, paper_id)
    print(f'Question -> qid map: {qmap}')
    saved, skipped, caption_strip = extract(pdf_path, paper_id, qmap, dry_run=dry)
    print(f'\nSaved {len(saved)} image(s):')
    for s in saved:
        print(f'  page {s[0]:>2}  Q{s[1]}  label {s[2]:<6} -> {s[4]}')
    if caption_strip:
        print(f'\nCaption blocks to strip from question_text: '
              f'{len(caption_strip)}')
        for (qid, key), lines in list(caption_strip.items())[:10]:
            preview = ' | '.join(lines[:3])
            print(f'  {qid[:8]}/{key}: {preview[:90]}')
    if skipped:
        print(f'\nSkipped {len(skipped)}:')
        for sk in skipped[:30]:
            print(f'  page {sk[0]:>2}  xref {sk[1]:<4}  reason: {sk[2]}')
        if len(skipped) > 30:
            print(f'  ... and {len(skipped) - 30} more')


if __name__ == '__main__':
    main()
