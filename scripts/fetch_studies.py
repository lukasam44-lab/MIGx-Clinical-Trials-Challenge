import requests
import json
import time
from pathlib import Path

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / 'data' / 'raw_studies.json'

def fetch_studies(target_count=500, page_size=100):
    """Fetch studies from ClinicalTrials.gov v2 API using pagination."""
    all_studies = []
    next_token = None          # no token on the first call
    page_number = 1

    while len(all_studies) < target_count:
        # Build the parameters for this call
        params = {"pageSize": page_size}
        if next_token:                      # add the bookmark if we have one
            params["pageToken"] = next_token

        # EXTRACT: make the call
        response = requests.get(BASE_URL, params=params)

        # QA reflex: verify the call succeeded before trusting it
        if response.status_code != 200:
            print(f"ERROR: status {response.status_code} on page {page_number}")
            break

        data = response.json()
        page_studies = data.get('studies', [])
        all_studies.extend(page_studies)     # add this page's studies to our collection

        print(f"Page {page_number}: fetched {len(page_studies)} studies "
              f"(total so far: {len(all_studies)})")

        # Get the bookmark for the next page
        next_token = data.get('nextPageToken')

        # If there's no token, we've reached the end of the data
        if not next_token:
            print("No more pages — reached the end of available data.")
            break

        page_number += 1
        time.sleep(0.5)     # be polite to the API — brief pause between calls

    # Trim to exactly target_count (last page may overshoot)
    all_studies = all_studies[:target_count]

    # Save the raw fetched data to a file
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_studies, f, indent=2)

    print(f"\nDone. Saved {len(all_studies)} studies to {OUTPUT_PATH}")
    return all_studies

if __name__ == '__main__':
    fetch_studies(target_count=500, page_size=100)