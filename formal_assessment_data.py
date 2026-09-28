"""
South African Teachers Hub — Formal Assessment (Programme of Assessment) data.

Source: DBE CAPS, Section 4 — Programme of Assessment, as reflected in the
2025 / 2026 Annual Teaching Plans (ATPs). Weightings below are the standard
CAPS values currently in force for the National Senior Certificate.

Data shape:
    FORMAL_ASSESSMENT['Subject Name'] = {
        'label': str,
        'grades': [
            {
                'heading': 'Grade 10 and 11',  # or 'Grade 12'
                'during':  { 'pct': int, 'cells': [<cell>, ...] },
                'eoy':     { 'pct': int, 'cells': [<cell>, ...] },  # optional
                'note':    str,                                     # optional
            },
            ...
        ]
    }

A <cell> is:
    { 'name': str, 'pct': int|None, 'lines': [str, ...] }

The template lays each table out as a single HTML table with
(len(during.cells) + len(eoy.cells)) columns. If 'eoy' is omitted the table
is 100 % SBA (e.g. Life Orientation in Grade 12).
"""


# --------------------------------------------------------------------------
# Common building blocks (re-used across many subjects)
# --------------------------------------------------------------------------

_STD_THEORY_G1011_DURING = {
    'pct': 25,
    'cells': [
        {'name': 'SBA tasks', 'pct': 25,
         'lines': ['2 tests', '1 assignment / project / case study',
                   '1 mid-year exam']}
    ],
}

_STD_THEORY_G12_DURING = {
    'pct': 25,
    'cells': [
        {'name': 'SBA tasks', 'pct': 25,
         'lines': ['2 tests', '1 assignment / project / research task',
                   '2 internal exams (mid-year + trial)']}
    ],
}


# --------------------------------------------------------------------------
# Per-subject Programme of Assessment
# --------------------------------------------------------------------------

FORMAL_ASSESSMENT = {

    # ----- Computer Applications Technology --------------------------------
    'Computer Applications Technology': {
        'label': 'Computer Applications Technology',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 40,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 40,
                         'lines': ['4 tests (1 may be an alternative form: open-book, case study, survey)',
                                   '1 mid-year exam']},
                    ],
                },
                'eoy': {
                    'pct': 60,
                    'cells': [
                        {'name': 'Practical Assessment Task', 'pct': 20,
                         'lines': ['Information-management project providing a solution to a scenario, using all CAT applications']},
                        {'name': 'Practical exam', 'pct': 20,
                         'lines': ['2.5 – 3 hours', 'Solution Development (Word, Excel, Access, HTML)']},
                        {'name': 'Written exam', 'pct': 20,
                         'lines': ['2.5 – 3 hours', 'Theory of all CAT topics']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['3 tests (1 may be an alternative form: open-book, case study, survey)',
                                   '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Practical Assessment Task', 'pct': 25,
                         'lines': ['Information-management project providing a solution to a scenario, using all CAT applications']},
                        {'name': 'Practical exam (Paper 1)', 'pct': 25,
                         'lines': ['3 hours · 180 marks', 'Solution Development']},
                        {'name': 'Written exam (Paper 2)', 'pct': 25,
                         'lines': ['3 hours · 150 marks', 'Theory of all CAT topics']},
                    ],
                },
            },
        ],
    },

    # ----- Information Technology -----------------------------------------
    'Information Technology': {
        'label': 'Information Technology',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['5 tests', '1 mid-year exam']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Practical Assessment Task', 'pct': 25,
                         'lines': ['Software-development project covering the planning cycle and software-engineering principles']},
                        {'name': 'Written exam (Paper 2)', 'pct': 25,
                         'lines': ['2 – 3 hours', 'Theory of all IT topics']},
                        {'name': 'Practical exam (Paper 1)', 'pct': 25,
                         'lines': ['3 hours', 'Solution Development (Delphi / Java)']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['4 tests', '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Practical Assessment Task', 'pct': 25,
                         'lines': ['Software-development project covering the planning cycle and software-engineering principles']},
                        {'name': 'Written exam (Paper 2)', 'pct': 25,
                         'lines': ['3 hours · 150 marks', 'Theory of all IT topics']},
                        {'name': 'Practical exam (Paper 1)', 'pct': 25,
                         'lines': ['3 hours · 150 marks', 'Solution Development']},
                    ],
                },
            },
        ],
    },

    # ----- Mathematics ----------------------------------------------------
    'Mathematics': {
        'label': 'Mathematics',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '1 assignment', '1 investigation or project',
                                   '1 mid-year exam']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1', 'pct': 37.5,
                         'lines': ['2 hours · 100 marks (Gr 10) / 3 hours · 150 marks (Gr 11)',
                                   'Algebra, Equations & Inequalities, Patterns, Functions, Finance, Calculus prep, Probability']},
                        {'name': 'Paper 2', 'pct': 37.5,
                         'lines': ['2 hours · 100 marks (Gr 10) / 3 hours · 150 marks (Gr 11)',
                                   'Trigonometry, Analytical Geometry, Euclidean Geometry, Statistics, Measurement']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '1 assignment / investigation / project',
                                   '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1', 'pct': 37.5,
                         'lines': ['3 hours · 150 marks',
                                   'Algebra & Equations, Sequences & Series, Functions, Calculus, Finance, Probability']},
                        {'name': 'Paper 2', 'pct': 37.5,
                         'lines': ['3 hours · 150 marks',
                                   'Statistics, Analytical Geometry, Trigonometry, Euclidean Geometry']},
                    ],
                },
            },
        ],
    },

    # ----- Mathematical Literacy ------------------------------------------
    'Mathematical Literacy': {
        'label': 'Mathematical Literacy',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '1 assignment', '1 investigation or project',
                                   '1 mid-year exam']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1', 'pct': 37.5,
                         'lines': ['1.5 hours (Gr 10) / 2 hours (Gr 11) · 75 / 100 marks',
                                   'Basic skills topics']},
                        {'name': 'Paper 2', 'pct': 37.5,
                         'lines': ['1.5 hours (Gr 10) / 2 hours (Gr 11) · 75 / 100 marks',
                                   'Application topics']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '1 assignment / investigation',
                                   '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1', 'pct': 37.5,
                         'lines': ['3 hours · 150 marks',
                                   'Finance, Measurement, Maps & Plans, Data Handling, Probability']},
                        {'name': 'Paper 2', 'pct': 37.5,
                         'lines': ['3 hours · 150 marks',
                                   'Finance, Measurement, Maps & Plans, Data Handling, Probability (application contexts)']},
                    ],
                },
            },
        ],
    },

    # ----- Physical Sciences ----------------------------------------------
    'Physical Sciences': {
        'label': 'Physical Sciences',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '2 practical investigations or experiments',
                                   '1 project', '1 mid-year exam']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1 (Physics)', 'pct': 37.5,
                         'lines': ['2 hours · 100 marks (Gr 10) / 3 hours · 150 marks (Gr 11)']},
                        {'name': 'Paper 2 (Chemistry)', 'pct': 37.5,
                         'lines': ['2 hours · 100 marks (Gr 10) / 3 hours · 150 marks (Gr 11)']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '2 practical activities',
                                   '1 project', '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1 (Physics)', 'pct': 37.5,
                         'lines': ['3 hours · 150 marks', 'Mechanics, Waves & Sound, Electricity & Magnetism']},
                        {'name': 'Paper 2 (Chemistry)', 'pct': 37.5,
                         'lines': ['3 hours · 150 marks', 'Organic Chemistry, Reaction Rate, Chemical Equilibrium, Acids & Bases, Electrochemistry']},
                    ],
                },
            },
        ],
    },

    # ----- Life Sciences --------------------------------------------------
    'Life Sciences': {
        'label': 'Life Sciences',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '2 practical tasks (1 must be data handling)',
                                   '1 project / assignment / case study', '1 mid-year exam']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1', 'pct': 37.5,
                         'lines': ['2 hours · 100 marks (Gr 10) / 2.5 hours · 150 marks (Gr 11)']},
                        {'name': 'Paper 2', 'pct': 37.5,
                         'lines': ['2 hours · 100 marks (Gr 10) / 2.5 hours · 150 marks (Gr 11)']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '2 practical tasks',
                                   '1 project / assignment',
                                   '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1', 'pct': 37.5,
                         'lines': ['2.5 hours · 150 marks',
                                   'Meiosis, Reproduction, Genetics, Evolution, Human Endocrine System']},
                        {'name': 'Paper 2', 'pct': 37.5,
                         'lines': ['2.5 hours · 150 marks',
                                   'DNA & Protein Synthesis, Nervous System, Senses, Homeostasis, Plant Responses, Population & Community Ecology, Human Impact']},
                    ],
                },
            },
        ],
    },

    # ----- Accounting -----------------------------------------------------
    'Accounting': {
        'label': 'Accounting',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '1 project (Companies)',
                                   '1 case study / presentation', '1 mid-year exam']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'End-of-Year exam', 'pct': 75,
                         'lines': ['2 hours · 150 marks (Gr 10) / 3 hours · 300 marks (Gr 11)',
                                   'All topics']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '1 project (Companies)',
                                   '1 case study', '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'End-of-Year exam', 'pct': 75,
                         'lines': ['3 hours · 300 marks',
                                   'Financial Accounting, Managerial Accounting, Managing Resources']},
                    ],
                },
            },
        ],
    },

    # ----- Business Studies -----------------------------------------------
    'Business Studies': {
        'label': 'Business Studies',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '1 project',
                                   '1 case study / presentation / research task',
                                   '1 mid-year exam']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'End-of-Year exam', 'pct': 75,
                         'lines': ['2 hours · 200 marks (Gr 10) / 3 hours · 300 marks (Gr 11)',
                                   'All four main topics']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '1 project',
                                   '1 case study / presentation',
                                   '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'End-of-Year exam', 'pct': 75,
                         'lines': ['3 hours · 300 marks',
                                   'Business Environments, Operations, Roles, Ventures']},
                    ],
                },
            },
        ],
    },

    # ----- Economics ------------------------------------------------------
    'Economics': {
        'label': 'Economics',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '1 project',
                                   '1 case study / data response',
                                   '1 mid-year exam']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1 (Macroeconomics)', 'pct': 37.5,
                         'lines': ['1.5 hours · 100 marks (Gr 10) / 2 hours · 150 marks (Gr 11)']},
                        {'name': 'Paper 2 (Microeconomics & Contemporary)', 'pct': 37.5,
                         'lines': ['1.5 hours · 100 marks (Gr 10) / 2 hours · 150 marks (Gr 11)']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '1 project',
                                   '1 case study / data response',
                                   '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1 (Macroeconomics & Economic Pursuits)', 'pct': 37.5,
                         'lines': ['2 hours · 150 marks']},
                        {'name': 'Paper 2 (Microeconomics & Contemporary Issues)', 'pct': 37.5,
                         'lines': ['2 hours · 150 marks']},
                    ],
                },
            },
        ],
    },

    # ----- Geography ------------------------------------------------------
    'Geography': {
        'label': 'Geography',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '1 mapwork task',
                                   '1 research / project task',
                                   '1 mid-year exam']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1 (Theory)', 'pct': 56.25,
                         'lines': ['2 hours · 150 marks (Gr 10) / 3 hours · 225 marks (Gr 11)',
                                   'Geomorphology, Climatology, Settlement & Economic Geography']},
                        {'name': 'Paper 2 (Mapwork)', 'pct': 18.75,
                         'lines': ['1 hour · 50 marks (Gr 10) / 1.5 hours · 75 marks (Gr 11)',
                                   'Topographic & orthophoto map skills']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '1 mapwork task',
                                   '1 research task',
                                   '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1 (Theory)', 'pct': 56.25,
                         'lines': ['3 hours · 225 marks',
                                   'Climate & Weather, Geomorphology, Settlement, Economic Geography']},
                        {'name': 'Paper 2 (Mapwork)', 'pct': 18.75,
                         'lines': ['1.5 hours · 75 marks',
                                   'Topographic & orthophoto map skills, GIS']},
                    ],
                },
            },
        ],
    },

    # ----- History --------------------------------------------------------
    'History': {
        'label': 'History',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 source-based tests', '1 essay',
                                   '1 research task / heritage assignment',
                                   '1 mid-year exam']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1 (Source-based)', 'pct': 37.5,
                         'lines': ['2 hours · 100 marks (Gr 10) / 3 hours · 150 marks (Gr 11)']},
                        {'name': 'Paper 2 (Essay)', 'pct': 37.5,
                         'lines': ['2 hours · 100 marks (Gr 10) / 3 hours · 150 marks (Gr 11)']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 source-based tests', '1 essay',
                                   '1 heritage research task',
                                   '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1 (Source-based)', 'pct': 37.5,
                         'lines': ['3 hours · 150 marks',
                                   'Cold War, Independent Africa, Civil Society Protests']},
                        {'name': 'Paper 2 (Essay)', 'pct': 37.5,
                         'lines': ['3 hours · 150 marks',
                                   'Civil Resistance, Coming of Democracy, End of Cold War, New World Order']},
                    ],
                },
            },
        ],
    },

    # ----- English Home Language ------------------------------------------
    'English Home Language': {
        'label': 'English Home Language',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['Oral tasks (listening, prepared & unprepared speaking)',
                                   'Writing tasks (essay + transactional)',
                                   '2 tests', '1 mid-year exam']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1 (Language in Context)', 'pct': 18.75,
                         'lines': ['2 hours · 70 marks',
                                   'Comprehension, Summary, Language structures']},
                        {'name': 'Paper 2 (Literature)', 'pct': 26.25,
                         'lines': ['2.5 hours · 80 marks',
                                   'Novel, Drama, Poetry, Short Stories']},
                        {'name': 'Paper 3 (Writing)', 'pct': 18.75,
                         'lines': ['2.5 hours · 100 marks',
                                   'Essay + transactional texts']},
                        {'name': 'Oral (Paper 4 — internal)', 'pct': 11.25,
                         'lines': ['Year-long', 'Listening, Prepared & Unprepared Speaking']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['Oral tasks (year-long)',
                                   'Writing tasks (essay + transactional)',
                                   '2 tests',
                                   '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1 (Language in Context)', 'pct': 18.75,
                         'lines': ['2 hours · 70 marks']},
                        {'name': 'Paper 2 (Literature)', 'pct': 26.25,
                         'lines': ['2.5 hours · 80 marks']},
                        {'name': 'Paper 3 (Writing)', 'pct': 18.75,
                         'lines': ['2.5 hours · 100 marks']},
                        {'name': 'Oral (Paper 4 — internal)', 'pct': 11.25,
                         'lines': ['Year-long, internally moderated']},
                    ],
                },
            },
        ],
    },

    # ----- English First Additional Language ------------------------------
    'English FAL': {
        'label': 'English First Additional Language',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['Oral tasks', 'Writing tasks (essay + transactional)',
                                   '2 tests', '1 mid-year exam']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1 (Language in Context)', 'pct': 18.75,
                         'lines': ['2 hours · 80 marks']},
                        {'name': 'Paper 2 (Literature)', 'pct': 26.25,
                         'lines': ['2 hours · 70 marks']},
                        {'name': 'Paper 3 (Writing)', 'pct': 18.75,
                         'lines': ['2.5 hours · 100 marks']},
                        {'name': 'Oral (Paper 4 — internal)', 'pct': 11.25,
                         'lines': ['Year-long']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['Oral tasks (year-long)', 'Writing tasks',
                                   '2 tests',
                                   '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1 (Language)', 'pct': 18.75,
                         'lines': ['2 hours · 80 marks']},
                        {'name': 'Paper 2 (Literature)', 'pct': 26.25,
                         'lines': ['2 hours · 70 marks']},
                        {'name': 'Paper 3 (Writing)', 'pct': 18.75,
                         'lines': ['2.5 hours · 100 marks']},
                        {'name': 'Oral (Paper 4 — internal)', 'pct': 11.25,
                         'lines': ['Year-long, internally moderated']},
                    ],
                },
            },
        ],
    },

    # ----- Afrikaans Home Language ----------------------------------------
    'Afrikaans Home Language': {
        'label': 'Afrikaans Huistaal',
        'grades': [
            {
                'heading': 'Graad 10 en 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA-take', 'pct': 25,
                         'lines': ['Mondelinge take', 'Skryftake (opstel + transaksioneel)',
                                   '2 toetse', '1 middeljaareksamen']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Vraestel 1 (Taal in konteks)', 'pct': 18.75,
                         'lines': ['2 uur · 70 punte']},
                        {'name': 'Vraestel 2 (Letterkunde)', 'pct': 26.25,
                         'lines': ['2½ uur · 80 punte']},
                        {'name': 'Vraestel 3 (Skryfwerk)', 'pct': 18.75,
                         'lines': ['2½ uur · 100 punte']},
                        {'name': 'Mondeling (Vraestel 4 — intern)', 'pct': 11.25,
                         'lines': ['Jaarlange assessering']},
                    ],
                },
            },
            {
                'heading': 'Graad 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA-take', 'pct': 25,
                         'lines': ['Mondelinge take', 'Skryftake', '2 toetse',
                                   '2 interne eksamens (middeljaar + proef)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Vraestel 1 (Taal)', 'pct': 18.75,
                         'lines': ['2 uur · 70 punte']},
                        {'name': 'Vraestel 2 (Letterkunde)', 'pct': 26.25,
                         'lines': ['2½ uur · 80 punte']},
                        {'name': 'Vraestel 3 (Skryfwerk)', 'pct': 18.75,
                         'lines': ['2½ uur · 100 punte']},
                        {'name': 'Mondeling (Vraestel 4 — intern)', 'pct': 11.25,
                         'lines': ['Jaarlange assessering']},
                    ],
                },
            },
        ],
    },

    # ----- Afrikaans First Additional Language ----------------------------
    'Afrikaans FAL': {
        'label': 'Afrikaans Eerste Addisionele Taal',
        'grades': [
            {
                'heading': 'Graad 10 en 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA-take', 'pct': 25,
                         'lines': ['Mondelinge take', 'Skryftake', '2 toetse',
                                   '1 middeljaareksamen']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Vraestel 1 (Taal in konteks)', 'pct': 18.75,
                         'lines': ['2 uur · 80 punte']},
                        {'name': 'Vraestel 2 (Letterkunde)', 'pct': 26.25,
                         'lines': ['2 uur · 70 punte']},
                        {'name': 'Vraestel 3 (Skryfwerk)', 'pct': 18.75,
                         'lines': ['2½ uur · 100 punte']},
                        {'name': 'Mondeling (Vraestel 4 — intern)', 'pct': 11.25,
                         'lines': ['Jaarlange assessering']},
                    ],
                },
            },
            {
                'heading': 'Graad 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA-take', 'pct': 25,
                         'lines': ['Mondelinge take', 'Skryftake', '2 toetse',
                                   '2 interne eksamens (middeljaar + proef)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Vraestel 1 (Taal)', 'pct': 18.75,
                         'lines': ['2 uur · 80 punte']},
                        {'name': 'Vraestel 2 (Letterkunde)', 'pct': 26.25,
                         'lines': ['2 uur · 70 punte']},
                        {'name': 'Vraestel 3 (Skryfwerk)', 'pct': 18.75,
                         'lines': ['2½ uur · 100 punte']},
                        {'name': 'Mondeling (Vraestel 4 — intern)', 'pct': 11.25,
                         'lines': ['Jaarlange assessering']},
                    ],
                },
            },
        ],
    },

    # ----- Life Orientation -----------------------------------------------
    'Life Orientation': {
        'label': 'Life Orientation',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'note': 'Life Orientation is internally assessed — there is no external NSC paper. The end-of-year mark is built from the year\u2019s SBA tasks plus the Common Assessment Task (CAT).',
                'during': {
                    'pct': 100,
                    'cells': [
                        {'name': 'Written tasks', 'pct': 30,
                         'lines': ['2 tests', '1 project / case study']},
                        {'name': 'Physical Education Task (PET)', 'pct': 30,
                         'lines': ['Participation & movement performance across all four terms']},
                        {'name': 'End-of-Year exam (internal)', 'pct': 40,
                         'lines': ['1.5 hours · 80 marks',
                                   'All five LO topics']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'note': 'Grade 12 LO is 100% internally assessed. The Common Assessment Task (CAT) replaces an external exam.',
                'during': {
                    'pct': 100,
                    'cells': [
                        {'name': 'Written tasks', 'pct': 30,
                         'lines': ['2 tests', '1 project']},
                        {'name': 'Physical Education Task (PET)', 'pct': 30,
                         'lines': ['Year-long participation & movement performance']},
                        {'name': 'Common Assessment Task (CAT)', 'pct': 40,
                         'lines': ['Externally set, internally administered',
                                   '2.5 hours · 100 marks']},
                    ],
                },
            },
        ],
    },

    # ----- Tourism --------------------------------------------------------
    'Tourism': {
        'label': 'Tourism',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '1 source-based / case study',
                                   '1 mid-year exam',
                                   'PAT preparation tasks']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Practical Assessment Task (PAT)', 'pct': 25,
                         'lines': ['Year-long PAT — tourism skills assessment file (research, presentation, customer service, tour-planning)']},
                        {'name': 'End-of-Year exam', 'pct': 50,
                         'lines': ['2 hours · 150 marks (Gr 10) / 3 hours · 200 marks (Gr 11)',
                                   'All Tourism topics']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '1 source-based / case study',
                                   '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Practical Assessment Task (PAT)', 'pct': 25,
                         'lines': ['Year-long PAT — tourism skills assessment file']},
                        {'name': 'End-of-Year exam', 'pct': 50,
                         'lines': ['3 hours · 200 marks',
                                   'All Tourism content']},
                    ],
                },
            },
        ],
    },

    # ----- Hospitality Studies --------------------------------------------
    'Hospitality Studies': {
        'label': 'Hospitality Studies',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '1 case study / research',
                                   '1 mid-year exam',
                                   'Practical preparation tasks']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Practical Assessment Task (PAT)', 'pct': 25,
                         'lines': ['Year-long PAT — practical food preparation, service & hosting events']},
                        {'name': 'End-of-Year written exam', 'pct': 50,
                         'lines': ['2 hours · 150 marks (Gr 10) / 3 hours · 200 marks (Gr 11)',
                                   'Theory of all Hospitality topics']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '1 case study / research task',
                                   '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Practical Assessment Task (PAT)', 'pct': 25,
                         'lines': ['Year-long PAT — practical food preparation, service & event hosting']},
                        {'name': 'End-of-Year written exam', 'pct': 50,
                         'lines': ['3 hours · 200 marks',
                                   'Kitchen & Restaurant Operations, Nutrition, Food Commodities, Hospitality Industry']},
                    ],
                },
            },
        ],
    },

    # ----- Consumer Studies -----------------------------------------------
    'Consumer Studies': {
        'label': 'Consumer Studies',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '1 case study / research task',
                                   '1 mid-year exam',
                                   'Practical preparation tasks']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Practical Assessment Task (PAT)', 'pct': 25,
                         'lines': ['Production project — design, plan and produce items in a chosen knowledge area (food / clothing / soft furnishing / craft)']},
                        {'name': 'End-of-Year written exam', 'pct': 50,
                         'lines': ['2 hours · 150 marks (Gr 10) / 3 hours · 200 marks (Gr 11)',
                                   'Theory of all Consumer Studies topics']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '1 case study',
                                   '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Practical Assessment Task (PAT)', 'pct': 25,
                         'lines': ['Production project in chosen knowledge area']},
                        {'name': 'End-of-Year written exam', 'pct': 50,
                         'lines': ['3 hours · 200 marks',
                                   'The Consumer, Food & Nutrition, Clothing, Housing & Furnishings, Entrepreneurship']},
                    ],
                },
            },
        ],
    },

    # ----- Engineering Graphics & Design ----------------------------------
    'Engineering Graphics & Design': {
        'label': 'Engineering Graphics & Design',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['Drawing tasks (mechanical & civil)',
                                   '2 tests', '1 PAT (mini-project)',
                                   '1 mid-year exam']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1 (Civil drawings)', 'pct': 37.5,
                         'lines': ['3 hours · 200 marks',
                                   'First-angle orthographic, isometric, civil components']},
                        {'name': 'Paper 2 (Mechanical drawings)', 'pct': 37.5,
                         'lines': ['3 hours · 200 marks',
                                   'Loci, mechanical components, assemblies']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['PAT — design project (year-long)',
                                   '2 tests',
                                   '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1 (Civil)', 'pct': 37.5,
                         'lines': ['3 hours · 200 marks',
                                   'Civil analytical, plans, sections, perspective']},
                        {'name': 'Paper 2 (Mechanical)', 'pct': 37.5,
                         'lines': ['3 hours · 200 marks',
                                   'Mechanical analytical, loci, assemblies']},
                    ],
                },
            },
        ],
    },

    # ----- Agricultural Sciences ------------------------------------------
    'Agricultural Sciences': {
        'label': 'Agricultural Sciences',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '2 practical investigations',
                                   '1 project / research task',
                                   '1 mid-year exam']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1', 'pct': 37.5,
                         'lines': ['2 hours · 100 marks (Gr 10) / 2.5 hours · 150 marks (Gr 11)',
                                   'Animal & Plant Studies']},
                        {'name': 'Paper 2', 'pct': 37.5,
                         'lines': ['2 hours · 100 marks (Gr 10) / 2.5 hours · 150 marks (Gr 11)',
                                   'Agricultural Management & Marketing']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '2 practical activities',
                                   '1 project',
                                   '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1', 'pct': 37.5,
                         'lines': ['2.5 hours · 150 marks',
                                   'Animal Nutrition, Animal Production & Reproduction, Animal Health']},
                        {'name': 'Paper 2', 'pct': 37.5,
                         'lines': ['2.5 hours · 150 marks',
                                   'Agricultural Management, Marketing & Production Factors, Basic Agricultural Genetics']},
                    ],
                },
            },
        ],
    },

    # ----- Visual Arts ----------------------------------------------------
    'Visual Arts': {
        'label': 'Visual Arts',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['Theory: 2 tests + 1 essay/research task',
                                   '1 mid-year theory exam',
                                   'PAT: sourcebook + practical artworks']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Practical Assessment Task (PAT)', 'pct': 50,
                         'lines': ['Body of practical work + sourcebook',
                                   'Year-long, externally moderated']},
                        {'name': 'Theory paper', 'pct': 25,
                         'lines': ['2 hours · 100 marks (Gr 10) / 3 hours · 100 marks (Gr 11)',
                                   'Visual culture studies']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['Theory: 2 tests + 1 essay',
                                   '2 internal theory exams (mid-year + trial)',
                                   'PAT preparation tasks']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Practical Assessment Task (PAT)', 'pct': 50,
                         'lines': ['Final body of work + sourcebook',
                                   'Year-long, externally moderated']},
                        {'name': 'Theory paper', 'pct': 25,
                         'lines': ['3 hours · 100 marks',
                                   'Visual Culture Studies — South African & International art']},
                    ],
                },
            },
        ],
    },

    # ----- Dramatic Arts --------------------------------------------------
    'Dramatic Arts': {
        'label': 'Dramatic Arts',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['Practical performances & workshops',
                                   '2 tests', '1 mid-year exam',
                                   '1 research / journal task']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Practical exam (PAT)', 'pct': 37.5,
                         'lines': ['Performance: prepared & unprepared pieces',
                                   'Externally moderated']},
                        {'name': 'Theory paper', 'pct': 37.5,
                         'lines': ['2 hours · 100 marks (Gr 10) / 3 hours · 150 marks (Gr 11)',
                                   'Drama history, theory, set works']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['Practical performances',
                                   '2 tests',
                                   '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Practical exam (PAT)', 'pct': 37.5,
                         'lines': ['Externally moderated performance examination']},
                        {'name': 'Theory paper', 'pct': 37.5,
                         'lines': ['3 hours · 150 marks',
                                   'South African theatre, set texts, theory']},
                    ],
                },
            },
        ],
    },

    # ----- Music ----------------------------------------------------------
    'Music': {
        'label': 'Music',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['Performance & improvisation tasks',
                                   '2 tests', '1 mid-year exam',
                                   '1 research / composition task']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Practical exam (PAT)', 'pct': 37.5,
                         'lines': ['Solo & ensemble performance',
                                   'Externally moderated']},
                        {'name': 'Theory paper', 'pct': 37.5,
                         'lines': ['2 hours · 100 marks (Gr 10) / 3 hours · 120 marks (Gr 11)',
                                   'Theory, Aural, General Music Knowledge']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['Performance tasks',
                                   '2 tests',
                                   '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Practical exam (PAT)', 'pct': 37.5,
                         'lines': ['Solo + ensemble performance',
                                   'Externally moderated']},
                        {'name': 'Theory paper', 'pct': 37.5,
                         'lines': ['3 hours · 120 marks',
                                   'Theory of Music, Aural, General Music Knowledge & Analysis']},
                    ],
                },
            },
        ],
    },

    # ----- Religion Studies -----------------------------------------------
    'Religion Studies': {
        'label': 'Religion Studies',
        'grades': [
            {
                'heading': 'Grade 10 and 11',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '1 research / case study',
                                   '1 project',
                                   '1 mid-year exam']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1', 'pct': 37.5,
                         'lines': ['2 hours · 100 marks (Gr 10) / 2 hours · 150 marks (Gr 11)']},
                        {'name': 'Paper 2', 'pct': 37.5,
                         'lines': ['2 hours · 100 marks (Gr 10) / 2 hours · 150 marks (Gr 11)']},
                    ],
                },
            },
            {
                'heading': 'Grade 12',
                'during': {
                    'pct': 25,
                    'cells': [
                        {'name': 'SBA tasks', 'pct': 25,
                         'lines': ['2 tests', '1 research task',
                                   '2 internal exams (mid-year + trial)']},
                    ],
                },
                'eoy': {
                    'pct': 75,
                    'cells': [
                        {'name': 'Paper 1', 'pct': 37.5,
                         'lines': ['2 hours · 150 marks',
                                   'Religions of SA, common features, normative sources']},
                        {'name': 'Paper 2', 'pct': 37.5,
                         'lines': ['2 hours · 150 marks',
                                   'Religion & current issues, comparative study']},
                    ],
                },
            },
        ],
    },

}
