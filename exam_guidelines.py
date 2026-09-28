"""
CAPS / DBE Examination Guidelines reference for Computer Applications Technology.

Source: "Computer Applications Technology – Examination Guidelines, Grade 12, 2021"
(DBE) and the CAPS document. These constants define the canonical structure
that every generated exam paper in this app must follow.

Usage:
    from exam_guidelines import CAPS_PAPER_TEMPLATES, CAPS_GUIDELINES
"""

# ---------------------------------------------------------------------------
# 1. Cognitive demand & difficulty mix (Section 2 of the guidelines).
#    Used by the question bank / paper-generator to validate the spread of
#    questions across cognitive levels.
# ---------------------------------------------------------------------------
COGNITIVE_LEVELS = {
    "C1": {
        "label": "Knowledge / Remembering / Routine procedures",
        "target_pct": 30,        # ±30% of paper marks
        "difficulty_split": {"D1": 10, "D2": 10, "D3": 10, "D4": 0},
    },
    "C2": {
        "label": "Understanding / Applying / Multi-step procedures",
        "target_pct": 40,
        "difficulty_split": {"D1": 10, "D2": 15, "D3": 13, "D4": 2},
    },
    "C3": {
        "label": "Analysing / Evaluating / Creating / Problem-solving",
        "target_pct": 30,
        "difficulty_split": {"D1": 10, "D2": 10, "D3": 7, "D4": 3},
    },
}

DIFFICULTY_LEVELS = {
    "D1": "Easy for the average Grade 12 candidate",
    "D2": "Moderately challenging for the average Grade 12 candidate",
    "D3": "Difficult for the average Grade 12 candidate",
    "D4": "Very difficult – distinguishes A-grade candidates",
}

# Action verbs with their required cognitive treatment.
ACTION_VERBS = {
    "analyse":     "Break into parts; show how parts relate and why important.",
    "arrange":     "Order items in a meaningful sequence (size, time, capacity, …).",
    "categorise":  "Group concepts that share characteristics or function.",
    "classify":    "Group concepts that share characteristics or function.",
    "compare":     "Show BOTH similarities AND differences.",
    "differentiate": "Show BOTH similarities AND differences.",
    "define":      "Give a short, formal meaning of the term/concept.",
    "describe":    "Give the main features by expanding the statement.",
    "diagram":     "Draw and label a graph / chart / diagram.",
    "discuss":     "Present arguments for AND against; reach a conclusion.",
    "evaluate":    "Give an opinion; show advantages and disadvantages.",
    "explain":     "Give full reasons / justification; how and why it works.",
    "give":        "Give one or more reason(s)/example(s) in a full sentence.",
    "identify":    "Recognise and name; pick out from other information.",
    "justify":     "State why and give reasons for the claim.",
    "name":        "One-word answer per item.",
    "list":        "Two or more one-word/short-phrase items.",
    "motivate":    "Provide reasons / justification for the answer.",
    "suggest":     "Analyse the case and propose possible solutions/ideas.",
    "state":       "Give a brief, factual answer (no full discussion needed).",
}

# Topics / concepts that must NO LONGER be examined (Section 4.3.2).
EXCLUDED_CONCEPTS = [
    "CRT monitors", "Digital migration", "Encarta", "Fax / Fax modems",
    "FireWire", "Freeware/Shareware software (as a stand-alone topic)",
    "FTP", "MICR", "MySpace", "OMR", "PDA", "RSS Feeds",
    "Second Life", "Stand-alone vs integrated office suites",
    "Trackball mouse", "Widgets",
    # Blurred concepts no longer asked:
    "Comparisons between printer types",
    "802.11 a/b/g/n details",
    "Plug-in vs add-on (use 'add-on')",
    "Phablet vs tablet",
    "LCD vs LED differentiation",
]

# ---------------------------------------------------------------------------
# 2. Standard structure of every generated paper.
#    These templates mirror the DBE Paper 1 (Practical) and Paper 2 (Theory)
#    structures exactly, including section letter, title, mark allocation
#    and instruction text.
# ---------------------------------------------------------------------------

PAPER2_DEFAULT_INSTRUCTIONS = (
    "This question paper consists of:\n"
    "  SECTION A (25)\n"
    "  SECTION B (75)\n"
    "  SECTION C (50)\n"
    "\n"
    "1. Answer ALL the questions.\n"
    "2. Number the answers correctly according to the numbering system used in this question paper.\n"
    "3. Start EACH question on a NEW page.\n"
    "4. Do NOT write in the right-hand margin of the ANSWER BOOK.\n"
    "5. Leave a line after EACH subquestion.\n"
    "6. Generally, one mark is allocated per fact; a 2-mark question therefore requires TWO facts.\n"
    "7. Read the questions carefully. Do NOT give more answers than the question requires.\n"
    "8. All answers MUST be related to Computer Applications Technology.\n"
    "9. Unless otherwise specified, answers such as 'cheaper', 'slower'/'faster' will NOT be accepted.\n"
    "10. Do NOT use brand names in your answers, unless specifically required.\n"
    "11. Write neatly and legibly."
)

PAPER1_DEFAULT_INSTRUCTIONS = (
    "1. Owing to the nature of this practical examination, it is important to note that, even if you "
    "complete the examination early, you will NOT be permitted to leave the examination room until "
    "all administrative functions associated with the examination have been finalised.\n"
    "2. Enter your examination number and centre number in the header of EVERY document that you create or save.\n"
    "3. The invigilator will give you a CD/DVD/flash disk containing all the files needed for the "
    "examination OR you will be told where on the hard drive the files can be found. If a CD/DVD has "
    "been issued to you, you must write your examination number and centre number on the CD/DVD.\n"
    "4. A copy of the master files will be available from the invigilator. Should there be any problems "
    "with a file, you may request another copy from the invigilator.\n"
    "5. This question paper consists of SEVEN questions.\n"
    "6. Answer ALL the questions.\n"
    "7. Save your work regularly.\n"
    "8. Read through each question before answering or solving the problem. Do NOT do more than is required.\n"
    "9. At the end of the examination, you must hand in the CD/DVD/flash disk given to you by the invigilator with ALL your answer files saved onto it. "
    "Ensure that ALL the files can be read.\n"
    "10. Note that no printing is required.\n"
    "11. During the examination, you may make use of the help functions of the programs you are using. "
    "You may NOT use any other resource material.\n"
    "12. Unless instructed otherwise, formulae and/or functions must be used for ALL calculations. "
    "Use absolute cell references only where necessary to ensure that formulae are correct when copied.\n"
    "13. The examination folder/data disk you receive with this question paper will contain a folder and the files listed below. "
    "Ensure that you have the folder and ALL the files before you begin this examination."
)

# Each section template entry produces one entry in `paper.sections` JSON.
# Marks are TARGETS (the user fills in the actual questions from the bank).
CAPS_PAPER_TEMPLATES = {
    "p2_grade12": {
        "label": "CAPS Paper 2 – Theory (Grade 12, 150 marks)",
        "subject": "Computer Applications Technology",
        "paper_number": "P2",
        "grade": 12,
        "duration_minutes": 180,
        "total_marks": 150,
        "instructions": PAPER2_DEFAULT_INSTRUCTIONS,
        "sections": [
            {
                "title": "SECTION A: SHORT QUESTIONS",
                "instructions": "Answer ALL the questions in this section.",
                "marks_target": 25,
                "subsections": [
                    {
                        "title": "QUESTION 1: MULTIPLE-CHOICE QUESTIONS",
                        "instructions": (
                            "Various options are given as possible answers to the following questions. "
                            "Choose the answer and write only the letter (A–D) next to the question "
                            "numbers (1.1 to 1.10) in the ANSWER BOOK, e.g. 1.11 D."
                        ),
                        "marks_target": 10,
                        "kind": "mcq",
                    },
                    {
                        "title": "QUESTION 2: MATCHING ITEMS",
                        "instructions": (
                            "Choose a term/concept from COLUMN B that matches the description in "
                            "COLUMN A. Write only the letter (A–T) next to the question numbers "
                            "(2.1 to 2.10) in the ANSWER BOOK, e.g. 2.11 U."
                        ),
                        "marks_target": 10,
                        "kind": "matching",
                    },
                    {
                        "title": "QUESTION 3: TRUE/FALSE ITEMS",
                        "instructions": (
                            "Indicate whether the following statements are TRUE or FALSE. "
                            "Write 'true' or 'false' next to the question numbers (3.1 to 3.5) in the "
                            "ANSWER BOOK. Correct the statement if it is FALSE by changing the "
                            "underlined word(s) to make the statement TRUE. (Do NOT simply use the "
                            "word 'NOT' to change the statement.) NO mark will be awarded if only "
                            "FALSE is written."
                        ),
                        "marks_target": 5,
                        "kind": "true_false",
                    },
                ],
            },
            {
                "title": "SECTION B",
                "instructions": "Answer ALL the questions in this section.",
                "marks_target": 75,
                "subsections": [
                    {
                        "title": "QUESTION 4: SYSTEMS TECHNOLOGIES",
                        "marks_target": 25,
                        "topic": "Systems Technologies",
                    },
                    {
                        "title": "QUESTION 5: INTERNET AND NETWORK TECHNOLOGIES",
                        "marks_target": 15,
                        "topic": "Internet and Network Technologies",
                    },
                    {
                        "title": "QUESTION 6: INFORMATION MANAGEMENT",
                        "marks_target": 10,
                        "topic": "Information Management",
                    },
                    {
                        "title": "QUESTION 7: SOCIAL IMPLICATIONS",
                        "marks_target": 10,
                        "topic": "Social Implications",
                    },
                    {
                        "title": "QUESTION 8: SOLUTION DEVELOPMENT",
                        "marks_target": 15,
                        "topic": "Solution Development",
                    },
                ],
            },
            {
                "title": "SECTION C: INTEGRATED SCENARIO",
                "instructions": (
                    "Two real-life scenarios are presented. Questions covering ALL topics will be "
                    "examined. Answer ALL the questions."
                ),
                "marks_target": 50,
                "subsections": [
                    {
                        "title": "QUESTION 9: INTEGRATED SCENARIO",
                        "marks_target": 25,
                        "topic": "Integrated Scenario",
                    },
                    {
                        "title": "QUESTION 10: INTEGRATED SCENARIO",
                        "marks_target": 25,
                        "topic": "Integrated Scenario",
                    },
                ],
            },
        ],
    },

    "p1_grade12": {
        "label": "CAPS Paper 1 – Practical (Grade 12, 150 marks)",
        "subject": "Computer Applications Technology",
        "paper_number": "P1",
        "grade": 12,
        "duration_minutes": 180,
        "total_marks": 150,
        "instructions": PAPER1_DEFAULT_INSTRUCTIONS,
        "sections": [
            {
                "title": "QUESTION 1: WORD PROCESSING",
                "marks_target": 45,
                "topic": "Word Processing",
            },
            {
                "title": "QUESTION 2: SPREADSHEETS",
                "marks_target": 40,
                "topic": "Spreadsheets",
            },
            {
                "title": "QUESTION 3: DATABASES",
                "marks_target": 35,
                "topic": "Databases",
            },
            {
                "title": "QUESTION 4: WEB DEVELOPMENT (HTML)",
                "marks_target": 15,
                "topic": "Web Development",
                "instructions": (
                    "An information sheet with HTML tags will be provided. ANY HTML QUESTION "
                    "ANSWERED USING A WORD PROCESSOR OR OTHER WEB DESIGN SOFTWARE WILL NOT BE MARKED."
                ),
            },
            {
                "title": "QUESTION 5: GENERAL",
                "marks_target": 15,
                "topic": "General / Integrated",
                "instructions": (
                    "Integration and application of techniques, knowledge and procedural skills "
                    "across all of the applications studied."
                ),
            },
        ],
    },
}

# Convenience: the canonical Section B topic order for Paper 2.
PAPER2_SECTION_B_TOPICS = [
    "Systems Technologies",
    "Internet and Network Technologies",
    "Information Management",
    "Social Implications",
    "Solution Development",
]


def flatten_template(key: str) -> list[dict]:
    """Return the template's section list flattened into the
    `sections` JSON shape used by the GeneratedPaper model:
    [{title, instructions, question_ids: []}, ...]
    Subsections become top-level sections so each gets its own page in the
    final paper (matching DBE convention)."""
    tpl = CAPS_PAPER_TEMPLATES.get(key)
    if not tpl:
        return []
    out: list[dict] = []
    for sec in tpl["sections"]:
        subs = sec.get("subsections")
        if subs:
            # Add a banner for the section letter.
            out.append({
                "title": sec["title"],
                "instructions": sec.get("instructions", ""),
                "question_ids": [],
                "is_banner": True,
                "marks_target": sec.get("marks_target"),
            })
            for sub in subs:
                out.append({
                    "title": sub["title"],
                    "instructions": sub.get("instructions", ""),
                    "question_ids": [],
                    "marks_target": sub.get("marks_target"),
                    "topic": sub.get("topic"),
                    "kind": sub.get("kind"),
                })
        else:
            out.append({
                "title": sec["title"],
                "instructions": sec.get("instructions", ""),
                "question_ids": [],
                "marks_target": sec.get("marks_target"),
                "topic": sec.get("topic"),
            })
    return out


# ---------------------------------------------------------------------------
# 3. Compact reference dict bundled into templates / API responses.
# ---------------------------------------------------------------------------
CAPS_GUIDELINES = {
    "source": "DBE Examination Guidelines – Computer Applications Technology, Grade 12 (2021)",
    "papers": {
        "P1": {
            "name": "Practical",
            "marks": 150,
            "duration_minutes": 180,
            "scope": {
                "Word processing":  45,
                "Spreadsheets":     40,
                "Databases":        35,
                "Web Development":  15,
                "General":          15,
            },
        },
        "P2": {
            "name": "Theory",
            "marks": 150,
            "duration_minutes": 180,
            "scope": {
                "Section A – Short Questions (MCQ + Matching + True/False)": 25,
                "Section B – Systems Technologies":         25,
                "Section B – Internet and Network Technologies": 15,
                "Section B – Information Management":       10,
                "Section B – Social Implications":          10,
                "Section B – Solution Development":         15,
                "Section C – Integrated Scenario (2 × ~25)": 50,
            },
        },
    },
    "cognitive_levels": COGNITIVE_LEVELS,
    "difficulty_levels": DIFFICULTY_LEVELS,
    "action_verbs": ACTION_VERBS,
    "excluded_concepts": EXCLUDED_CONCEPTS,
}
