"""squash-api pytest fixtures."""

import os

import pymysql
import pytest
import redis

from squash.config import Development
from squash.models import UserModel

# timeout in seconds to get the docker services running
DOCKER_SERVICE_TIMEOUT = 120


def is_mysql_responsive():
    """Try to connect and run a query to check if mysql is responsive."""
    try:
        connection = pymysql.connect(
            host="localhost",
            user=Development.SQUASH_DB_USER,
            password=Development.SQUASH_DB_PASSWORD,
            db="squash_local",
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return False
    return True


def is_redis_responsive():
    """Try to connect to redis to check if the service is responsive."""
    try:
        redis.StrictRedis(host="localhost", port=6379, db=0)
    except Exception:
        return False
    return True


@pytest.fixture(scope="session")
def ensure_mysql_service(docker_services):
    """Ensure that mysql service is up and responsive."""
    docker_services.wait_until_responsive(
        timeout=DOCKER_SERVICE_TIMEOUT,
        pause=5,
        check=lambda: is_mysql_responsive(),
    )
    return True


@pytest.fixture(scope="session")
def ensure_redis_service(docker_services):
    """Ensure that redis service is up and responsive."""
    docker_services.wait_until_responsive(
        timeout=DOCKER_SERVICE_TIMEOUT,
        pause=5,
        check=lambda: is_redis_responsive(),
    )
    return True


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    """Return location and name of the docker-compose configuration file."""
    return os.path.join(str(pytestconfig.rootdir), "", "docker-compose.yaml")


@pytest.fixture(scope="module")
def new_user():
    """Create a test user."""
    user = UserModel("mole", "desert")
    return user


@pytest.fixture(scope="module")
def test_client(ensure_redis_service, ensure_mysql_service):
    """Create an app for testing."""
    from squash.app import create_app

    app = create_app("squash.config.Testing")
    # Flask provides a way to test your application by exposing the Werkzeug
    # test Client and handling the context locals for you.
    testing_client = app.test_client()
    # Establish an application context before running the tests.
    ctx = app.app_context()
    ctx.push()
    yield testing_client  # this is where the testing happens!
    ctx.pop()
