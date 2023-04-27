"""Script version of the influxdb_data_model.ipynb notebook."""

import requests

from squash.tasks.influxdb import create_influxdb_database, write_influxdb_line
from squash.tasks.utils.transformation import Transformer

SQUASH_API_URL = "https://squash-sandbox.lsst.codes/"

response = requests.get(SQUASH_API_URL + "/jobs").json()
ids = response["ids"]
number_of_jobs = len(ids)
print(f"Found {number_of_jobs} jobs in the SQuaSH API")

# These environment variables define the InfluxDB instance.
INFLUXDB_API_URL = "https://squash-sandbox.lsst.codes/influxdb"
INFLUXDB_DATABASE = "squash-sandbox"
INFLUXDB_USERNAME = "admin"
INFLUXDB_PASSWORD = ""

# Create the destination InfluxDB database if it does not exist.
status_code = create_influxdb_database(
    INFLUXDB_DATABASE, INFLUXDB_API_URL, INFLUXDB_USERNAME, INFLUXDB_PASSWORD
)
status_code

# Transform jobs to InfluxDB line protocol format.
influxdb_lines = []
for id in ids:
    data = requests.get(SQUASH_API_URL + "/job/{}".format(id)).json()

    dataset = data["ci_dataset"]

    print(f"Transforming job {id}, dataset {dataset} to InfluxDB format.")

    transformer = Transformer(squash_api_url=SQUASH_API_URL, data=data)

    influxdb_lines.extend(transformer.to_influxdb_line())


# Write to InfluxDB
for line in influxdb_lines:
    status_code = write_influxdb_line(
        line,
        INFLUXDB_DATABASE,
        INFLUXDB_API_URL,
        INFLUXDB_USERNAME,
        INFLUXDB_PASSWORD,
    )
    if status_code != 204:
        print(line)
