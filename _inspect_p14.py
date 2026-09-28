"""Investigate page 14 layout to find the table region."""
import fitz
src = r"static\uploads\Computer Applications Technology P2 Nov 2025 Eng.pdf"
doc = fitz.open(src)
page = doc[13]

terms = ["9.4", "An incomplete spreadsheet", "is used to capture", "Week 1", "Week 2", "1:42", "1:00", "Total time", "#NAME?", "To calculate", "9.4.1", "9.4.2", "B7"]
for t in terms:
    hits = page.search_for(t)
    print(f"{t!r:35} -> {hits[:3]}")
