import pdfplumber, os

PDF = r"data/all_uploads/Computer Applications Technology P1 May-June 2025 Eng.pdf"
out = []
with pdfplumber.open(PDF) as pdf:
    out.append(f"PAGES: {len(pdf.pages)}")
    for i, p in enumerate(pdf.pages):
        out.append(f"\n===== PAGE {i+1} =====")
        txt = p.extract_text() or ""
        out.append(txt)
        if p.images:
            out.append(f"  [IMAGES on page {i+1}: {len(p.images)}]")
            for im in p.images:
                out.append(f"    x0={im['x0']:.0f} top={im['top']:.0f} w={im['width']:.0f} h={im['height']:.0f}")

with open("_p1_paper.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("wrote _p1_paper.txt;", len(out), "lines")
