##########
SQuaSH API
##########

RESTful API for managing Science Pipelines metrics. You can learn more about SQuaSH in `SQR-009 <https://sqr-009.lsst.io>`_.


Deployment
==========

The SQuaSH API is deployed as part of the `Science Platform <https://github.com/lsst-sqre/lsp-deploy>`_. The SQuaSH API Helm chart is maintained at the SQuaRE `charts repository <https://github.com/lsst-sqre/charts/tree/master/charts/squash-api>`_.

We assume you are familiar with the SQuaSH MySQL 5.7 instances on Google Cloud SQL. There's an instance for each SQuaSH environment, ``sandbox`` and ``prod``. Such instances exist under the ``sqre`` project on Google Cloud Platform, and the `service account <https://cloud.google.com/sql/docs/mysql/connect-kubernetes-engine>`_ key can be found on SQuaRE 1Password (search for *SQuaSH Cloud SQL service account key*).


Development workflow
====================

1. Clone the repository

.. code-block::

 git clone  https://github.com/lsst-sqre/squash-api.git
 cd squash-api

2. Install the dependencies

.. code-block::

 python3 -m venv venv

Activate the Flask app and set development mode in your environment

.. code-block::

 echo "export FLASK_APP=squash.app:app" >> venv/bin/activate
 echo "export FLASK_ENV=development" >> venv/bin/activate

 source venv/bin/activate
 make update

3. Run the app locally

To run the app locally you need a local instances of MySQL, Redis, InfluxDB and Chronograf, which are set up through docker-compose.

.. code-block::

 docker-compose up -d

The SQuaSH API requires the `AWS credentials present in the environment <https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html>`_. It also assumes that the `s3://squash-dev.data/` S3 bucket was previously created.

Note that by default the app will run using the development config profile, which is equivalent to do:

.. code-block::

 export SQUASH_API_PROFILE="squash.config.Development"
 flask run


The app will run at http://127.0.0.1:5000

On another terminal start the Celery worker:

.. code-block::

 celery -A squash.tasks -E -l DEBUG worker


Running tests
-------------

Pytest uses the docker-compose setup to run functional tests:

.. code-block::

 tox -e pytest

To run unit tests only, you can skip the docker-compose using a ``pytest`` marker:

.. code-block::

 pytest -m "unit"

You can also exercise the API running the `test API notebook <https://github.com/lsst-sqre/squash-rest-api/blob/master/tests/test_api.ipynb>`_.
