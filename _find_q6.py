"""Find page+anchors for Q6.1 webpage example figure."""
import fitz
d = fitz.open('static/uploads/Computer Applications Technology P1 Nov 2025 Eng.pdf')
for i, p in enumerate(d):
    for anchor in [
        "Open the incomplete 6_1Home",
        "Your final web page should look like the example below",
        "Make the following changes",
        "6.1.1",
    ]:
        rs = p.search_for(anchor)
        if rs:
            print(f'pg {i+1}  {anchor!r}  -> y={rs[0].y0}-{rs[0].y1}')
