import os
import numpy as np
import requests
from pytz import UTC
from datetime import datetime
from dateutil.parser import parse

from .celery import celery

INFLUXDB_API_URL = os.environ.get('INFLUXDB_API_URL')
INFLUXDB_DATABASE = os.environ.get('INFLUXDB_DATABASE')


def format_timestamp(date):
    """ Format timestamp as required by the InfluxDB line protocol.

        Parameters
        ----------
        date: `<str>`
            Timestamp string

        Returns
        -------
        timestamp: `<int>`
            Timestamp in nanosecond-precision Unix time.
            See https://docs.influxdata.com/influxdb/v1.6/write_protocols/
    """

    epoch = UTC.localize(datetime.utcfromtimestamp(0))

    timestamp = int((parse(date) - epoch).total_seconds() * 1e9)

    return timestamp


def format_line(measurement, tags, fields, timestamp):
    """ Format an InfluxDB line.

        Parameters
        ----------
        measurement: `<str>`
            Name of the InfluxDB measurement
        tags: `<list>`
            A list of valid InfluxDB tags
        fields: `<list>`
            A list of valid InfluxDB fields
        timestamp: `int`
            A timestamp as returned by `format_timestamp()`

        Returns
        -------
        line: `<str>`
            An InfluxDB line as defined by the line protocol in
            https://docs.influxdata.com/influxdb/v1.6/write_protocols/
    """
    line = "{},{} {} {}".format(measurement, ",".join(tags), ",".join(fields),
                                timestamp)
    return line


def send_to_influxdb(influxdb_line):
    """ Send a line to an InfluxDB database. It assumes the database already
        exists.

        Parameters
        ----------
        influxdb_line: `<str>`
            An InfluxDB line as defined by the line protocol in
            https://docs.influxdata.com/influxdb/v1.6/write_protocols/

        status_code: `<int>`
            Status code from the InfluxDB HTTP API.
    """

    params = {'db': INFLUXDB_DATABASE}
    r = requests.post(url=INFLUXDB_API_URL + "/write", params=params,
                      data=influxdb_line)

    return r.status_code, r.text


@celery.task(bind=True)
def job_to_influxdb(self, job_id, date_created, data):
    """ Unpack a SQuaSH job and send to InfluxDB

        Parameters
        ----------
        data: `<dict>`
            A dictionary containing the job data

        Returns
        -------
        status_code: `<int>`
             204:
               The request was processed successfully
             400:
               Malformed syntax or bad query

        Note
        ----
        A lsst.verify measurement and an InfluxDB measurement are different
        things. See e.g.:
        https://docs.influxdata.com/influxdb/v1.6/concepts/key_concepts/
    """

    # The datamodel for a SQuaSH job in InfluxDB maps each verification package
    # to an InfluxDB measurement, verification job metadata to InfluxDB
    # tags and metric names and values to fields.

    # Here we associate metrics (fields) to their corresponding
    # packages (measurements)

    fields = {}
    for meas in data['measurements']:
        influxdb_measurement = meas['metric'].split('.')[0]

        if influxdb_measurement not in fields:
            fields[influxdb_measurement] = []

        # Skip None, np.nan and np.inf values
        if meas['value'] is not None and np.isfinite(meas['value']):
            fields[influxdb_measurement].append("{}={}".format(meas['metric'],
                                                               meas['value']))

    timestamp = ""
    if date_created:
        timestamp = format_timestamp(date_created)

    # add the squash job_id and the ci_dataset as metadata
    data['meta']['squash_id'] = job_id

    if 'ci_dataset' in data['meta']['env']:
        data['meta']['ci_dataset'] = data['meta']['env']['ci_dataset']

    if 'ci_id' in data['meta']['env']:
        data['meta']['ci_id'] = data['meta']['env']['ci_id']

    # skip other job metadata when forming tags
    del data['meta']['env']
    del data['meta']['packages']

    tags = []
    for key, value in data['meta'].items():
        # scape white space, comma and equal sign characters
        # https://docs.influxdata.com/influxdb/v0.13/write_protocol
        key = key.replace(" ", "\ ") # noqa
        key = key.replace(",", "\,") # noqa
        key = key.replace("=", "\=") # noqa
        if type(value) == str:
            value = value.replace(" ", "\ ") # noqa
            value = value.replace(",", "\,") # noqa
            value = value.replace("=", "\=") # noqa

        tags.append("{}={}".format(key, value))

    for measurement in fields:
        influxdb_line = format_line(measurement, tags, fields[measurement],
                                    timestamp)

        status_code, message = send_to_influxdb(influxdb_line)

    return status_code, message
