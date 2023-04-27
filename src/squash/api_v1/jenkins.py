from flask_restful import Resource, reqparse

from ..models import EnvModel, JobModel


class Jenkins(Resource):
    parser = reqparse.RequestParser()

    def get(self, ci_id):
        """
        Retrieve a verification job from the jenkins environment.
        ---
        tags:
          - Jobs
        parameters:
        - name: ci_id
          in: path
          type: integer
          description: ID of the jenkins job.
          required: true
        responses:
          200:
            description: Jenkins job successfully retrieved.
          404:
            description: Jenkins job not found.
        """
        env = EnvModel.find_by_name(env_name="jenkins")

        if env:
            job = JobModel.find_by_env_data(env_id=env.id, ci_id=ci_id)
        else:
            message = "Environment `jenkins` not found."
            return {"message": message}, 400

        if job:
            return job.json()

        return {"message": "Jenkins job not found"}, 404
