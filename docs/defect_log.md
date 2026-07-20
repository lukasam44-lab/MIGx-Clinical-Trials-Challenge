# Data Quality Defect Log

Generated: 2026-07-16 16:31

Tests executed: 12 | Passed: 9 | Failed: 3

---

## DEF-001 — DQ-003

- **Rule violated:** Critical fields (nct_id, status, study_type) must be populated
- **Severity:** High
- **Affected records:** 1

## DEF-002 — DQ-004

- **Rule violated:** Dates must be complete ISO-8601 (YYYY-MM-DD)
- **Severity:** High
- **Affected records:** 209
- **Examples:** `[{'nct_id': 'NCT01705535', 'start_date': '2012-10', 'completion_date': '2019-07'}, {'nct_id': 'NCT00358735', 'start_date': '2006-06', 'completion_date': '2008-12'}, {'nct_id': 'NCT00738335', 'start_date': '2009-01', 'completion_date': '2009-07'}]`

## DEF-003 — DQ-011

- **Rule violated:** Completed interventional trials must have at least one location
- **Severity:** Medium
- **Affected records:** 14
- **Examples:** `[{'nct_id': 'NCT00152035', 'status': 'COMPLETED', 'study_type': 'INTERVENTIONAL'}, {'nct_id': 'NCT00200525', 'status': 'COMPLETED', 'study_type': 'INTERVENTIONAL'}, {'nct_id': 'NCT00000489', 'status': 'COMPLETED', 'study_type': 'INTERVENTIONAL'}]`


## DQ-013 | Condition names should map to a controlled vocabulary
- **Detect near-duplicate condition labels (case/spacing/synonym variants)**
- **Manual review required** — mesh_term unavailable**
- **Severity:** Medium**