import re, html
with open('_paper.html', encoding='utf-8') as f:
    h = f.read()
# strip tags but keep structure
t = re.sub(r'<script[^>]*>.*?</script>', '', h, flags=re.S|re.I)
t = re.sub(r'<style[^>]*>.*?</style>', '', t, flags=re.S|re.I)
t = re.sub(r'<br\s*/?>', '\n', t, flags=re.I)
t = re.sub(r'</(p|div|tr|li|h[1-6])>', '\n', t, flags=re.I)
t = re.sub(r'<[^>]+>', ' ', t)
t = html.unescape(t)
t = re.sub(r'[ \t]+', ' ', t)
t = re.sub(r'\n{2,}', '\n\n', t)
print(t.strip())
