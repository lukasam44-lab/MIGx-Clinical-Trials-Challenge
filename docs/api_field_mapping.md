# API Field → Schema Mapping

This document maps ClinicalTrials.gov v2 API response fields to our 7-table database schema.
Built and verified by inspecting live API responses. Used as the blueprint for the ingestion script.

Every path begins inside `protocolSection` (the main container in each study record).
The API returns many fields per module; we extract only the ones our schema needs and ignore the rest.

---

## studies table
One row per trial. Collects single-value fields from five modules:
identification, status, description, design, eligibility.

| Schema column            | API path                                                          | Notes |
|--------------------------|-------------------------------------------------------------------|-------|
| study_id                 | (internal)                                                        | Auto-assigned primary key, not from API |
| nct_id                   | protocolSection.identificationModule.nctId                        | External business key |
| title                    | protocolSection.identificationModule.briefTitle                   | Chose briefTitle over officialTitle for readability |
| acronym                  | protocolSection.identificationModule.acronym                      | May be absent |
| status                   | protocolSection.statusModule.overallStatus                        |  |
| phase                    | protocolSection.designModule.phases                               | LIST — take first element (schema models one phase) |
| study_type               | protocolSection.designModule.studyType                            |  |
| start_date               | protocolSection.statusModule.startDateStruct.date                 | Year-month only (e.g. "2008-09") — see data gaps |
| completion_date          | protocolSection.statusModule.completionDateStruct.date            | Year-month only |
| primary_completion_date  | protocolSection.statusModule.primaryCompletionDateStruct.date     | Year-month only |
| enrollment               | protocolSection.designModule.enrollmentInfo.count                 | Nested |
| enrollment_type          | protocolSection.designModule.enrollmentInfo.type                  | Nested (ACTUAL / ESTIMATED) |
| brief_summary            | protocolSection.descriptionModule.briefSummary                    |  |
| eligibility_criteria     | protocolSection.eligibilityModule.eligibilityCriteria             | Verified present |
| minimum_age              | (NOT provided; API gives stdAges categories instead)             | DATA GAP — leave null |
| maximum_age              | (NOT provided; API gives stdAges categories instead)             | DATA GAP — leave null |
| gender                   | protocolSection.eligibilityModule.sex                             | API field is "sex"; schema calls it "gender" |
| created_at               | (internal)                                                        | DB default timestamp |
| updated_at               | (internal)                                                        | DB default timestamp |

Ignored from these modules (no schema column): healthyVolunteers, stdAges, keywords, officialTitle, orgStudyIdInfo, etc.

---

## conditions table
One row per condition. Comes from a LIST of strings.

| Schema column   | API path                                       | Notes |
|-----------------|------------------------------------------------|-------|
| condition_id    | (internal)                                     | Auto-assigned primary key |
| study_id        | (internal)                                     | FK to studies, assigned during ingestion |
| condition_name  | protocolSection.conditionsModule.conditions    | LIST → one row per item |
| mesh_term       | (not provided by API v2)                       | Leave null |

Ignored: keywords list.

---

## interventions table
One row per intervention. Comes from a LIST of objects.

| Schema column     | API path                                                            | Notes |
|-------------------|---------------------------------------------------------------------|-------|
| intervention_id   | (internal)                                                          | Auto-assigned primary key |
| study_id          | (internal)                                                          | FK to studies |
| intervention_type | protocolSection.armsInterventionsModule.interventions[].type        | LIST → one row per item |
| name              | protocolSection.armsInterventionsModule.interventions[].name        |  |
| description       | protocolSection.armsInterventionsModule.interventions[].description | Often absent — leave null |

---

## outcomes table
One row per outcome measure. Comes from a LIST of objects.

| Schema column | API path                                                       | Notes |
|---------------|----------------------------------------------------------------|-------|
| outcome_id    | (internal)                                                     | Auto-assigned primary key |
| study_id      | (internal)                                                     | FK to studies |
| outcome_type  | (derived: "primary" / "secondary" based on source list)        | primaryOutcomes vs secondaryOutcomes; assign during ingestion |
| measure       | protocolSection.outcomesModule.primaryOutcomes[].measure       | LIST → one row per item |
| time_frame    | protocolSection.outcomesModule.primaryOutcomes[].timeFrame     | Often absent — leave null |
| description   | protocolSection.outcomesModule.primaryOutcomes[].description   | Often absent — leave null |

Note: this study's outcomes had only `measure`. type/timeFrame/description are frequently null.
outcomesModule may also contain a secondaryOutcomes list — optionally include, tagging outcome_type.

---

## sponsors table
One row per sponsor. Combines the single lead sponsor AND the list of collaborators.

| Schema column        | API path                                                          | Notes |
|----------------------|-------------------------------------------------------------------|-------|
| sponsor_id           | (internal)                                                        | Auto-assigned primary key |
| study_id             | (internal)                                                        | FK to studies |
| agency               | sponsorCollaboratorsModule.leadSponsor.name + collaborators[].name | Lead + each collaborator → rows |
| agency_class         | sponsorCollaboratorsModule.leadSponsor.class + collaborators[].class |  |
| lead_or_collaborator | (derived)                                                         | "lead" for leadSponsor; "collaborator" for each collaborator |

Ignored: responsibleParty.

---

## locations table
One row per location. Comes from a LIST of objects.

| Schema column | API path                                                     | Notes |
|---------------|--------------------------------------------------------------|-------|
| location_id   | (internal)                                                   | Auto-assigned primary key |
| study_id      | (internal)                                                   | FK to studies |
| facility      | protocolSection.contactsLocationsModule.locations[].facility | LIST → one row per item |
| city          | protocolSection.contactsLocationsModule.locations[].city     |  |
| state         | protocolSection.contactsLocationsModule.locations[].state    | Often absent for non-US — leave null |
| country       | protocolSection.contactsLocationsModule.locations[].country  |  |
| continent     | (NOT in API — derive from country, or leave null)            | DATA GAP: derive via country→continent map or document |

Ignored: overallOfficials, geoPoint (lat/lon), zip.

---

## study_design table
One row per study. Single values from designModule.designInfo.

| Schema column       | API path                                                    | Notes |
|---------------------|-------------------------------------------------------------|-------|
| design_id           | (internal)                                                  | Auto-assigned primary key |
| study_id            | (internal)                                                  | FK to studies |
| allocation          | protocolSection.designModule.designInfo.allocation          |  |
| intervention_model  | protocolSection.designModule.designInfo.interventionModel   |  |
| masking             | protocolSection.designModule.designInfo.maskingInfo.masking | Nested one extra level |
| primary_purpose     | protocolSection.designModule.designInfo.primaryPurpose      | Often absent — leave null |
| observational_model | protocolSection.designModule.designInfo.observationalModel  | Only for observational studies — else null |
| time_perspective    | protocolSection.designModule.designInfo.timePerspective     | Only for observational studies — else null |

Note: designModule feeds BOTH studies (phase, enrollment, study_type) AND study_design (designInfo sub-object).

---

## Transformation Decisions & Data Gaps (running log)

1. **Dates are year-month only** (e.g. "2008-09") — API omits the day. Decision: standardize to
   YYYY-MM-01 on load OR store as-is and flag in profiling. (Finalize during ETL; document choice.)
2. **`continent` not provided** — API gives country only. Decision: derive via a country → continent
   mapping, or leave null and document the limitation.
3. **`phase` arrives as a list** (e.g. ["NA"]) — schema models one phase; take the first element.
4. **`mesh_term` not exposed** by API v2 conditions module — leave null.
5. **`gender` vs `sex`** — schema column is `gender`; API field is `sex`. Map across.
6. **Observational-only design fields** (observational_model, time_perspective) are null for
   interventional studies, and interventional design fields are null for observational ones. Expected.
7. **Age given as categories, not numbers** — API provides `stdAges` (CHILD/ADULT/OLDER_ADULT), not
   numeric minimumAge/maximumAge. Schema's min/max age columns will be null. Data gap.
8. **Outcomes often minimal** — many studies provide only `measure`; type/timeFrame/description
   frequently null. Not a defect, but affects completeness metrics.
9. **Some fields simply absent per study** — the API returns different field subsets per record.
   Ingestion must access fields safely (return null when missing) rather than assume presence.