from flask import jsonify
from flask_restful import Resource

from squash.tasks.influxdb import job_to_influxdb


class Status(Resource):
    def get(self, task_id):
        """
        Retrieve status of an upload task.
        ---
        tags:
          - Misc
        parameters:
        - name: task_id
          in: path
          type: string
          description: Upload task ID as returned by /job
          required: true
        responses:
          200:
            description: >
                InfluxDB task status successfully retrieved.
                PENDING: the task did not start yet.
                STARTED: the task has started.
                FAILURE: something went wrong.
                On sucess report a message and status code for the request.

        """
        result = job_to_influxdb.AsyncResult(task_id)

        if result.state == "PENDING":
            response = {
                "status": result.state,
            }

        if result.state == "STARTED":
            response = {
                "status": result.state,
            }

        elif result.state == "FAILURE":
            response = {
                "status": result.state,
            }
        else:
            response = {
                "message": result.info["message"],
                "status_code": result.info["status_code"],
            }

        return jsonify(response)
