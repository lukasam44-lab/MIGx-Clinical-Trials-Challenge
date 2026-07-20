# Data Quality Test Plan

Each test case maps to an explicit data quality rule, has a binary pass/fail criterion,
and is executed by `scripts/data_quality_tests.py`. Failures are recorded in the defect log.

| ID | Quality Rule | Test Case                                                            | Pass Criterion | Severity |
|----|--------------|----------------------------------------------------------------------|----------------|----------|
| DQ-001 | Primary business key must be unique | No duplicate `nct_id` in studies                                     | 0 duplicates | Critical |
| DQ-002 | Identifiers must match canonical format | All `nct_id` match `^NCT\d{8}$`                                      | 0 malformed | High |
| DQ-003 | Critical fields must be populated | `nct_id`, `status`, `study_type` are non-null                        | 0 nulls | High |
| DQ-004 | Dates must be complete ISO-8601 (YYYY-MM-DD) | All non-null dates have length 10                                    | 0 partial dates | High |
| DQ-005 | Chronology: a trial cannot complete before it starts | `completion_date >= start_date` where both present                   | 0 violations | Critical |
| DQ-006 | Cross-field consistency: a trial cannot start in the future unless it is pre-launch | `start_date > today` only permitted where `status` ∈ {NOT_YET_RECRUITING, RECRUITING} | 0 violations | Medium |
| DQ-007 | Enrollment must be non-negative | `enrollment >= 0`                                                    | 0 violations | High |
| DQ-008 | Status must belong to the controlled vocabulary | `status` ∈ known ClinicalTrials.gov set                              | 0 invalid values | Medium |
| DQ-009 | Phase must belong to the controlled vocabulary | `phase` ∈ {PHASE1..PHASE4, EARLY_PHASE1, NA, NULL}                   | 0 invalid values | Medium |
| DQ-010 | Referential integrity: no orphaned child records | All child `study_id` exist in studies (6 tables)                     | 0 orphans | Critical |
| DQ-011 | Cross-field consistency: completed interventional trials must have locations | COMPLETED + INTERVENTIONAL studies have ≥1 location                  | 0 violations | Medium |
| DQ-012 | Cross-field consistency: zero enrollment implies non-recruiting status | `enrollment = 0` only where status ∈ {WITHDRAWN, NOT_YET_RECRUITING} | 0 violations | Low |