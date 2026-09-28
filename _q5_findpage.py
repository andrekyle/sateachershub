# -*- coding: utf-8 -*-
h=open('_mj23p1_audit/current_preview.html',encoding='utf-8').read()
pages=h.split('class="page"')
for i,p in enumerate(pages):
    print(i, 'Q5HEAD' if 'QUESTION 5' in p else '', '5Tours' if '5Tours' in p else '', 'qry5_4' if 'qry5_4' in p else '', 'rpt5_6' if 'rpt5_6' in p else '')
