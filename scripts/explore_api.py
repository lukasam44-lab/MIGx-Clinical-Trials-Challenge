import requests

# The API endpoint (the "restaurant address")
BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

# Parameters — our specific "order" to the waiter
params = {
    "pageSize": 1     # "bring me just 1 study for now"
}

# Make the call — pick up the phone and ask
response = requests.get(BASE_URL, params=params)

# Check it worked
print("Status code:", response.status_code)
print("Type of response:", type(response))


# Convert the JSON response into Python dictionaries/lists
data = response.json()

# What are the top-level keys? (the main sections of the response)
print("Top-level keys:", data.keys())

import json

# Grab the first (only) study from the studies list
first_study = data['studies'][0]

# Pretty-print its structure so we can read the nesting
print(json.dumps(first_study, indent=2)[:3000])


first_study = data['studies'][0]
protocol = first_study['protocolSection']

# What modules exist in this study
print("Available modules:")
for module_name in protocol.keys():
    print("  -", module_name)




first_study = data['studies'][0]
protocol = first_study['protocolSection']

# Inspect the list-type modules that become their own tables
for mod in ['conditionsModule', 'designModule', 'sponsorCollaboratorsModule',
            'contactsLocationsModule', 'armsInterventionsModule']:
    print(f"\n===== {mod} =====")
    if mod in protocol:
        print(json.dumps(protocol[mod], indent=2)[:1200])
    else:
        print("(not present in this study)")



first_study = data['studies'][0]
protocol = first_study['protocolSection']

for mod in ['eligibilityModule', 'outcomesModule']:
    print(f"\n===== {mod} =====")
    if mod in protocol:
        print(json.dumps(protocol[mod], indent=2)[:1500])
    else:
        print("(not present in this study)")

        