# -*- coding: utf-8 -*-
import json, re
from app import app, db, GeneratedPaper, QuestionBankItem
PID = '2b687490-9157-4e10-b0c9-2bab1ee303fd'

A = {}
# Q3.7 (idx26) — clean garbled truth table to formula heading + 6 marked bullets
A[26] = (
 'Cell K6:\n'
 '=IF(E6<TODAY(),"Complete",IF(E6-TODAY()<=60,"Notify","*"))\n'
 'OR\n'
 '=IF(E6>=TODAY(),IF((E6-TODAY())<=60,"Notify","*"),"Complete")\n'
 '\u2022 Function: Nested IF  1\n'
 '\u2022 First condition  1\n'
 '\u2022 Output for first condition  1\n'
 '\u2022 Second condition  1\n'
 '\u2022 Output for second condition  1\n'
 '\u2022 Output for third condition  1'
)
# Q5
A[34] = 'Field: Coverage\n\u2022 Field size changed to Decimal  1'
A[35] = "Field: PollutionType\n\u2022 Display control: Combo Box  1\n\u2022 Row Source: 'Air', 'Land', 'Water'  1"
A[36] = ('Field: Level\n'
 'Validation rule: Between 100 And 1000 OR >=100 and <=1000 OR >99 and <1001\n'
 '\u2022 100 and above  1\n\u2022 And  1\n\u2022 1000 and below  1')
A[37] = '\u2022 Field name: Evidence  1\n\u2022 Field type: Attachment, Hyperlink  1'
A[38] = ("\u2022 Form heading changed to 'Survey'  1\n"
 '\u2022 Only date appears in the form footer  2\n'
 '\u2022 Ion theme applied to the form  1\n'
 '\u2022 YearBorn field format changed to Medium Date  1')
A[39] = ('\u2022 Group by RecyclingActivity  1\n'
 '\u2022 Function AVG in DropOff  1\n'
 '\u2022 Average value displays no decimal places  1')
A[40] = ('\u2022 Only Name, Surname, (YearBorn,) Knowledge, RecyclingActivity, DropOff fields display  1\n'
 '\u2022 Sorted by Surname ascending  1\n'
 "\u2022 Knowledge field criteria: 'Yes'  1\n"
 '\u2022 OR  1\n'
 "\u2022 RecyclingActivity field criteria: 'Very Active'  1\n"
 '\u2022 AND  1\n'
 '\u2022 DropOff field criteria: 15  1\n'
 '(Expected number of records: 113)')
A[41] = ('\u2022 YearBorn field criteria: >#1990/12/31#  1\n'
 'OR >=#1991/01/01#\n'
 'OR YEAR([YearBorn])>1990\n'
 '\u2022 Calculated field: NewDrop:[DropOff]*10/100+[DropOff]\n'
 'OR [DropOff]*110/100  OR  [DropOff]*1.1  OR  [DropOff]+[DropOff]*0.1\n'
 '\u2022 NewDrop:  1\n'
 '\u2022 [DropOff]  1\n'
 '\u2022 *  1\n'
 '\u2022 10/100 + [DropOff] OR 110/100 OR 1.1  1\n'
 '(Expected number of records: 58)')
A[42] = ('\u2022 DropOff field inserted and moved to correct position  1\n'
 '\u2022 Grouping inserted on RecyclingActivity  1\n'
 '\u2022 Any colour applied to the page header  1\n'
 '\u2022 Sorted by Surname  1\n'
 '\u2022 Function inserted in group header  1\n'
 '\u2022 = COUNT(*) OR any other field  2')
# Q6 — restore HTML code lines + clean bullets
A[44] = ('Title tags\n<title>12345678</title>\n'
 '\u2022 Title tags  1\n\u2022 Examination number inserted between the tags  1')
A[45] = ('Font colour: Heading: The Global Crisis of Plastic Pollution\n'
 '<h1><font color="red">The Global Crisis of Plastic Pollution </font></h1>\n'
 '\u2022 Font set to a red colour  1')
A[46] = ('Picture\n<img src="6_1Plastic.jpg" height="200" width="300"/>\n'
 '\u2022 Attribute scr changed to src  1\n\u2022 File extension png changed to jpg  1')
A[47] = ('Table: rowspan\n'
 '<table border="5" width="300" cellpadding="10">\n<tr>\n'
 '<td rowspan="3">Tons per year</td>\n<td>China</td>\n'
 '\u2022 Only column inserted <td>\u2026</td>  1\n'
 "\u2022 Text 'Tons per year' inserted in first column  1\n"
 '\u2022 Rowspan="3"  1')
A[48] = ('<body>\n<br/>\n<a href="6_1Clean.html">Home Page</a>\n'
 '<h2>Types of pollution</h2>\n<hr size="5" color="Black"/>\n<ol>\n'
 '<li>Air pollution</li>\n<ul type="square">\n<li>Ground-level ozone</li>\n'
 '<li>Carbon monoxide</li>\n<li>Sulphur oxides</li>\n<li>Nitrogen oxides</li>\n'
 '<li>Lead</li>\n</ul>\n<li>Water pollution</li>\n<li>Light pollution</li>\n'
 '<li>Noise pollution</li>\n<li>Soil pollution</li>\n</ol>\n</body>\n'
 '\u2022 Hyperlink: Tag for hyperlink correctly inserted  1\n'
 '\u2022 Horizontal line: Horizontal rule tag  1\n'
 '\u2022 size="5" (Accept any size larger than "1")  1\n'
 '\u2022 Unordered list <ul>\u2026</ul> tags  1\n'
 '\u2022 Type="square"  1\n'
 '\u2022 <li>Lead</li>  1')
# Q7
A[50] = ('Form controls\n'
 '\u2022 Form field set to Current Date (Alt + F9, Form text Date)  1\n'
 "\u2022 '7' and '14' options appear in the drop-down form field control  1")
A[51] = ('Mail merge (Expect 21 letters)\n'
 '\u2022 7Letter linked to 7Company spreadsheet  1\n'
 "\u2022 Recipients' list is filtered\n"
 '\u2022 Level = very high  1\n'
 "\u2022 Or OR contains 'high'  1\n"
 '\u2022 Level = high  1\n'
 '\u2022 Merge fields inserted for Company name and Level  1\n'
 '\u2022 Mail merge completed  1\n'
 "(SELECT * from 'Sheet1$' WHERE 'Level'='very high' OR 'Level'='high'/'Level' LIKE '%high%')")
A[52] = ('Cell D3:\n=IF(AND(B3="Low",MONTH(C3)=11),A3," ")\n'
 '\u2022 Criteria: Test if the level is low  1\n'
 '\u2022 Criteria: Test if the month is 11  2')
A[53] = ('Filter\n\u2022 Filtered on column A: Very High  1\n'
 '\u2022 Filtered on column B: 2021  1\n\u2022 Names sorted alphabetically  1')
A[54] = '\u2022 7Picture file extracted  1'

with app.app_context():
    p = GeneratedPaper.query.get(PID)
    qids = json.loads(p.sections)[0]['question_ids']
    for i, txt in A.items():
        q = db.session.get(QuestionBankItem, qids[i])
        q.answer_text = txt
    # Strip trailing divider chrome from idx30 (4.4) and idx9 (1.10)
    q30 = db.session.get(QuestionBankItem, qids[30])
    q30.answer_text = re.sub(r'\n?\s*Graph worksheet\s*$', '', q30.answer_text or '').rstrip()
    q9 = db.session.get(QuestionBankItem, qids[9])
    # drop the two general-instruction lines merged after the bullet
    lines9 = [ln for ln in (q9.answer_text or '').split('\n')
              if not ln.strip().lower().startswith(('check the accuracy','ignore spelling'))]
    q9.answer_text = '\n'.join(lines9).rstrip()
    db.session.commit()
    # verify per-Q sums (info only)
    splits = json.loads(p.sections)[0]['splits'] + [len(qids)]
    for qi in range(7):
        tot = sum(db.session.get(QuestionBankItem, qids[k]).marks or 0 for k in range(splits[qi], splits[qi+1]))
        print(f'Q{qi+1} item-sum =', tot)
    print('done')
