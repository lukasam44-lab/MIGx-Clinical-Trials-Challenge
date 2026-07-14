import json
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = PROJECT_ROOT / 'data' / 'raw_studies.json'
DB_PATH = PROJECT_ROOT / 'data' / 'clinical_trials.db'


# ---------- Helpers ----------

def safe_get(data, *keys):
    """Safely walk a nested dict. Returns None if any key is missing."""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key)
        else:
            return None
    return data


def first_or_none(value):
    """Return the first item of a list, or None."""
    if isinstance(value, list) and len(value) > 0:
        return value[0]
    return None


# ---------- Transform: studies (single-value fields) ----------

def transform_study(study):
    protocol = study.get('protocolSection', {})
    return {
        'nct_id':      safe_get(protocol, 'identificationModule', 'nctId'),
        'title':       safe_get(protocol, 'identificationModule', 'briefTitle'),
        'acronym':     safe_get(protocol, 'identificationModule', 'acronym'),
        'status':      safe_get(protocol, 'statusModule', 'overallStatus'),
        'phase':       first_or_none(safe_get(protocol, 'designModule', 'phases')),
        'study_type':  safe_get(protocol, 'designModule', 'studyType'),
        'start_date':  safe_get(protocol, 'statusModule', 'startDateStruct', 'date'),
        'completion_date': safe_get(protocol, 'statusModule', 'completionDateStruct', 'date'),
        'primary_completion_date': safe_get(protocol, 'statusModule', 'primaryCompletionDateStruct', 'date'),
        'enrollment':      safe_get(protocol, 'designModule', 'enrollmentInfo', 'count'),
        'enrollment_type': safe_get(protocol, 'designModule', 'enrollmentInfo', 'type'),
        'brief_summary':   safe_get(protocol, 'descriptionModule', 'briefSummary'),
        'eligibility_criteria': safe_get(protocol, 'eligibilityModule', 'eligibilityCriteria'),
        'gender':          safe_get(protocol, 'eligibilityModule', 'sex'),
    }


# ---------- Transform: child tables (lists) ----------

def transform_conditions(study, study_id):
    protocol = study.get('protocolSection', {})
    conditions = safe_get(protocol, 'conditionsModule', 'conditions') or []
    return [{'study_id': study_id, 'condition_name': c, 'mesh_term': None}
            for c in conditions]


def transform_interventions(study, study_id):
    protocol = study.get('protocolSection', {})
    interventions = safe_get(protocol, 'armsInterventionsModule', 'interventions') or []
    return [{'study_id': study_id,
             'intervention_type': i.get('type'),
             'name': i.get('name'),
             'description': i.get('description')}
            for i in interventions]


def transform_outcomes(study, study_id):
    protocol = study.get('protocolSection', {})
    rows = []
    for out_type, key in [('primary', 'primaryOutcomes'), ('secondary', 'secondaryOutcomes')]:
        outcomes = safe_get(protocol, 'outcomesModule', key) or []
        for o in outcomes:
            rows.append({'study_id': study_id,
                         'outcome_type': out_type,
                         'measure': o.get('measure'),
                         'time_frame': o.get('timeFrame'),
                         'description': o.get('description')})
    return rows


def transform_sponsors(study, study_id):
    protocol = study.get('protocolSection', {})
    sponsor_mod = protocol.get('sponsorCollaboratorsModule', {})
    rows = []
    # The single lead sponsor
    lead = sponsor_mod.get('leadSponsor')
    if lead:
        rows.append({'study_id': study_id,
                     'agency': lead.get('name'),
                     'agency_class': lead.get('class'),
                     'lead_or_collaborator': 'lead'})
    # The list of collaborators
    collaborators = sponsor_mod.get('collaborators') or []
    for c in collaborators:
        rows.append({'study_id': study_id,
                     'agency': c.get('name'),
                     'agency_class': c.get('class'),
                     'lead_or_collaborator': 'collaborator'})
    return rows


def transform_locations(study, study_id):
    protocol = study.get('protocolSection', {})
    locations = safe_get(protocol, 'contactsLocationsModule', 'locations') or []
    return [{'study_id': study_id,
             'facility': loc.get('facility'),
             'city': loc.get('city'),
             'state': loc.get('state'),
             'country': loc.get('country'),
             'continent': None}   # data gap: derive later or leave null
            for loc in locations]


def transform_study_design(study, study_id):
    protocol = study.get('protocolSection', {})
    design_info = safe_get(protocol, 'designModule', 'designInfo') or {}
    return {'study_id': study_id,
            'allocation': design_info.get('allocation'),
            'intervention_model': design_info.get('interventionModel'),
            'masking': safe_get(design_info, 'maskingInfo', 'masking'),
            'primary_purpose': design_info.get('primaryPurpose'),
            'observational_model': design_info.get('observationalModel'),
            'time_perspective': design_info.get('timePerspective')}


# ---------- Load: insert helpers ----------

def insert_row(conn, table, row):
    """Insert one dict as a row; returns the new row's id."""
    columns = ', '.join(row.keys())
    placeholders = ', '.join(['?'] * len(row))
    sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
    cursor = conn.execute(sql, list(row.values()))
    return cursor.lastrowid


def insert_rows(conn, table, rows):
    """Insert many dicts into a table."""
    for row in rows:
        insert_row(conn, table, row)


# ---------- Main ETL ----------

def run_etl():
    with open(RAW_PATH, 'r', encoding='utf-8') as f:
        raw_studies = json.load(f)
    print(f"Loaded {len(raw_studies)} raw studies")

    conn = sqlite3.connect(DB_PATH)

    studies_loaded = 0
    for study in raw_studies:
        # 1. Insert the parent study, capture its assigned study_id
        study_row = transform_study(study)
        study_id = insert_row(conn, 'studies', study_row)

        # 2. Insert all child records using that study_id
        insert_rows(conn, 'conditions',    transform_conditions(study, study_id))
        insert_rows(conn, 'interventions', transform_interventions(study, study_id))
        insert_rows(conn, 'outcomes',      transform_outcomes(study, study_id))
        insert_rows(conn, 'sponsors',      transform_sponsors(study, study_id))
        insert_rows(conn, 'locations',     transform_locations(study, study_id))
        insert_row(conn, 'study_design',   transform_study_design(study, study_id))

        studies_loaded += 1

    conn.commit()

    # Verify: count rows in each table
    print(f"\nLoaded {studies_loaded} studies. Row counts per table:")
    for table in ['studies', 'conditions', 'interventions', 'outcomes',
                  'sponsors', 'locations', 'study_design']:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:15} : {count}")

    conn.close()


if __name__ == '__main__':
    run_etl()