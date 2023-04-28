"""Create the squash-api app.

To run the app in development mode set the following variables:

    export SQUASH_API_PROFILE=squash.config.Development
    export FLASK_APP=app:app
    export FLASK_ENV=development
    flask run

If FLASK_ENV is set to development, the flask command will enable debug mode
and `flask run` will enable the interactive debugger and reloader.

See app/config.py for the app configuration.
"""


__all__ = ["create_app"]

import os

from flask import Flask
from flask_jwt import JWT
from flask_restful import Api

from squash.api_v1.code_changes import CodeChanges
from squash.api_v1.dataset import DatasetList
from squash.api_v1.jenkins import Jenkins
from squash.api_v1.job import Job, JobList, JobWithArg
from squash.api_v1.measurement import Measurement, MeasurementList
from squash.api_v1.metric import Metric, MetricList
from squash.api_v1.package import PackageList
from squash.api_v1.root import Root
from squash.api_v1.specification import Specification, SpecificationList
from squash.api_v1.stats import Stats
from squash.api_v1.status import Status
from squash.api_v1.user import Register, User, UserList
from squash.api_v1.version import Version
from squash.auth import authenticate, identity
from squash.models import UserModel


def create_app(profile):
    """Create an instance of the flask app.

    Parameters
    ----------
    profile: `str`
        One of the app configuration profiles, `app.config.Development`,
        `app.config.Testing` or `app.config.Production`.

    Return
    ------
    app: `object`
        A flask app instance.
    """
    app = Flask(__name__)
    app.config.from_object(profile)

    # initialize the database
    from squash.models import db

    db.init_app(app)

    with app.app_context():
        db.create_all()

        # create admin user
        if UserModel.query.get(1) is None:
            user = UserModel(
                username=app.config["DEFAULT_USER"],
                password=app.config["DEFAULT_PASSWORD"],
            )
            user.save_to_db()

    # add authentication route /auth
    JWT(app, authenticate, identity)

    # register api resources
    api = Api(app)

    # Redirect root url to api documentation
    api.add_resource(Root, "/")

    # Generic Job resource
    api.add_resource(Job, "/job", endpoint="job")

    # Because flasgger cannot handle endpoints with multiple URLs,
    # the methods that require the job_id argument are implemented
    # separately in a different resource.
    # See the status of this issue and the reason for this
    # workaround at
    # https://github.com/rochacbruno/flasgger/issues/174
    api.add_resource(JobWithArg, "/job/<int:job_id>", endpoint="jobwitharg")
    api.add_resource(JobList, "/jobs", endpoint="jobs")

    # Resource for jobs in the jenkins enviroment
    api.add_resource(Jenkins, "/jenkins/<string:ci_id>", endpoint="jenkins")

    # Status of the upload
    api.add_resource(Status, "/status/<string:task_id>", endpoint="status")

    # User resources
    api.add_resource(User, "/user/<string:username>", endpoint="user")
    api.add_resource(UserList, "/users", endpoint="users")
    api.add_resource(Register, "/register", endpoint="register")

    # Metric resources
    api.add_resource(Metric, "/metric/<string:name>", endpoint="metric")
    api.add_resource(MetricList, "/metrics", endpoint="metrics")

    # Metric specifications resources
    api.add_resource(Specification, "/spec/<string:name>", endpoint="spec")
    api.add_resource(SpecificationList, "/specs", endpoint="specs")

    # Metric measurement resources
    api.add_resource(
        Measurement, "/measurement/<int:job_id>", endpoint="measurement"
    )
    api.add_resource(MeasurementList, "/measurements", endpoint="measurements")

    # Apps
    api.add_resource(DatasetList, "/datasets", endpoint="datasets")
    api.add_resource(PackageList, "/packages", endpoint="packages")
    api.add_resource(
        CodeChanges, "/code_changes/<string:ci_id>", endpoint="code_changes"
    )

    # Miscellaneous
    api.add_resource(Version, "/version", endpoint="version")
    api.add_resource(Stats, "/stats", endpoint="stats")

    return app


profile = os.environ.get("SQUASH_API_PROFILE", "squash.config.Development")

if profile in ["squash.config.Development", "squash.config.Production"]:
    app = create_app(profile)
