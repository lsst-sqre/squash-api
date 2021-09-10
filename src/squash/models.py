"""Implement SQuaSH API database model."""

import os
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.mysql import JSON, TIMESTAMP
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import expression
from werkzeug.security import check_password_hash, generate_password_hash

SQUASH_ETL_MODE = os.environ.get("SQUASH_ETL_MODE", False)

# Initialize extension
db = SQLAlchemy()


# https://jira.lsstcorp.org/browse/DM-12193
class now(expression.FunctionElement):
    """Use the TIMESTAMP datatype.

    Using the TIMESTAMP datatype in MySQL we Store timestamps in UTC
    computed always server side.
    """

    type = TIMESTAMP


@compiles(now, "mysql")
def mysql_now(element, compiler, **kw):
    """Implement the MySQL now() using the TIMESTAMP datatype."""
    return "CURRENT_TIMESTAMP()"


class UserModel(db.Model):
    """Database model for authenticated API users."""

    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(
        db.String(64), unique=True, index=True, nullable=False
    )
    password_hash = db.Column(db.String(128), nullable=False)

    def __init__(self, username, password):
        self.username = username
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        """Verify the user password.

        Verify password against the password hash saved in the database.
        """
        return check_password_hash(self.password_hash, password)

    def json(self):
        """Return JSON serialized username."""
        return {"username": self.username}

    def save_to_db(self):
        """Save user to database."""
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        """Delete user from the database."""
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def find_by_username(cls, username):
        """Find user record by username."""
        return cls.query.filter_by(username=username).first()

    @classmethod
    def find_by_id(cls, _id):
        """Find user record by user id."""
        return cls.query.filter_by(id=_id).first()


class MetricModel(db.Model):
    """Database model for metrics.

    See metric definition in https://sqr-019.lsst.io
    """

    __tablename__ = "metric"

    id = db.Column(db.Integer, primary_key=True)
    # Full qualified name of the metric including the package
    # name, e.g. validate_drp.AM1
    name = db.Column(db.String(64), nullable=False, unique=True)
    # Name of the package that defines this metric, e.g. validate_drp
    package = db.Column(db.String(64))
    # Display name of the metric, e.g. `AM1`
    display_name = db.Column(db.String(64))
    # Short description about the metric.
    description = db.Column(db.Text())
    # Units of the metric. String representation of an astropy unit.
    # An empty string means an unitless quantity.
    unit = db.Column(db.String(16))
    # Tags that can be used to label metrics
    tags = db.Column(JSON())
    # Reference to the original document that defines the metric
    # usually with a handle to the document, a url and a page number.
    reference = db.Column(JSON())

    specification = db.relationship("SpecificationModel", lazy="joined")
    measurement = db.relationship("MeasurementModel", lazy="joined")

    def __init__(
        self,
        name,
        package=None,
        display_name=None,
        description=None,
        unit=None,
        tags=None,
        reference=None,
    ):

        self.name = name
        self.package = package
        self.display_name = display_name
        self.description = description
        self.unit = unit
        self.tags = tags
        self.reference = reference

    def json(self):
        """Return JSON serialized metric object."""
        return {
            "name": self.name,
            "package": self.package,
            "display_name": self.display_name,
            "description": self.description,
            "unit": self.unit,
            "tags": self.tags,
            "reference": self.reference,
        }

    @classmethod
    def find_by_name(cls, name):
        """Find metric by name."""
        return cls.query.filter_by(name=name).first()

    def save_to_db(self):
        """Save metric to database."""
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        """Delete metric from the databse."""
        db.session.delete(self)
        db.session.commit()


class SpecificationModel(db.Model):
    """Database model for specifications.

    See specifications in https://sqr-019.lsst.io
    """

    __tablename__ = "spec"

    id = db.Column(db.Integer, primary_key=True)
    # Full qualified name of the specification, e.g.
    # validate_drp.AM1.minimum_gri
    name = db.Column(db.String(64), nullable=False)
    # Defines the specification, usually the threshold
    # field has an operator, value and unit keys.
    threshold = db.Column(JSON())
    # Tags associated with this specification
    tags = db.Column(JSON())
    # Additional metadata information that can be tested
    # against the job metadata
    metadata_query = db.Column(JSON())
    # Type of specification
    type = db.Column(db.String(64))

    # Id of the metric this specification applies to
    metric_id = db.Column(db.Integer, db.ForeignKey("metric.id"))

    def __init__(
        self,
        name,
        metric_id,
        threshold=None,
        tags=None,
        metadata_query=None,
        type=None,
    ):

        self.name = name
        self.metric_id = metric_id
        self.threshold = threshold
        self.tags = tags
        self.metadata_query = metadata_query
        self.type = type

    def json(self):
        """Return JSON serialized specification."""
        return {
            "name": self.name,
            "threshold": self.threshold,
            "tags": self.tags,
            "metadata_query": self.metadata_query,
        }

    @classmethod
    def find_by_name(cls, name):
        """Find specification by name."""
        return cls.query.filter_by(name=name).first()

    def save_to_db(self):
        """Save specification to the database."""
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        """Delete specification from the datbase."""
        db.session.delete(self)
        db.session.commit()


class EnvModel(db.Model):
    """Database model for execution environments.

    See execution enviroments in https://sqr-009.lsst.io
    """

    __tablename__ = "env"

    id = db.Column(db.Integer, primary_key=True)
    # Name of the environment
    name = db.Column(db.String(64), nullable=False)
    # Environment display name
    display_name = db.Column(db.String(64), nullable=False)

    job = db.relationship("JobModel", lazy="noload")

    def __init__(self, name):
        self.name = name
        self.display_name = name.title()

    def json(self):
        """Return JSON serialized environment."""
        return {"name": self.name, "display_name": self.display_name}

    @classmethod
    def find_by_name(cls, env_name):
        """Find environment by name."""
        return cls.query.filter_by(name=env_name).first()

    def save_to_db(self):
        """Save environment to database."""
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        """Delete environment from the database."""
        db.session.delete(self)
        db.session.commit()


class JobModel(db.Model):
    """Database model for jobs.

    See verification jobs in See https://sqr-019.lsst.io
    """

    __tablename__ = "job"

    id = db.Column(db.Integer, primary_key=True)

    # Id of the environment this job has run
    env_id = db.Column(db.Integer, db.ForeignKey("env.id"))
    # Name of the dataset used in this job, extrated from the
    # environment
    # FIXME: DM-14538 Remove ci_dataset from job model
    ci_dataset = db.Column(db.String(32), default=None)
    # Timestamp when the actual job object was created
    date_created = db.Column(
        db.TIMESTAMP, nullable=False, server_default=now()
    )
    env = db.Column(JSON())
    meta = db.Column(JSON())
    # URI of the object store repository for this job, note that this
    # field is updated only after the job object is created
    s3_uri = db.Column(db.Unicode(255), default=None)

    # Measurements are deleted upon job deletion
    measurements = db.relationship(
        "MeasurementModel", lazy="joined", cascade="all, delete-orphan"
    )

    # Packages are deleted upon job deletion
    packages = db.relationship(
        "PackageModel", lazy="joined", cascade="all, delete-orphan"
    )

    def __init__(self, env_id, env, meta):

        self.env_id = env_id
        # FIXME: DM-14538 Remove ci_dataset from job model
        if "ci_dataset" in env:
            self.ci_dataset = env["ci_dataset"]
        elif "dataset" in env:
            self.ci_dataset = env["dataset"]
        # Preserve date from the env metadata if SQUASH is running
        # in ETL mode
        if SQUASH_ETL_MODE and "date" in env:
            self.date_created = datetime.strptime(
                env["date"], "%Y-%m-%dT%H:%M:%SZ"
            )

        self.env = env
        self.meta = meta

    def json(self):
        """Return JSON serialized job."""
        # Reconstruct the lsst.verify job metadata before returning
        self.meta["packages"] = [pkg.json() for pkg in self.packages]
        self.meta["env"] = self.env

        return {
            "id": self.id,
            "date_created": self.date_created.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ci_dataset": self.ci_dataset,
            "s3_uri": self.s3_uri,
            "measurements": [meas.json() for meas in self.measurements],
            "meta": self.meta,
        }

    @classmethod
    def find_by_id(cls, job_id):
        """Find job by id."""
        return cls.query.filter_by(id=job_id).first()

    @classmethod
    def find_by_env_data(cls, env_id, **kwargs):
        """Find job by environment ID."""
        query = cls.query.filter_by(env_id=env_id)

        for key, value in kwargs.items():
            expression = cls.env[key] == value
            query = query.filter(expression)
        # TODO: not very useful if it returns just the first record.
        # Review where this is used.
        return query.first()

    def save_to_db(self):
        """Save job to database."""
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        """Delete job from database."""
        db.session.delete(self)
        db.session.commit()


class PackageModel(db.Model):
    """A specific version of an eups package.

    Store eups package version information used by jobs.
    """

    __tablename__ = "package"

    id = db.Column(db.Integer, primary_key=True)
    # EUPS package name
    name = db.Column(db.String(64), nullable=False)
    # SHA1 hash of the git commit
    git_sha = db.Column(db.String(64), nullable=False)
    # URL of the git repository for this package
    git_url = db.Column(db.Unicode(255))
    # Resolved git branch that the commit resides on
    git_branch = db.Column(db.String(64))
    # EUPS build version
    eups_version = db.Column(db.String(64))

    job_id = db.Column(db.Integer, db.ForeignKey("job.id"))

    def __init__(
        self,
        job_id,
        name,
        git_sha,
        git_url=None,
        git_branch=None,
        eups_version=None,
    ):

        self.job_id = job_id
        self.name = name
        self.git_sha = git_sha
        self.git_url = git_url
        self.git_branch = git_branch
        self.eups_version = eups_version

    def json(self):
        """Return JSON serialization of a package."""
        return {
            "name": self.name,
            "git_sha": self.git_sha,
            "git_url": self.git_url,
            "git_branch": self.git_branch,
            "eups_version": self.eups_version,
        }

    @classmethod
    def find_by_job_id(cls, job_id):
        """Find packages by job ID."""
        return cls.query.filter_by(job_id=job_id).first()

    def save_to_db(self):
        """Save package to database."""
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        """Delete package from database."""
        db.session.delete(self)
        db.session.commit()


# Association table for measurements and blobs
measurement_blob = db.Table(
    "measurement_blob",
    db.Column(
        "measurement_id",
        db.Integer,
        db.ForeignKey("measurement.id"),
        primary_key=True,
    ),
    db.Column(
        "blob_id", db.Integer, db.ForeignKey("blob.id"), primary_key=True
    ),
)


class MeasurementModel(db.Model):
    """Database model for measurements.

    See measurements in See https://sqr-019.lsst.io
    """

    __tablename__ = "measurement"

    id = db.Column(db.Integer, primary_key=True)
    # Measurement value
    value = db.Column(db.Float)
    # Full qualified name of the metric including the package
    # name, e.g. validate_drp.AM1
    metric_name = db.Column(db.String(64), nullable=False)
    # Measurement unit.  String representation of an astropy unit.
    # An empty string means an unitless quantity.
    unit = db.Column(db.String(16), nullable=False)

    metric_id = db.Column(db.Integer, db.ForeignKey("metric.id"))

    job_id = db.Column(db.Integer, db.ForeignKey("job.id"))

    blobs = db.relationship(
        "BlobModel", secondary=measurement_blob, lazy="dynamic"
    )

    def __init__(
        self,
        job_id,
        metric_id,
        value=None,
        unit="",
        metric="",
        identifier=None,
        blob_refs=None,
    ):

        self.job_id = job_id
        self.metric_id = metric_id
        self.value = value
        self.metric_name = metric
        self.unit = unit

    def json(self):
        """Return JSON serialized measurement."""
        return {
            "value": self.value,
            "unit": self.unit,
            "metric": self.metric_name,
            "blobs": [blob.json() for blob in self.blobs],
        }

    @classmethod
    def find_by_job_id(cls, job_id):
        """Return measurements by job ID."""
        return cls.query.filter_by(job_id=job_id).all()

    def save_to_db(self):
        """Save measurements to database."""
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        """Delete measurements from database."""
        db.session.delete(self)
        db.session.commit()


class BlobModel(db.Model):
    """Database model for data blobs.

    Keep reference for data blobs uploaded to S3. See blobs in
    https://sqr-019.lsst.io/
    """

    __tablename__ = "blob"

    id = db.Column(db.Integer, primary_key=True)
    # Receives a string representation of python UUID object
    # and store as CHAR(32)
    identifier = db.Column(db.String(32), nullable=False)
    # Blob name
    name = db.Column(db.String(64), nullable=False)
    # URI of the object store repository for this job, note that
    # this field is updated only after the blob object is created
    s3_uri = db.Column(db.Unicode(255), default=None)

    def __init__(self, identifier, name):
        self.identifier = identifier
        self.name = name

    def json(self):
        """Return JSON serialized blob."""
        return {
            "identifier": self.identifier,
            "name": self.name,
            "s3_uri": self.s3_uri,
        }

    @classmethod
    def find_by_identifier(cls, identifier):
        """Find blobs by an identifier."""
        return cls.query.filter_by(identifier=identifier).all()

    def save_to_db(self):
        """Save blob to database."""
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        """Delete blob from the database."""
        db.session.delete(self)
        db.session.commit()
