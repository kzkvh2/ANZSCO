"""
Diverse CV acceptance test — 10 real-world-style CVs.

These CVs deliberately differ from the original synthetic set:
  - Different occupations (trades, health, ICT, social, science)
  - Variable English quality and formatting
  - Mixed seniority (junior, mid, senior, managerial)
  - Non-Australian employers and institutions
  - Career changers and dual-specialisation profiles

Pass criteria: same as acceptance_test.py
  - Top-5 accuracy >= 8/10
  - Top-1 accuracy >= 5/10

Usage:
  cd ~/projects/mate1
  ANTHROPIC_API_KEY=sk-ant-... PYTHONPATH=. .venv/bin/python3 tests/acceptance/diverse_cv_test.py
"""

import json, os, sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))
from src.rag.matcher import match_cv

CASES = [
    # 1 — Physiotherapist (from India, AHP English style)
    {
        'role': 'Physiotherapist',
        'acceptable_codes': {'252511', '252512'},
        'cv': """
Rajesh Kumar Nair
Physiotherapist | Melbourne VIC | rajesh.nair@gmail.com

PROFESSIONAL SUMMARY
Qualified physiotherapist with 6 years experience in musculoskeletal and sports rehabilitation.
AHPRA registered. Seeking permanent role in Australian private practice.

EMPLOYMENT
Senior Physiotherapist — Apollo Hospitals, Chennai, India (2019–2023)
- Assessed and treated outpatients with musculoskeletal, neurological and post-surgical conditions
- Developed individualised treatment plans using manual therapy, exercise prescription, ultrasound and TENS
- Treated 25–30 patients daily across orthopaedic, sports and geriatric clinics
- Supervised junior physiotherapists and interns (team of 4)
- Conducted group exercise classes for chronic lower back pain patients

Physiotherapist — Fortis Healthcare, Bangalore (2018–2019)
- Provided inpatient rehabilitation for post-operative joint replacement patients
- Administered hydrotherapy and electrotherapy modalities

EDUCATION
Bachelor of Physiotherapy (BPT) — Manipal University (2018)
AHPRA Registration: current (PTH0001234567)

SKILLS
Manual therapy, exercise prescription, dry needling, ultrasound, TENS, gait analysis,
sports rehabilitation, neurological rehab, patient education, AHPRA compliant documentation
""",
    },

    # 2 — Data Scientist (career changer from statistics background)
    {
        'role': 'Data Scientist',
        'acceptable_codes': {'224115', '224114', '261313'},
        'cv': """
Mei-Lin Zhang — Data Scientist
mei.zhang@outlook.com | Sydney NSW

EXPERIENCE
Data Scientist — Westpac Banking Group (2021–present)
- Build and deploy machine learning models for credit risk and customer churn prediction
- Work with structured and unstructured data; pipelines process 50M+ records/month
- Use Python (scikit-learn, XGBoost, PyTorch), SQL, Databricks and MLflow
- Collaborate with product and engineering teams to translate business problems into ML solutions
- Present model performance and findings to non-technical stakeholders

Statistical Analyst — Australian Bureau of Statistics (2018–2021)
- Designed and analysed sample surveys (Labour Force Survey, Census quality checks)
- Built R and SAS models for population estimation
- Transitioned to Python-based ML methods during this role

EDUCATION
Master of Statistics — University of New South Wales (2018)
Bachelor of Mathematics — University of Melbourne (2016)

SKILLS
Python, R, SQL, machine learning, deep learning, statistical modelling,
A/B testing, data visualisation (Tableau, matplotlib), Azure, Databricks
""",
    },

    # 3 — Construction Project Manager (condensed format, international background)
    {
        'role': 'Construction Project Manager',
        'acceptable_codes': {'133111', '133112'},
        'cv': """
Ahmed Al-Rashidi | Perth WA | ahmed.rashidi@email.com
Construction Project Manager — 10 years experience

CURRENT: Senior Project Manager — CIMIC Group / UGL (2022–present)
Projects: Fortescue Metals Group infrastructure, BHP Pilbara upgrades ($50M–$150M range)
Responsibilities: full project lifecycle, schedule, cost, subcontractor management, HSE

PREVIOUS:
Project Manager — Bechtel Corporation, Saudi Arabia (2017–2022)
- Managed construction of industrial facilities (oil & gas sector)
- Led teams of 80+ site workers and 6 engineers
- Delivered projects on time and under budget using Primavera P6

Site Engineer — Al-Habtoor Engineering, Dubai (2013–2017)
- Civil works supervision, concrete pours, structural steel erection

QUALIFICATIONS
B.Eng Civil Engineering — King Abdullah University (2013)
PMP Certified (PMI) | White Card (WA) | RPEQ candidate

TOOLS: Primavera P6, MS Project, AutoCAD, Procore, cost forecasting
""",
    },

    # 4 — Social Worker (local graduate, welfare sector)
    {
        'role': 'Social Worker',
        'acceptable_codes': {'272511', '272512'},
        'cv': """
Jessica Morrison
Social Worker | Brisbane QLD | j.morrison@socialwork.net

WORK EXPERIENCE

Case Manager — Anglicare Queensland (2020–present)
- Provide case management services to at-risk families under the Child Protection Act
- Conduct home assessments, safety planning and risk assessments
- Liaise with Department of Children, Youth Justice and Multicultural Affairs
- Facilitate referrals to housing, mental health and domestic violence services
- Maintain detailed case notes in CRIS database

Student Social Worker Placement — Lives Lived Well (2019)
- Supported clients with alcohol and other drug issues in residential treatment
- Co-facilitated group therapy sessions under clinical supervision

EDUCATION
Bachelor of Social Work (Honours) — Queensland University of Technology (2020)
AASW full member | Blue Card: current

SKILLS
Case management, risk assessment, family support, child protection,
motivational interviewing, trauma-informed practice, report writing, CRIS
""",
    },

    # 5 — Plumber (trade, minimal CV, spelling as-is)
    {
        'role': 'Plumber',
        'acceptable_codes': {'334111'},
        'cv': """
Troy Galloway — Plumber
troy.galloway@hotmail.com | Gold Coast QLD | 0412 xxx xxx

About me: Licensed plumber with 8 years expereince in residential and commerical work.
Looking for stable employment with a reputable company.

Work History:
Self-employed Plumber — TG Plumbing Services (2019–present)
  New residential plumbing installations
  Hot water system replacements (gas and electric)
  Blocked drain clearing and pipe relining
  Renovations — bathroom and kitchen fit-outs
  Backflow prevention testing and certification

Plumber — Reece Plumbing Services (2016–2019)
  Apprenticeship completion and first trade position
  Commercial fit-outs and body corporate maintenance

Licences/Certs:
  QLD Contractor Licence (QBCC)
  Gas Work Authorisation (Type B)
  Certificate III in Plumbing (2016)
  White Card

Skills: copper, PVC, PEX pipe, gas fitting, drainage, stormwater, waterproofing
""",
    },

    # 6 — ICT Business Analyst (mid-career, government sector)
    {
        'role': 'ICT Business Analyst',
        'acceptable_codes': {'261111', '224711'},
        'cv': """
Karen Whitfield — ICT Business Analyst
karen.whitfield@email.com | Canberra ACT

PROFESSIONAL EXPERIENCE

ICT Business Analyst — Department of Home Affairs (2020–present)
- Elicit and document business requirements for digital transformation projects
- Facilitate workshops with stakeholders to map current-state and future-state processes
- Produce business requirement documents (BRDs), use cases, user stories and process maps
- Work with development teams in Agile/Scrum delivery environments
- Conduct user acceptance testing (UAT) and support change management activities
- Projects include: visa processing system modernisation, identity verification uplift

Business Analyst — Accenture Australia (2016–2020)
- Delivered BA services across financial services and government clients
- Modelled business processes using BPMN and UML notation
- Led requirements workshops for a $12M ERP implementation (SAP)

EDUCATION
Bachelor of Information Systems — Australian National University (2016)
IIBA CBAP Certification (2022)

SKILLS
Requirements analysis, BPMN, UML, user stories, UAT, Agile, Jira, Confluence,
stakeholder management, process mapping, SAP, ServiceNow
""",
    },

    # 7 — Pharmacist (recent immigrant, international qual recognised)
    {
        'role': 'Pharmacist',
        'acceptable_codes': {'251511'},
        'cv': """
Sunita Patel — Pharmacist
sunita.patel@gmail.com | Adelaide SA

SUMMARY
Registered pharmacist with 9 years combined experience in community and hospital pharmacy
across India and Australia. AHPRA registered since 2022.

EMPLOYMENT HISTORY

Pharmacist — TerryWhite Chemmart, Adelaide (2022–present)
- Dispensing and checking prescriptions for a high-volume community pharmacy (400+ scripts/day)
- Medication reviews (MedsCheck and Diabetes MedsCheck) for chronic disease patients
- Vaccination administration (flu, COVID-19, travel vaccines)
- Counselling patients on medication use, interactions and adherence
- Supervision of pharmacy assistants and interns

Senior Pharmacist — Apollo Pharmacy, Mumbai, India (2015–2022)
- Managed pharmacy operations for a chain of 3 community stores
- Handled controlled substance dispensing and regulatory compliance
- Trained and supervised 12 staff

EDUCATION
Bachelor of Pharmacy (B.Pharm) — University of Mumbai (2015)
Ahpra Registration: current (PHR0001235678)
Intern Training Program — SA Pharmacy (2022)

SKILLS
Dispensing, medication review, patient counselling, vaccination, drug interactions,
controlled substances, inventory management, Fred Dispense, MedsCheck
""",
    },

    # 8 — Disability Support Worker (para-professional, entry level)
    {
        'role': 'Disability Support Worker',
        'acceptable_codes': {'423111'},
        'cv': """
Amara Osei
Disability Support Worker
amara.osei@email.com | Melbourne VIC

I am a caring and reliable support worker with 3 years experience supporting people
with physical and intellectual disabilities in both community and residential settings.

EXPERIENCE

Disability Support Worker — Scope Australia (2022–present)
Support participants with daily living activities including personal care, meal preparation,
household tasks and community access. Implement support plans aligned with NDIS goals.
Assist with communication supports for participants with complex needs.
Provide transport to appointments and recreational activities.
Complete daily progress notes and incident reports.

Support Worker — HammondCare (2021–2022)
Supported older adults and people with dementia in a residential aged care facility.
Assisted with mobility, hygiene, dining and social activities.

EDUCATION & CERTIFICATIONS
Certificate III in Individual Support (Disability) — TAFE Victoria (2021)
NDIS Worker Screening Check: current
Working with Children Check: current
First Aid and CPR: current

SKILLS
Personal care, manual handling, behaviour support, NDIS, documentation,
community access, communication supports, medication assistance
""",
    },

    # 9 — Financial Accountant (senior, different from original mid-career test)
    {
        'role': 'Management Accountant',
        'acceptable_codes': {'221112', '221111', '132211'},
        'cv': """
David Lim CPA — Senior Financial Accountant
david.lim@email.com | Melbourne VIC

15 years progressive accounting experience across manufacturing and FMCG sectors.
Currently seeking management accounting role with a focus on business partnering.

CAREER HISTORY

Senior Financial Accountant — Asahi Beverages Australia (2019–present)
- Prepare monthly management accounts and board reporting pack ($2.8B revenue segment)
- Lead annual budget process (CAPEX and OPEX) and quarterly reforecasts
- Perform detailed cost variance analysis and drive cost reduction initiatives
- Business partner with operations and supply chain teams on financial performance
- Oversee fixed asset register, depreciation and CAPEX tracking
- Manage 2 junior accountants

Financial Accountant — Amcor Packaging (2014–2019)
- Prepared statutory financial statements under AIFRS
- Month-end close including journals, accruals, prepayments and intercompany reconciliations
- Managed cash flow reporting and treasury support

Graduate Accountant — KPMG (2010–2014)
- Audit and assurance for manufacturing and retail clients

EDUCATION
Bachelor of Commerce (Accounting & Finance) — Monash University (2010)
CPA Australia — full member | CA ANZ — associate

SKILLS
Management reporting, financial analysis, budgeting, forecasting, AIFRS,
Oracle ERP, Hyperion Essbase, Excel (advanced), PowerBI, team leadership
""",
    },

    # 10 — Secondary Teacher (LOTE / ESL focus, distinct from original teacher)
    {
        'role': 'TESOL Teacher',
        'acceptable_codes': {'241411', '241213'},
        'cv': """
Maria Santos — English as a Second Language Teacher
maria.santos@edu.au | Sydney NSW

TEACHING EXPERIENCE

ESL / LOTE Teacher — Blacktown International Selective High School (2018–present)
- Teach English as an Additional Language or Dialect (EAL/D) to Years 7–12 students
  from non-English speaking backgrounds
- Differentiate curriculum delivery for students with varying English proficiency levels
- Implement NESA EAL/D Life Skills syllabus for students with disability
- Co-teach with mainstream teachers to support language across the curriculum
- Coordinate school's Multicultural Education program (300+ students)
- Liaise with SLSO, parents and community organisations

EFL Teacher — British Council, Manila, Philippines (2013–2018)
- Delivered Cambridge ESOL preparation classes (A2–C1 levels)
- Taught adult professional English to corporate clients

EDUCATION
Master of Teaching (Secondary) — Western Sydney University (2018)
Bachelor of Arts (English Literature) — University of the Philippines (2013)
NSW Teacher Accreditation: Proficient level | NESA registered
TESOL Certificate (Cambridge CELTA)

SKILLS
EAL/D, TESOL, curriculum differentiation, assessment, reporting, LOTE,
multicultural education, NESA syllabus, Sentral, Canvas LMS
""",
    },
]


def run_diverse_test():
    print('=' * 65)
    print('ANZSCO Code Finder — Diverse CV Test')
    print(f'{len(CASES)} varied CVs (trades, health, ICT, social, science)')
    print('Pass: correct code in top 5 for >=8/10 | Stretch: #1 for >=5/10')
    print('=' * 65)

    results_log = []
    top5_hits = 0
    top1_hits = 0
    total_start = time.perf_counter()

    for idx, case in enumerate(CASES, 1):
        print(f'\n[{idx:2d}/{len(CASES)}] {case["role"]}')
        print(f'       Acceptable codes: {case["acceptable_codes"]}')

        t0 = time.perf_counter()
        try:
            result = match_cv(case['cv'])
        except Exception as e:
            print(f'       ERROR: {e}')
            results_log.append({**case, 'acceptable_codes': list(case['acceptable_codes']),
                                 'error': str(e), 'in_top5': False, 'is_top1': False})
            continue
        elapsed = int((time.perf_counter() - t0) * 1000)

        codes = [r['code'] for r in result['results']]
        in_top5 = bool(case['acceptable_codes'] & set(codes))
        is_top1 = codes[0] in case['acceptable_codes'] if codes else False
        top5_hits += in_top5
        top1_hits += is_top1

        top1_result = result['results'][0] if result['results'] else {}
        print(f'       Top 5 returned : {codes}')
        print(f'       #1 result      : [{top1_result.get("code")}] {top1_result.get("title")} ({top1_result.get("match_score")}/100)')
        print(f'       In top 5       : {"PASS ✓" if in_top5 else "FAIL ✗"}  |  Is #1: {"PASS ✓" if is_top1 else "FAIL ✗"}  |  {elapsed}ms')

        results_log.append({
            'role':             case['role'],
            'acceptable_codes': list(case['acceptable_codes']),
            'returned_codes':   codes,
            'top1_code':        top1_result.get('code'),
            'top1_title':       top1_result.get('title'),
            'top1_score':       top1_result.get('match_score'),
            'in_top5':          in_top5,
            'is_top1':          is_top1,
            'elapsed_ms':       elapsed,
            'all_results':      result['results'],
        })

    total_elapsed = int((time.perf_counter() - total_start) * 1000)
    n = len(CASES)

    print('\n' + '=' * 65)
    print('FINAL RESULTS')
    print('=' * 65)
    print(f'  Top-5 accuracy : {top5_hits}/{n} ({100*top5_hits//n}%)  — target >=80%  {"PASS ✓" if top5_hits/n >= 0.8 else "FAIL ✗"}')
    print(f'  Top-1 accuracy : {top1_hits}/{n} ({100*top1_hits//n}%)  — target >=50%  {"PASS ✓" if top1_hits/n >= 0.5 else "FAIL ✗"}')
    print(f'  Total time     : {total_elapsed/1000:.1f}s across {n} CVs ({total_elapsed//n}ms avg)')

    out = pathlib.Path('tests/acceptance/diverse_run.json')
    out.write_text(json.dumps(results_log, indent=2))
    print(f'\n  Full results saved -> {out}')

    failures = [r for r in results_log if not r.get('in_top5')]
    if failures:
        print(f'\n  MISSED ({len(failures)} cases):')
        for f in failures:
            print(f'    - {f["role"]}: returned {f.get("returned_codes")}, expected one of {f.get("acceptable_codes")}')

    return top5_hits / n >= 0.8


if __name__ == '__main__':
    passed = run_diverse_test()
    sys.exit(0 if passed else 1)
