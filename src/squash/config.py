"""Implement SQuaSH app configuration.

See http://flask.pocoo.org/docs/0.12/config/#configuration-best-practices
"""

__all__ = ["Config"]

import os
from datetime import timedelta


class Config(object):
    """Base class configuration."""

    APP_DIR = os.path.abspath(os.path.dirname(__file__))

    # DB admin user credentials
    SQUASH_DB_USER = os.environ.get("SQUASH_DB_USER", "root")
    SQUASH_DB_PASSWORD = os.environ.get("SQUASH_DB_PASSWORD", "squash")

    # Default database uri connection string
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "SQLALCHEMY_DATABASE_URI",
        "mysql+pymysql://{}:{}@127.0.0.1/squash_local".format(
            SQUASH_DB_USER, SQUASH_DB_PASSWORD
        ),
    )

    # Default API user credentials
    DEFAULT_USER = os.environ.get("SQUASH_DEFAULT_USER", "mole")
    DEFAULT_PASSWORD = os.environ.get("SQUASH_DEFAULT_PASSWORD", "desert")

    # InfluxDB instance
    INFLUXDB_API_URL = os.environ.get(
        "INFLUXDB_API_URL", "http://localhost:8086"
    )
    INFLUXDB_DATABASE = os.environ.get("INFLUXDB_DATABASE", "squash-local")

    # InfluxDB credentials
    INFLUXDB_USERNAME = os.environ.get("INFLUXDB_USERNAME")
    INFLUXDB_PASSWORD = os.environ.get("INFLUXDB_PASSWORD")

    # SQuaSH API URL
    SQUASH_API_URL = os.environ.get("SQUASH_API_URL", "http://127.0.0.1:5000")

    # Turn off the Flask-SQLAlchemy event system
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flass APP debug mode
    DEBUG = True

    # Secret key for signing cookies
    SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(32))


class Production(Config):
    """Production configuration."""

    # Because the cloudsql-proxy containter runs in the same pod as the app,
    # it appears to the application as localhost
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "SQLALCHEMY_DATABASE_URI",
        "mysql+pymysql://{}:{}@127.0.0.1/squash".format(
            Config.SQUASH_DB_USER, Config.SQUASH_DB_PASSWORD
        ),
    )

    DEBUG = False
    SQLALCHEMY_ECHO = False
    PREFERRED_URL_SCHEME = "https"

    # Required for the upload of large files ~1G
    JWT_EXPIRATION_DELTA = timedelta(900)


class Development(Config):
    """Development configuration."""

    SQLALCHEMY_ECHO = True


class Testing(Config):
    """Testing configuration."""

    # Bcrypt algorithm hashing rounds (reduced for testing purposes only!)
    BCRYPT_LOG_ROUNDS = 4

    # Enable the TESTING flag to disable the error catching during request
    # handling so that you get better error reports when performing test
    # requests against the application.
    TESTING = True

    SQLALCHEMY_ECHO = True
