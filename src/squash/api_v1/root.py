from flask import url_for
from flask_restful import Resource


class Root(Resource):
    """Lookup for resource URLs."""

    def external_url(self, endpoint):
        return url_for(endpoint, _external=True)

    def get(self):
        # List of resources we want in the API root
        endpoints = [
            "jenkins",
            "job",
            "jobs",
            "metric",
            "metrics",
            "spec",
            "specs",
            "measurement",
            "measurements",
            "register",
            "auth",
            "user",
            "users",
            "stats",
            "status",
            "version",
            "blob",
            "code_changes",
            "datasets",
            "kpms",
            "monitor",
            "packages",
        ]

        root_url = url_for("root", _external=True)

        response = {key: root_url + key for key in endpoints}

        return response
