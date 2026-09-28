"""Extract screenshots from page 11 of CAT P2 Nov 2025 PDF for Q8.3 and Q8.5."""
import fitz, os
src = r"static\uploads\Computer Applications Technology P2 Nov 2025 Eng.pdf"
out_dir = r"static\uploads\cat_p2_n25"
os.makedirs(out_dir, exist_ok=True)
doc = fitz.open(src)
# The user's image shows page labelled 11 (footer indicates "QUESTION 8: SOLUTION DEVELOPMENT")
# Try pages 10, 11 (0-indexed 9, 10) — print which has Q8
for pno in range(9, 13):
    page = doc[pno]
    txt = page.get_text()[:200]
    print(f"--- page {pno+1} ---")
    print(repr(txt))
