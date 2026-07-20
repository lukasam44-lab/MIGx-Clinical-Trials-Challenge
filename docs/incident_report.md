# Data Quality Incident Report

**Incident ID:** DQI-001
**Date detected:** 2026-07-16
**Detected by:** Automated data quality test suite (test DQ-004)
**Severity:** High
**Status:** Open — remediation recommended

---

## Summary

209 of 500 studies (41.8%) contain date values at month-level precision (YYYY-MM) rather
than the full ISO-8601 day-level precision (YYYY-MM-DD) that the schema declares. Affected
fields: start_date, completion_date, primary_completion_date.

## Detection

Surfaced during Dimension 3 profiling (type consistency) and formalized as test case DQ-004:
"All non-null dates must be complete ISO-8601 (length 10)." The test flagged 209 studies with
at least one partial date. Representative examples:

| NCT ID | start_date | completion_date |
|--------|-----------|-----------------|
| NCT01705535 | 2012-10 | 2019-07 |
| NCT00358735 | 2006-06 | 2008-12 |

## Root Cause

The ClinicalTrials.gov v2 API returns dates at the precision the trial sponsor originally
submitted. Sponsors are permitted to record dates as year-month when the exact day is
unknown or not tracked — common for older trials or for estimated (versus actual) dates.
This is a **source-data characteristic, not an ingestion error**: the ETL faithfully
preserved the source precision rather than fabricating days. Verified by inspecting the raw
API response (`startDateStruct.date` field), which contains the partial values as delivered.

## Impact

**Primary impact — duration analysis (Business Question 5):** trial duration is computed as
completion_date − start_date. With month-level dates, duration carries up to ±60 days of
error per date (±120 days combined). Rather than fabricate precision, duration was computed
only on studies with both dates at full precision, reducing the analyzable sample from 190
to 104 interventional-with-phase studies — a 45% loss of usable duration data.

**Secondary impact — date comparisons:** chronology checks (completion ≥ start) and temporal
sorting are unreliable when comparing mixed-precision dates, as '2008-09' has no defined
position relative to '2008-09-15'.

**Silent-failure risk:** the imprecision is invisible in aggregate outputs. Duration averages
computed on mixed-precision dates would appear authoritative while carrying undisclosed error
— the most dangerous class of data quality issue.

## Recommended Resolution

**Immediate (analytical):**
- Flag records by date precision (a `date_precision` derived field: 'day' vs 'month')
- Restrict day-level analyses (duration) to full-precision records; disclose the sample reduction
- Report duration findings with explicit precision caveats

**Short-term (pipeline):**
- Add a `date_precision` column during ETL, derived from source string length
- Retain DQ-004 as a monitoring test; track the partial-date rate over time
- For month-only dates, document the imputation policy explicitly if days are ever needed
  (e.g. impute to the 1st, flagged as imputed — never silently)

**Long-term (governance):**
- Engage data stewards on whether sponsors can be prompted for day-level precision at submission
- Establish precision requirements per analytical use case (duration analysis requires day-level;
  landscape counts tolerate month-level)

## Lessons / Preventive Action

The incident reinforces that faithful ingestion (preserving source imperfections) is correct —
silently imputing days would have masked the issue. The defect is now guarded by an automated
test that will detect any change in the partial-date rate on future data refreshes.