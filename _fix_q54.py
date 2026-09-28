"""Q5.4 memo: italicize the 'Benefit' and 'Limitation' sub-headings so the
memo cell matches the source image (bold-italic top heading + italic
sub-labels + numbered lists + right-aligned tick tail)."""
from app import app, db, QuestionBankItem

QID = '61c78f7a-baa7-45b9-a0f9-4536ab7b58dc'

NEW_ANSWER = (
    "ONE benefit and ONE limitation of using cloud computing\n"
    "<i>Benefit</i>\n"
    "(1) Access files and applications from anywhere with an internet connection\n"
    "(2) Save local storage space/no need to carry storage device\n"
    "(3) Collaboration and sharing of files\n"
    "(4) Work with the latest updated versions\n"
    "(5) Can be used on variety of platforms\n"
    "(6) Cloud providers often offer robust data backup and recovery services\n"
    "(7) Cost Savings: Less expensive to use cloud computing than to purchase the software\n"
    "(8) Synchronisation features\n"
    "\u2713 (Any one)\n"
    "<i>Limitation</i>\n"
    "(1) Slow internet connection may cause apps to load slower and not refresh on time\n"
    "(2) You no longer have control over security and backup\n"
    "(3) Uploading/saving to cloud can use up data\n"
    "(4) Free versions have limited storage/features/support\n"
    "\u2713 (Any one)"
)

with app.app_context():
    q = db.session.get(QuestionBankItem, QID)
    print('BEFORE marks=', q.marks)
    q.answer_text = NEW_ANSWER
    q.marks = 2
    db.session.commit()
    print('AFTER  marks=', q.marks)
    print('AFTER  A:')
    print(q.answer_text)
