import json
import os
import requests
from datetime import datetime
# Toronto Open Data is stored in a CKAN instance. It's APIs are documented here:
# https://docs.ckan.org/en/latest/api/

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)

# To hit our API, you'll be making requests to:
base_url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"

# Datasets are called "packages". Each package can contain many "resources"
# To retrieve the metadata for this package and its resources, use the package name in this page's URL:
url = base_url + "/api/3/action/package_show"
params = { "id": "licensed-child-care-centres"}
package = requests.get(url, params = params).json()

# To get resource data:
for idx, resource in enumerate(package["result"]["resources"]):

       # for datastore_active resources:
       if resource["datastore_active"]:

           # To get all records in CSV format:
           url = base_url + "/datastore/dump/" + resource["id"]
           resource_dump_data = requests.get(url).text
           filename = f"data/daycare_list_{datetime.now().strftime('%Y%m%d')}.csv"
           with open(filename, "w") as f:
               f.write(resource_dump_data)
           print(f"Saved {filename}")