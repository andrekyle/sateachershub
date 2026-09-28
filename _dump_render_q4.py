"""Fetch rendered preview via existing session cookie, dump Q4 block."""
import urllib.request, urllib.error, re, sys

PID = '8fe0ceee-4092-4c16-9126-506a62da55e1'
URL = f'http://127.0.0.1:5004/teacher/generator/{PID}/preview'

session_val = None
with open('cookies.txt', encoding='utf-8') as f:
    for ln in f:
        if not ln.strip() or ln.startswith('# '):
            continue
        parts = ln.rstrip('\n').split('\t')
        if len(parts) >= 7 and parts[5] == 'session':
            session_val = parts[6]
            break

if not session_val:
    print('no session cookie'); sys.exit(1)

req = urllib.request.Request(URL, headers={'Cookie': f'session={session_val}'})
try:
    html = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', errors='replace')
except urllib.error.HTTPError as e:
    print('HTTP', e.code, e.reason)
    sys.exit(1)

print('len=', len(html))

i = html.find('QUESTION 4')
if i < 0:
    print('QUESTION 4 not found in render')
    sys.exit(1)
j = html.find('QUESTION 5', i + 1)
if j < 0:
    j = html.find('TOTAL SECTION', i + 1)
seg = html[i:j if j > 0 else i + 30000]

seg = re.sub(r'<script.*?</script>', '', seg, flags=re.S)
seg = re.sub(r'<style.*?</style>', '', seg, flags=re.S)

# Iterate items, postitems, q-totals
pat = re.compile(
    r'<div class="(item [^"]*|q-postitem[^"]*|q-total|q-outro|section-total|match-block[^"]*|q-intro[^"]*|q-head[^"]*)"[^>]*>',
    re.S)

# Simpler: parse top-level item blocks via fixed pattern
print('\n--- Q4 items ---')
for m in re.finditer(r'<div class="item [^"]*"[^>]*data-qid="([^"]+)"[^>]*>(.*?)(?=<div class="item |<div class="q-postitem|<div class="q-outro|<div class="q-total|<div class="match-block|<div class="section-total|<div class="q-head)', seg, re.S):
    qid, body = m.group(1), m.group(2)
    num_m = re.search(r'<div class="num"[^>]*>([^<]+)</div>', body)
    marks_m = re.search(r'<div class="marks"[^>]*>([^<]*)</div>', body)
    body_m = re.search(r'<div class="body"[^>]*>(.*?)</div>\s*(?=<div class="marks"|<div class="q-figure|<div class="q-postitem|$)', body, re.S)
    fig_m = re.search(r'<div class="q-figure', body)
    body_text = ''
    if body_m:
        body_text = re.sub(r'<[^>]+>', ' ', body_m.group(1))
        body_text = re.sub(r'\s+', ' ', body_text).strip()
    cls_m = re.search(r'<div class="item ([^"]*)"', body) or re.match(r'.*?class="item ([^"]*)"', body)
    num = (num_m.group(1) if num_m else '?').strip()
    marks = (marks_m.group(1) if marks_m else '').strip()
    print(f'  {num:<8} marks={marks:<6} fig={"Y" if fig_m else "N"} body={body_text[:90]!r}')

# also print depth class for each item
print('\n--- depths ---')
for m in re.finditer(r'<div class="item ([^"]*)"', seg):
    print(' ', m.group(1)[:80])

print('\nq-total values:', re.findall(r'<div class="q-total"[^>]*>([^<]+)</div>', seg))
print('section-total:', re.findall(r'<div class="section-total"[^>]*>([^<]+)</div>', seg))
