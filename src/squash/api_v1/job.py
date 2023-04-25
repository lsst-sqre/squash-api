import json
import warnings

from flask import current_app as app
from flask import url_for
from flask_jwt import jwt_required
from flask_restful import Resource, reqparse

from squash.decorators import time_this
from squash.error import ApiError
from squash.tasks.influxdb import job_to_influxdb

from ..models import (
    BlobModel,
    EnvModel,
    JobModel,
    MeasurementModel,
    MetricModel,
    PackageModel,
)


class JobWithArg(Resource):
    def get(self, job_id):
        """
        Retrieve a verification job.
        ---
        tags:
          - Jobs
        parameters:
        - name: job_id
          in: path
          type: integer
          description: ID of the job.
          required: true
        responses:
          200:
            description: Job successfully retrieved.
          404:
            description: Job not found.
        """
        job = JobModel.find_by_id(job_id)

        if job:
            return job.json()

        return {"message": "Job not found"}, 404

    @jwt_required()
    def delete(self, job_id):
        """
        Delete a verification job and associated measurements,\
        data blobs and metadata.
        ---
        tags:
          - Jobs
        parameters:
        - name: job_id
          in: path
          type: integer
          description: ID of the job.
          required: true
        responses:
          200:
            description: Job deleted.
          404:
            description: Job not found.
          401:
            description: >
                Authorization Required. Request does not contain a
                valid access token.
        """

        job = JobModel.find_by_id(job_id)

        if not job:
            message = "Job `{}` does not exist.".format(job_id)
            return {"message": message}, 404

        job.delete_from_db()
        return {"message": "Job deleted."}


class Job(Resource):
    parser = reqparse.RequestParser()
    # accept multiple values
    # http://flask-restful.readthedocs.io/en/0.3.5/reqparse.html
    parser.add_argument(
        "measurements",
        type=dict,
        default=[],
        action="append",
    )
    parser.add_argument(
        "meta",
        default={},
        type=dict,
    )
    parser.add_argument(
        "blobs",
        type=dict,
        default=[],
        action="append",
    )

    @jwt_required()
    def post(self):
        """
        Create a verification job.
        This is the entry point for `dispatch_verify.py`. \
        See http://sqr-019.lsst.io for the body content.
        ---
        tags:
          - Jobs
        parameters:
        - in: body
          name: "Request body:"
          schema:
            type: object
            required:
              - measurements
              - meta
            properties:
              measurements:
                type: array
              blobs:
                type: array
              meta:
                type: object
        responses:
          202:
            description: Request for creating Job received.
          400:
            description: Missing or invalid data in the request body.
          401:
            description: >
                Authorization Required. Request does not contain a
                valid access token.
          500:
            description: An error occurred creating this job.
        """
        self.data = Job.parser.parse_args()

        try:
            env_id = self.check_or_create_env()
        except ApiError as err:
            app.logger.error(err.message)
            return {"message": err.message}, err.status_code

        try:
            job_id = self.create_job(env_id)
        except ApiError as err:
            app.logger.error(err.message)
            return {"message": err.message}, err.status_code

        try:
            self.insert_packages(job_id)
        except ApiError as err:
            app.logger.error(err.message)
            return {"message": err.message}, err.status_code

        try:
            self.insert_measurements(job_id)
        except ApiError as err:
            app.logger.error(err.message)
            return {"message": err.message}, err.status_code

        # async celery task
        try:
            task = job_to_influxdb.delay(job_id)
        except ApiError:
            app.logger.error(message)
            return {"message": message}, err.status_code

        # see DM-16391 for improving task status report
        message = "Request for creating Job `{}` received".format(job_id)
        return {
            "message": message,
            "status": url_for("status", task_id=task.id, _external=True),
        }, 202

    @time_this
    def check_or_create_env(self):
        """Check if env (e.g. Jenkins) exists in the db,
        if not create it.
        """
        if "env" in self.data["meta"]:
            env = self.data["meta"]["env"]
            if "env_name" in env:
                e = EnvModel.find_by_name(env["env_name"])
                if not e:
                    e = EnvModel(env["env_name"])
                    try:
                        e.save_to_db()
                    except Exception:
                        raise ApiError(
                            "An error ocurred creating " "the env object.", 500
                        )
            else:
                raise ApiError("Missing `env_name` in env metadata.", 400)
        else:
            # allows for unknown environment
            e = EnvModel.find_by_name("unknown")
            if not e:
                e = EnvModel("unknown")
                try:
                    e.save_to_db()
                except Exception:
                    raise ApiError(
                        "An error ocurred creating " "the env object.", 500
                    )

        return e.id

    @time_this
    def create_job(self, env_id):
        """Creates the job object

        Parameters
        ----------
        env_id : `int`
            id of the environment associated with the job.

        Return
        ------
        job_id : `int`
            id of the job created
        """

        # job metadata contains arbitrary metadata plus
        # env metadata and packages
        meta = self.data["meta"].copy()

        # we extract the env metadata
        if "env" in meta:
            env = meta.pop("env")
        else:
            env = {}

        # and remove the packages, they will be inserted later.
        if "packages" in meta:
            del meta["packages"]
        else:
            raise ApiError("Missing packages metadata.", 400)

        # what remains in meta is the arbitrary metadata we want to save
        j = JobModel(env_id, env, meta)

        try:
            j.save_to_db()
        except Exception:
            raise ApiError(
                "An error occurred creating " "the job object.", 500
            )

        return j.id

    @time_this
    def insert_packages(self, job_id):
        """Insert packages associated with the job.

        Parameters
        ----------
        job_id : `int`
            id of the job object previously created.
        """
        meta = self.data["meta"]
        if "packages" in meta:
            packages = meta["packages"]
        else:
            raise ApiError("Missing packages metadata.", 400)

        for package in packages:
            p = PackageModel(job_id, **packages[package])
            try:
                p.save_to_db()
            except Exception:
                raise ApiError("An error occurred inserting packages", 500)

    @time_this
    def insert_measurements(self, job_id):
        """Insert measurements associated with the job.

        Parameters
        ----------
        job_id : `int`
            id of the job object previously created.
        """
        measurements = self.data["measurements"]

        for measurement in measurements:
            if measurement and "metric" in measurement:
                metric_name = measurement["metric"]
            else:
                raise ApiError(
                    "You must provide a list of measurements "
                    "and the associated metric name.",
                    400,
                )

            metric = MetricModel.find_by_name(metric_name)

            if metric:
                m = MeasurementModel(job_id, metric.id, **measurement)
                # Insert data blobs associated with this measurement
                blobs = self.data["blobs"]
                m.blobs = []

                for blob in blobs:
                    if blob and "identifier" in blob and "name" in blob:
                        identifier = blob["identifier"]
                        if identifier in measurement["blob_refs"]:
                            name = blob["name"]
                            b = BlobModel(identifier, name)
                            m.blobs.append(b)

                try:
                    m.save_to_db()
                except Exception:
                    raise ApiError(
                        "An error occurred inserting " "measurements", 500
                    )

            else:
                warnings.warn(
                    "Metric `{}` not found, it looks like "
                    "the metrics definition is out of "
                    "date.".format(metric_name)
                )


class JobList(Resource):
    def get(self):
        """
        Retrieve the complete list of job ids.
        ---
        tags:
          - Jobs
        responses:
          200:
            description: List of job ids successfully retrieved.
        """

        queryset = JobModel.query

        generator = queryset.values(JobModel.id)

        return {"ids": [value[0] for value in generator]}
