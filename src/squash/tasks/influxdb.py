"""Implement Celery task to write SQuaSH metrics to InfluxDB."""

__all__ = [
    "create_influxdb_database",
    "write_influxdb_line",
    "job_to_influxdb",
]

import importlib
import logging
import os

import requests

from .celery import squash_tasks
from .utils.transformation import Transformer

profile = os.environ.get("SQUASH_API_PROFILE", "squash.config.Development")
cls = profile.split(".")[2]
config = getattr(importlib.import_module("squash.config"), cls)()

logger = logging.getLogger("squash")


def create_influxdb_database(
    influxdb_database,
    influxdb_api_url,
    influxdb_username=None,
    influxdb_password=None,
):
    """Create a database in InfluxDB.

    Parameters
    ----------
    influxdb_database: `str`
        Name of the databse to create in InfluxDB.
    influxdb_api_url: `str`
        URL for the InfluxDB HTTP API.
    influxdb_username: `str`
        InfluxDB username, by default set from the INFLUXDB_USERNAME env var.
    influxdb_password: `str`
        InfluxDB password, by default set from the INFLUXDB_PASSWORD env var.

    Returns
    -------
    status_code: `int`
        Status code from the InfluxDB HTTP API.
        200: The request was processed successfully.
        400: Malformed syntax or bad query.
        401: Unathenticated request.
    """
    # credentials defined in the environment take precedence
    influxdb_username = os.environ.get("INFLUXDB_USERNAME", influxdb_username)
    influxdb_password = os.environ.get("INFLUXDB_PASSWORD", influxdb_password)

    params = {
        "q": f'CREATE DATABASE "{influxdb_database}"',
        "u": influxdb_username,
        "p": influxdb_password,
    }

    status_code = 500
    try:
        r = requests.post(url=f"{influxdb_api_url}/query", params=params)
        r.raise_for_status()
        status_code = r.status_code
    except requests.exceptions.RequestException as err:
        message = (
            f"Could not create InfluxDB database {influxdb_database}.\n{err}"
        )
        logger.error(message)

    return status_code


def write_influxdb_line(
    line,
    influxdb_database,
    influxdb_api_url,
    influxdb_username=None,
    influxdb_password=None,
):
    """Write a line to InfluxDB.

    Parameters
    ----------
    line : `str`
        An InfluxDB line formatted according to the line protocol:
        See https://docs.influxdata.com/influxdb/v1.8/write_protocols/

    Returns
    -------
    status_code : `int`
        Status code from the InfluxDB HTTP API.
        204: The request was processed successfully.
        400: Malformed syntax or bad query.
        401: Unathenticated request.
    """
    params = {
        "db": influxdb_database,
        "u": influxdb_username,
        "p": influxdb_password,
    }

    url = f"{influxdb_api_url}/write"
    status_code = 500
    try:
        r = requests.post(url=url, params=params, data=line)
        r.raise_for_status()
        status_code = r.status_code
    except requests.exceptions.RequestException as err:
        message = f"Could not write line to InfluxDB {line}.\n{err}"
        logger.error(message)

    return status_code


@squash_tasks.task(bind=True)
def job_to_influxdb(self, job_id):
    """Transform a SQuaSH job into InfluxDB lines and send to InfluxDB.

    Parameters
    ----------
    job_id : `int`
        ID for the SQuaSH job

    Returns
    -------
    status_code : `int`
        Status code from the InfluxDB or SQuaSH APIs
        200 or 204: The request was processed successfully
        400: Malformed syntax or bad query
        401: Unathenticated request.
    """
    status_code = create_influxdb_database(
        config.INFLUXDB_DATABASE, config.INFLUXDB_API_URL
    )

    if status_code != 200:
        message = "Could not create InfluxDB database."
        return {"message": message, "status_code": status_code}

    # Get job data from the SQuaSH API
    job_url = f"{config.SQUASH_API_URL}/job/{job_id}"
    status_code = 500
    try:
        r = requests.get(url=job_url)
        r.raise_for_status()
        status_code = r.status_code
    except requests.exceptions.RequestException as err:
        message = (
            f"Failed to establish connection with {config.SQUASH_API_URL}."
        )
        logger.error(message, err)

    if status_code != 200:
        return {"message": message, "status_code": status_code}

    data = r.json()
    transformer = Transformer(squash_api_url=config.SQUASH_API_URL, data=data)

    influxdb_lines = transformer.to_influxdb_line()

    for line in influxdb_lines:
        status_code = write_influxdb_line(
            line, config.INFLUXDB_DATABASE, config.INFLUXDB_API_URL
        )

        if status_code != 204:
            message = f"Failed to write Job {job_id} to InfluxDB."
            return {"message": message, "status_code": status_code}

    message = f"Job {job_id} sucessfully written to InfluxDB."
    return {"message": message, "status_code": status_code}
