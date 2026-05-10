"""
Full acceptance test — 10 ground-truth CVs.

Pass criteria  : correct code in top 5 for >= 8/10 (80%)
Stretch target : correct code is #1   for >= 5/10 (50%)
Speed          : each CV < 30s (cold model load amortised after first call)

Each test case accepts a set of valid codes because many occupations map
legitimately to 2-3 nearby codes depending on specialisation.

Known limitation (tracked): seniority / tenure not factored into matching.
A 20-year IT manager may score as an ICT support technician. Fix pending.

Usage:
  cd ~/projects/anzsco
  ANTHROPIC_API_KEY=sk-ant-... PYTHONPATH=. .venv/bin/python3 tests/acceptance/acceptance_test.py
"""

import json, os, sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))
from src.rag.matcher import match_cv

# ---------------------------------------------------------------------------
# Ground-truth test cases
# Each CV is deliberately mid-career to avoid the seniority skew issue.
# Acceptable codes validated against ABS ANZSCO 2022 browse pages.
# ---------------------------------------------------------------------------
CASES = [
    {
        'role': 'Software Engineer',
        'acceptable_codes': {'261313', '261312', '261311'},
        'cv': """
Michael Chen — Software Engineer
michael.chen@email.com | Melbourne, VIC

EXPERIENCE
Software Engineer — REA Group (2019–present)
- Design and develop backend microservices in Python and Java
- Build and maintain REST APIs serving 2M daily active users
- Write unit and integration tests, maintain 90%+ code coverage
- Participate in code reviews and technical design discussions
- Deploy services to AWS using Terraform and Docker

Junior Software Engineer — MYOB (2017–2019)
- Developed features for cloud accounting platform in Python
- Fixed bugs and improved performance of core payroll module

EDUCATION
Bachelor of Software Engineering — Monash University (2017)

SKILLS
Python, Java, REST APIs, AWS, Docker, Terraform, PostgreSQL, Git, Agile
""",
    },
    {
        'role': 'Registered Nurse',
        'acceptable_codes': {'254418', '254412', '254415', '254413', '254414', '254422', '254499'},
        'cv': """
Sarah O'Brien — Registered Nurse
sarah.obrien@email.com | Brisbane, QLD

EXPERIENCE
Registered Nurse — Princess Alexandra Hospital (2018–present)
- Provide nursing care to patients in a 30-bed medical ward
- Assess, plan, implement and evaluate patient care plans
- Administer medications and monitor patient responses
- Liaise with doctors, allied health and family members
- Supervise and mentor enrolled nurses and student nurses

Graduate Registered Nurse — Mater Hospital (2016–2018)
- Rotated across surgical, medical and emergency departments
- Completed DETECT Early Warning System training

EDUCATION
Bachelor of Nursing — Queensland University of Technology (2016)
AHPRA Registration: current

SKILLS
Patient assessment, medication administration, wound care, IV therapy,
documentation, patient education, team coordination
""",
    },
    {
        'role': 'Accountant',
        'acceptable_codes': {'221111', '221112', '221113'},
        'cv': """
Priya Sharma — Accountant
priya.sharma@email.com | Sydney, NSW

EXPERIENCE
Accountant — Deloitte Australia (2020–present)
- Prepare financial statements and management reports for ASX-listed clients
- Conduct variance analysis and budget vs actuals reporting
- Prepare BAS, IAS and income tax returns for corporate clients
- Assist in statutory audits and liaise with ATO on compliance matters
- Advise clients on accounting system implementation (Xero, MYOB)

Graduate Accountant — BDO (2018–2020)
- Prepared financial reports and reconciliations for SME clients
- Assisted with payroll tax and fringe benefits tax calculations

EDUCATION
Bachelor of Commerce (Accounting) — University of Sydney (2018)
CPA Australia — member

SKILLS
Financial reporting, tax compliance, audit, Xero, MYOB, Excel, IFRS, AASB
""",
    },
    {
        'role': 'Chef',
        'acceptable_codes': {'351311'},
        'cv': """
Marco Rossi — Chef
marco.rossi@email.com | Melbourne, VIC

EXPERIENCE
Chef de Partie — Vue de Monde, Melbourne (2021–present)
- Responsible for the larder and entrée sections of a fine dining kitchen
- Prepare, cook and plate dishes to executive chef's specifications
- Develop seasonal menu items using locally sourced produce
- Maintain food safety standards and HACCP records
- Train and supervise kitchen hands and apprentice cooks

Commis Chef — Attica Restaurant (2019–2021)
- Assisted senior chefs in all sections of the kitchen
- Prepared mise en place for 60-cover dinner service

EDUCATION
Certificate III in Commercial Cookery — William Angliss Institute (2019)

SKILLS
Fine dining cookery, menu development, food safety (HACCP),
stock and sauce preparation, pastry, team supervision
""",
    },
    {
        'role': 'Civil Engineer',
        'acceptable_codes': {'233211', '233212', '233214'},
        'cv': """
James Nguyen — Civil Engineer
james.nguyen@email.com | Perth, WA

EXPERIENCE
Civil Engineer — AECOM Australia (2018–present)
- Design road and highway infrastructure for state government projects
- Prepare engineering drawings, specifications and tender documents
- Conduct site inspections and quality assurance checks
- Manage stakeholder consultation with local councils and landowners
- Use AutoCAD Civil 3D and 12d Model for design and drainage analysis

Graduate Civil Engineer — GHD (2016–2018)
- Assisted in design of stormwater drainage and subdivision works
- Prepared engineering calculations and design reports

EDUCATION
Bachelor of Civil Engineering (Honours) — Curtin University (2016)
Engineers Australia — Graduate Member

SKILLS
Road design, drainage, AutoCAD Civil 3D, 12d Model, project management,
geotechnical analysis, stormwater, construction supervision
""",
    },
    {
        'role': 'Secondary School Teacher',
        'acceptable_codes': {'241411'},
        'cv': """
Emma Thompson — Secondary School Teacher
emma.thompson@email.com | Adelaide, SA

EXPERIENCE
Secondary Teacher — Unley High School (2017–present)
- Teach Mathematics and Science to Years 8–12 students
- Plan and deliver lessons aligned to the Australian Curriculum
- Assess and report on student progress each semester
- Coordinate Year 10 STEM elective program
- Mentor pre-service teachers on professional placement

Graduate Teacher — Mitcham Girls High School (2015–2017)
- Taught Years 7–10 Mathematics and Year 9 Science
- Implemented differentiated learning strategies

EDUCATION
Bachelor of Education (Secondary) — University of Adelaide (2015)
South Australian Teaching Certificate: current

SKILLS
Curriculum planning, differentiated instruction, student assessment,
classroom management, parent communication, SACE coordination
""",
    },
    {
        'role': 'Electrician',
        'acceptable_codes': {'341111', '341112', '341113'},
        'cv': """
Daniel Walsh — Electrician
daniel.walsh@email.com | Sydney, NSW

EXPERIENCE
Electrician — Jemena Electricity Networks (2019–present)
- Install, test and maintain electrical wiring systems in residential
  and commercial buildings
- Read and interpret electrical blueprints and wiring diagrams
- Diagnose faults and carry out repairs to electrical systems
- Install switchboards, meters and distribution boards
- Ensure all work complies with AS/NZS 3000 wiring rules

Apprentice Electrician — O'Brien Electrical (2015–2019)
- Completed 4-year electrical apprenticeship
- Assisted licensed electricians on residential and commercial sites

EDUCATION
Certificate III in Electrotechnology Electrician — TAFE NSW (2019)
NSW Electrical Contractor Licence: current

SKILLS
Electrical installation, fault diagnosis, switchboard installation,
wiring systems, AS/NZS 3000, power tools, safety compliance
""",
    },
    {
        'role': 'Marketing Manager',
        'acceptable_codes': {'131011', '225113', '225111'},
        'cv': """
Aisha Patel — Marketing Manager
aisha.patel@email.com | Melbourne, VIC

EXPERIENCE
Marketing Manager — Seek Limited (2020–present)
- Lead a team of 5 marketing specialists across digital and brand channels
- Develop and execute annual marketing strategy with $2M budget
- Oversee SEO, SEM, social media and email marketing campaigns
- Manage relationships with external agencies and media partners
- Report on campaign performance and ROI to executive leadership

Senior Marketing Coordinator — Carsales (2017–2020)
- Managed paid search campaigns generating 40% of new user acquisition
- Developed content calendar and managed social media accounts

EDUCATION
Bachelor of Business (Marketing) — RMIT University (2017)

SKILLS
Digital marketing, SEO, SEM, Google Ads, social media, brand strategy,
budget management, campaign analytics, team leadership, Adobe Creative Suite
""",
    },
    {
        'role': 'Architect',
        'acceptable_codes': {'232111'},
        'cv': """
Lena Kowalski — Architect
lena.kowalski@email.com | Sydney, NSW

EXPERIENCE
Architect — Hassell Studio (2018–present)
- Lead design of commercial and mixed-use buildings from concept to completion
- Prepare architectural drawings, specifications and documentation
- Manage consultant coordination including structural, hydraulic and ESD
- Conduct client briefings and present design proposals
- Oversee construction administration and site inspections

Graduate Architect — Architectus (2015–2018)
- Contributed to design development of residential apartment projects
- Produced architectural documentation using Revit and AutoCAD

EDUCATION
Bachelor of Architecture (Honours) — University of Sydney (2015)
Architects Registration Board NSW: registered

SKILLS
Architectural design, Revit, AutoCAD, SketchUp, project management,
building codes, documentation, sustainability, construction administration
""",
    },
    {
        'role': 'Human Resources Manager',
        'acceptable_codes': {'132111', '223111', '223112'},
        'cv': """
Tom Fitzgerald — Human Resources Manager
tom.fitzgerald@email.com | Brisbane, QLD

EXPERIENCE
HR Manager — Suncorp Group (2019–present)
- Manage full HR function for a business unit of 350 employees
- Lead recruitment, onboarding and workforce planning activities
- Develop and implement performance management and remuneration frameworks
- Handle employee relations matters including investigations and grievances
- Partner with senior leaders on organisational change programs

HR Business Partner — QSuper (2016–2019)
- Provided HR advisory services to 5 business units
- Managed annual salary review process and job evaluation

EDUCATION
Bachelor of Business (Human Resource Management) — QUT (2016)
AHRI — Certified HR Practitioner

SKILLS
Workforce planning, recruitment, employee relations, performance management,
remuneration, HR policy, change management, HRIS (Workday, SAP SuccessFactors)
""",
    },
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_acceptance_test():
    print('=' * 65)
    print('ANZSCO Code Finder — Acceptance Test')
    print(f'{len(CASES)} ground-truth CVs')
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
            results_log.append({**case, 'error': str(e), 'in_top5': False, 'is_top1': False})
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

    # Save detailed results
    out = pathlib.Path('tests/acceptance/last_run.json')
    out.write_text(json.dumps(results_log, indent=2))
    print(f'\n  Full results saved -> {out}')

    # Failure summary
    failures = [r for r in results_log if not r.get('in_top5')]
    if failures:
        print(f'\n  MISSED ({len(failures)} cases):')
        for f in failures:
            print(f'    - {f["role"]}: returned {f.get("returned_codes")}, expected one of {f.get("acceptable_codes")}')

    return top5_hits / n >= 0.8


if __name__ == '__main__':
    passed = run_acceptance_test()
    sys.exit(0 if passed else 1)
