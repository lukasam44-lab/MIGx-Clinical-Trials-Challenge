"""
Data Quality Test Suite
Executes test cases from docs/test_plan.md against the clinical trials database.
Produces a pass/fail summary and a defect log.
Rerunnable: safe to execute before every data refresh.
"""

import sqlite3
import re
import pandas as pd
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / 'data' / 'clinical_trials.db'
DEFECT_LOG_PATH = PROJECT_ROOT / 'docs' / 'defect_log.md'

# Controlled vocabularies (expected value sets)
VALID_STATUSES = {
    'COMPLETED', 'RECRUITING', 'TERMINATED', 'WITHDRAWN', 'UNKNOWN',
    'NOT_YET_RECRUITING', 'ACTIVE_NOT_RECRUITING', 'ENROLLING_BY_INVITATION',
    'SUSPENDED', 'AVAILABLE', 'WITHHELD', 'NO_LONGER_AVAILABLE',
    'APPROVED_FOR_MARKETING', 'TEMPORARILY_NOT_AVAILABLE'
}
VALID_PHASES = {'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4', 'EARLY_PHASE1', 'NA'}

results = []   # collects every test result


def record(test_id, rule, severity, violations, sample=None):
    """Record one test result."""
    results.append({
        'test_id': test_id,
        'rule': rule,
        'severity': severity,
        'violations': violations,
        'status': 'PASS' if violations == 0 else 'FAIL',
        'sample': sample
    })


def run_tests(conn):
    # DQ-001 — nct_id uniqueness
    v = conn.execute("""
        SELECT COUNT(*) - COUNT(DISTINCT nct_id) FROM studies
    """).fetchone()[0]
    record('DQ-001', 'Primary business key must be unique', 'Critical', v)

    # DQ-002 — nct_id format (regex — Python is the right tool)
    ids = pd.read_sql("SELECT study_id, nct_id FROM studies", conn)
    pattern = re.compile(r'^NCT\d{8}$')
    bad = ids[~ids['nct_id'].astype(str).str.match(pattern)]
    record('DQ-002', 'Identifiers must match canonical format NCT+8 digits',
           'High', len(bad), bad['nct_id'].head(3).tolist())

    # DQ-003 — critical field completeness
    v = conn.execute("""
        SELECT COUNT(*) FROM studies
        WHERE nct_id IS NULL OR status IS NULL OR study_type IS NULL
    """).fetchone()[0]
    record('DQ-003', 'Critical fields (nct_id, status, study_type) must be populated',
           'High', v)

    # DQ-004 — date format completeness
    v = conn.execute("""
        SELECT COUNT(*) FROM studies
        WHERE (start_date IS NOT NULL AND LENGTH(start_date) != 10)
           OR (completion_date IS NOT NULL AND LENGTH(completion_date) != 10)
           OR (primary_completion_date IS NOT NULL AND LENGTH(primary_completion_date) != 10)
    """).fetchone()[0]
    sample = pd.read_sql("""
        SELECT nct_id, start_date, completion_date FROM studies
        WHERE start_date IS NOT NULL AND LENGTH(start_date) != 10 LIMIT 3
    """, conn).to_dict('records')
    record('DQ-004', 'Dates must be complete ISO-8601 (YYYY-MM-DD)', 'High', v, sample)

    # DQ-005 — chronology (completion >= start)
    v = conn.execute("""
        SELECT COUNT(*) FROM studies
        WHERE start_date IS NOT NULL AND completion_date IS NOT NULL
          AND completion_date < start_date
    """).fetchone()[0]
    sample = pd.read_sql("""
        SELECT nct_id, start_date, completion_date FROM studies
        WHERE start_date IS NOT NULL AND completion_date IS NOT NULL
          AND completion_date < start_date LIMIT 3
    """, conn).to_dict('records')
    record('DQ-005', 'A trial cannot complete before it starts', 'Critical', v, sample)

    # DQ-006 — future-dating: a trial cannot START after today unless not-yet-recruiting
    v = conn.execute("""
                     SELECT COUNT(*)
                     FROM studies
                     WHERE start_date > date ('now')
                       AND status NOT IN ('NOT_YET_RECRUITING'
                         , 'RECRUITING')
                     """).fetchone()[0]
    record('DQ-006', 'Trials starting in the future must have a pre-launch status',
           'Medium', v)

    # DQ-007 — enrollment non-negative
    v = conn.execute("""
        SELECT COUNT(*) FROM studies WHERE enrollment < 0
    """).fetchone()[0]
    record('DQ-007', 'Enrollment must be non-negative', 'High', v)

    # DQ-008 — status controlled vocabulary
    statuses = pd.read_sql("SELECT DISTINCT status FROM studies WHERE status IS NOT NULL", conn)
    invalid = set(statuses['status']) - VALID_STATUSES
    record('DQ-008', 'Status must belong to the controlled vocabulary',
           'Medium', len(invalid), list(invalid))

    # DQ-009 — phase controlled vocabulary
    phases = pd.read_sql("SELECT DISTINCT phase FROM studies WHERE phase IS NOT NULL", conn)
    invalid = set(phases['phase']) - VALID_PHASES
    record('DQ-009', 'Phase must belong to the controlled vocabulary',
           'Medium', len(invalid), list(invalid))

    # DQ-010 — referential integrity across all child tables
    total_orphans = 0
    for child in ['conditions', 'interventions', 'outcomes', 'sponsors', 'locations', 'study_design']:
        n = conn.execute(f"""
            SELECT COUNT(*) FROM {child} c
            LEFT JOIN studies s ON c.study_id = s.study_id
            WHERE s.study_id IS NULL
        """).fetchone()[0]
        total_orphans += n
    record('DQ-010', 'No orphaned child records (referential integrity)',
           'Critical', total_orphans)

    # DQ-011 — completed interventional trials must have locations
    v = conn.execute("""
        SELECT COUNT(*) FROM studies s
        LEFT JOIN (SELECT DISTINCT study_id FROM locations) l ON s.study_id = l.study_id
        WHERE s.status = 'COMPLETED' AND s.study_type = 'INTERVENTIONAL'
          AND l.study_id IS NULL
    """).fetchone()[0]
    sample = pd.read_sql("""
        SELECT s.nct_id, s.status, s.study_type FROM studies s
        LEFT JOIN (SELECT DISTINCT study_id FROM locations) l ON s.study_id = l.study_id
        WHERE s.status = 'COMPLETED' AND s.study_type = 'INTERVENTIONAL'
          AND l.study_id IS NULL LIMIT 3
    """, conn).to_dict('records')
    record('DQ-011', 'Completed interventional trials must have at least one location',
           'Medium', v, sample)

    # DQ-012 — zero enrollment implies non-recruiting status
    v = conn.execute("""
        SELECT COUNT(*) FROM studies
        WHERE enrollment = 0
          AND status NOT IN ('WITHDRAWN', 'NOT_YET_RECRUITING')
    """).fetchone()[0]
    record('DQ-012', 'Zero enrollment only permitted for WITHDRAWN/NOT_YET_RECRUITING',
           'Low', v)


def report():
    df = pd.DataFrame(results)

    print("\n" + "="*70)
    print("DATA QUALITY TEST SUITE — RESULTS")
    print("="*70)
    print(df[['test_id', 'status', 'severity', 'violations', 'rule']].to_string(index=False))

    passed = (df['status'] == 'PASS').sum()
    failed = (df['status'] == 'FAIL').sum()
    print(f"\nSummary: {passed} passed, {failed} failed, {len(df)} total")

    # Defects by severity
    defects = df[df['status'] == 'FAIL']
    if len(defects) > 0:
        print("\nDefects by severity:")
        print(defects.groupby('severity')['test_id'].count().to_string())

    return df


def write_defect_log(df):
    defects = df[df['status'] == 'FAIL'].copy()
    lines = [
        "# Data Quality Defect Log",
        f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"\nTests executed: {len(df)} | Passed: {(df['status']=='PASS').sum()} | Failed: {len(defects)}",
        "\n---\n"
    ]

    if len(defects) == 0:
        lines.append("No defects detected.\n")
    else:
        for i, row in enumerate(defects.itertuples(), start=1):
            lines.append(f"## DEF-{i:03d} — {row.test_id}\n")
            lines.append(f"- **Rule violated:** {row.rule}")
            lines.append(f"- **Severity:** {row.severity}")
            lines.append(f"- **Affected records:** {row.violations}")
            if row.sample:
                lines.append(f"- **Examples:** `{row.sample}`")
            lines.append("")

    DEFECT_LOG_PATH.write_text("\n".join(lines), encoding='utf-8')
    print(f"\nDefect log written to {DEFECT_LOG_PATH}")


if __name__ == '__main__':
    conn = sqlite3.connect(DB_PATH)
    run_tests(conn)
    df = report()
    write_defect_log(df)
    conn.close()


