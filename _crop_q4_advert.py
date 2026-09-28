"""Crop the StellarX advertisement box from PDF page 7 and save as the Q4.1 figure."""
import pdfplumber

PDF = 'static/uploads/Computer Applications Technology P2 May-June 2025  Eng.pdf'
OUT = 'static/uploads/paper_images/p2_2025/q4_1_advert.png'

# Outer border bbox (with small padding), in PDF points
bbox = (99, 167, 530, 364)

with pdfplumber.open(PDF) as pdf:
    page = pdf.pages[6]
    cropped = page.crop(bbox)
    im = cropped.to_image(resolution=400)
    im.save(OUT)
    print('saved', OUT)
