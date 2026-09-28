import threading, time, sys
from werkzeug.serving import make_server
from flask.sessions import SecureCookieSessionInterface
import app as appmod

PID = "60471f83-d846-48f7-9195-629c43e3ab8f"
OWNER = "951c278b-2d76-4969-b0d4-6271479bf397"
PORT = 5099
PAGES = sys.argv[1:] if len(sys.argv) > 1 else None  # optional list of page numbers

srv = make_server('127.0.0.1', PORT, appmod.app, threaded=True)
t = threading.Thread(target=srv.serve_forever, daemon=True)
t.start()
time.sleep(1.5)

# auth cookie
ser = SecureCookieSessionInterface().get_signing_serializer(appmod.app)
cookie = ser.dumps({'_user_id': OWNER, '_fresh': True, 'user_id': OWNER, 'user_role': 'teacher'})

from playwright.sync_api import sync_playwright
url = f"http://127.0.0.1:{PORT}/teacher/generator/{PID}/preview?embed=1&print=1"
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context()
    ctx.add_cookies([{'name': 'session', 'value': cookie, 'domain': '127.0.0.1', 'path': '/'}])
    pg = ctx.new_page()
    pg.goto(url, wait_until='networkidle', timeout=60000)
    pg.pdf(path="_p1_preview.pdf", format="A4", print_background=True)
    b.close()

srv.shutdown()
print("rendered _p1_preview.pdf")

# convert selected pages to PNG
import pdfplumber
pages = [int(x) for x in PAGES] if PAGES else list(range(1, 25))
with pdfplumber.open("_p1_preview.pdf") as pdf:
    print("preview pages:", len(pdf.pages))
    for n in pages:
        if n <= len(pdf.pages):
            pdf.pages[n-1].to_image(resolution=110).save(f"_pv_p{n}.png")
            print("saved page", n)
