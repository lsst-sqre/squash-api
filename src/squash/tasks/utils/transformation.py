"""Transform metrics stored in SQuaSH into InfluxDB format.

See sqr-009.lsst.io for a description on how metrics are stored in SQuaSH and
the resulting InfluxDB data model.
"""

__all__ = ["Transformer"]

import logging
import pathlib
import urllib.parse

import numpy as np
import requests
import yaml
from requests.exceptions import ConnectionError, HTTPError

from squash.tasks.utils.format import Formatter

logger = logging.getLogger("squash")


class Transformer(Formatter):
    """Transform metrics stored in SQuaSH into InfluxDB format.

    Parameters
    ----------
    squash_api_url : `str`
        SQuaSH API URL.
    data : `str`
        SQuaSH job data in JSON.
    """

    def __init__(self, squash_api_url, data):

        super().__init__(squash_api_url=squash_api_url)

        self.squash_api_url = squash_api_url
        self.data = data
        self.mapping = self.load_mapping()

    def load_mapping(self):
        """Load the SQuaSH to InfluxDB mapping.

        Returns
        -------
        mapping : `dict`
            Dictionary with the SQuaSH to InfluxDB mapping.
        """
        filename = pathlib.Path(__file__).parent / "mapping.yaml"

        with open(filename) as f:
            mapping = yaml.load(f, Loader=yaml.FullLoader)

        return mapping

    def run_mapping(self, key):
        """Return schema, key, and transformation from the mapping.

        Parameters
        ----------
        key : `str`
            The key to look for in the mapping.

        Returns
        -------
        schema : `str` or `None`
            The InfluxDB schema to write or `None` if it should not
            be added to InfluxDB.

        mapped_key : `str` or `None`
            The mapped key or `None` if it should not be added to InfluxDB.

        transformation : `str` or `None`
            The transformation that should be applied to the value if any.
        """
        # By default, if the key is not found in the mapping, it should be
        # added to InfluxDB as a tag and preserving the original name.
        schema = "tag"
        mapped_key = key
        transformation = None

        if key in self.mapping:
            item = self.mapping[key]
            schema = item["schema"]
            mapped_key = item["key"]
            transformation = item["transformation"]

        return schema, mapped_key, transformation

    def get_timestamp(self):
        """Get the timestamp to use in InfluxDB.

        Use the timestamp when the verification job is recorded. If it runs
        in Jenkins uses the pipeline runtime instead.

        Returns
        -------
        timestamp : `int`
            Formatted timestamp.
        """
        timestamp = Formatter.format_timestamp(self.data["date_created"])
        logger.debug(f"Using timestamp from the job {timestamp}.")

        if self.data["meta"]["env"]["env_name"] == "jenkins":

            ci_id = self.data["meta"]["env"]["ci_id"]
            ci_name = self.data["meta"]["env"]["ci_name"]

            # Make sure the job ran in Jenkins, i.e has valid ci_id and ci_name
            if ci_id == "unknown" or ci_name == "unknown":
                return timestamp

            # Get timestamp from Jenkins
            jenkins_url = (
                f"{self.squash_api_url}/jenkins/{ci_id}?ci_name={ci_name}"
            )
            try:
                r = requests.get(jenkins_url)
                r.raise_for_status()
            except HTTPError:
                message = "Could not get timestamp from Jenkins."
                logger.error(message)
                raise
            except ConnectionError:
                message = (
                    f"Failed to establish connection with Jenkins "
                    f"{jenkins_url}."
                )
                logger.error(message)
                raise

            date_created = r.json()["date_created"]
            timestamp = Formatter.format_timestamp(date_created)
            logger.debug(f"Using timestamp from Jenkins {timestamp}.")

        return timestamp

    def update_metadata(self):
        """Add/remove metadata before the trandformation step."""
        # Add extra metadata
        id = self.data["id"]
        self.data["meta"]["id"] = id
        self.data["meta"]["url"] = urllib.parse.urljoin(
            self.squash_api_url, f"/job/{id}"
        )

        self.data["meta"]["date_created"] = self.data["date_created"]
        self.data["meta"]["env"]["ci_dataset"] = self.data["ci_dataset"]

        # Fix dataset_repo_url duplication
        if "dataset_repo_url" in self.data["meta"].keys():
            del self.data["meta"]["dataset_repo_url"]

        # Fix use of ci_dataset key in environments other than jenkins
        if self.data["meta"]["env"]["env_name"] != "jenkins":
            if "ci_dataset" in self.data["meta"]["env"]:
                del self.data["meta"]["env"]["ci_dataset"]

        # Add code changes metadata keys
        if self.data["meta"]["env"]["env_name"] == "jenkins":
            self.data["meta"]["env"]["code_changes"] = ""
            self.data["meta"]["env"]["code_changes_counts"] = ""

        # Add ci_name until DM-18599 is not implemented
        if "ci_url" in self.data["meta"]["env"].keys():

            if "validate_drp_gen3" in self.data["meta"]["env"]["ci_url"]:
                self.data["meta"]["env"]["ci_name"] = "validate_drp_gen3"
            elif "validate_drp" in self.data["meta"]["env"]["ci_url"]:
                self.data["meta"]["env"]["ci_name"] = "validate_drp"
            elif "ap_verify" in self.data["meta"]["env"]["ci_url"]:
                self.data["meta"]["env"]["ci_name"] = "ap_verify"

    def process_metadata(self, data):
        """Process SQuaSH metadata using a pre-configured mapping to InfluxDB.

        Parameters
        ----------
        data : `dict`
            A dictionary with SQuaSH metadata.

        Return
        ------
        tags : `<list>`
            List of tags to be written to InfluxDB.
        fields : `<list>`
            List of fields to be written to InfluxDB.
        """
        tags = []
        fields = []
        for key, value in data.items():
            # process nested dict
            if isinstance(value, dict):
                tmp_tags, tmp_fields = self.process_metadata(value)
                tags.extend(tmp_tags)
                fields.extend(tmp_fields)
            else:
                schema, mapped_key, transformation = self.run_mapping(key)
                if transformation:
                    value = eval(transformation)
                if mapped_key and schema == "tag":
                    tags.append(
                        "{}={}".format(
                            Formatter.sanitize(mapped_key),
                            Formatter.sanitize(value),
                        )
                    )
                elif mapped_key and schema == "field":
                    if isinstance(value, str):
                        fields.append(
                            '{}="{}"'.format(
                                Formatter.sanitize(mapped_key), value
                            )
                        )
                    else:
                        fields.append(
                            "{}={}".format(
                                Formatter.sanitize(mapped_key), value
                            )
                        )

        # Make sure tags and fields are unique
        tags = list(set(tags))
        fields = list(set(fields))

        return tags, fields

    def get_meas_by_package(self):
        """Group verify measurements by package.

        By grouping verify measurements by package we can send them to InfluxDB
        in batch. A package is mapped to an InfluxDB measurement.
        """
        meas_by_package = {}
        for meas in self.data["measurements"]:
            # DM-18360 - SQuaSH API/measurements should return the verification
            # package
            # a metric fqn is <package>.<metric>, extract package name from the
            # metric fqn
            package = None
            if "." in meas["metric"]:
                package = meas["metric"].split(".")[0]

            if package:
                # No need to carry the package name prefix in the metric name.
                if meas["metric"].startswith(package):
                    metric = meas["metric"][len(package) + 1 :]

                value = meas["value"]
                # Skip None, np.nan and np.inf value
                if value is not None and np.isfinite(value):
                    if package not in meas_by_package:
                        meas_by_package[package] = []
                    meas_by_package[package].append(f"{metric}={value}")

        return meas_by_package

    def to_influxdb_line(self):
        """Process job data and make the InfluxDB lines.

        Returns
        -------
        influxdb_lines : `list`
            A list with strings representing each InfluxDB line.
        """
        timestamp = self.get_timestamp()

        self.update_metadata()

        tags, extra_fields = self.process_metadata(self.data["meta"])

        meas_by_package = self.get_meas_by_package()

        influxdb_lines = []
        for meas in meas_by_package:
            fields = meas_by_package[meas] + extra_fields
            influxdb_lines.append(
                Formatter.format_influxdb_line(meas, tags, fields, timestamp)
            )

        return influxdb_lines
