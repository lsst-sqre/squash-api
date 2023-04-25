"""Test squash-api routes."""


def test_root(test_client):
    """Test root route."""
    response = test_client.get("/")
    assert response.status_code == 200


def test_jenkins(test_client):
    """Test jenkins route."""
    response = test_client.get("jenkins")
    assert response.status_code == 404


def test_job(test_client):
    """Test job route."""
    response = test_client.get("job")
    assert response.status_code == 405


def test_jobs(test_client):
    """Test jobs route."""
    response = test_client.get("jobs")
    assert response.status_code == 200


def test_metric(test_client):
    """Test metric route."""
    response = test_client.get("metric")
    assert response.status_code == 404


def test_metrics(test_client):
    """Test metrics route."""
    response = test_client.get("metrics")
    assert response.status_code == 200


def test_spec(test_client):
    """Test spec route."""
    response = test_client.get("spec")
    assert response.status_code == 404


def test_specs(test_client):
    """Test specs route."""
    response = test_client.get("specs")
    assert response.status_code == 200


def test_measurement(test_client):
    """Test measurement route."""
    response = test_client.get("measurement")
    assert response.status_code == 404


def test_measurements(test_client):
    """Test measurements route."""
    response = test_client.get("measurements")
    assert response.status_code == 200


def test_register(test_client):
    """Test register route."""
    response = test_client.get("register")
    assert response.status_code == 405


def test_auth(test_client):
    """Test auth route."""
    response = test_client.get("auth")
    assert response.status_code == 405


def test_user(test_client):
    """Test user route."""
    response = test_client.get("user")
    assert response.status_code == 404


def test_users(test_client):
    """Test users route."""
    response = test_client.get("users")
    assert response.status_code == 200


def test_stats(test_client):
    """Test stats route."""
    response = test_client.get("stats")
    assert response.status_code == 200


def test_status(test_client):
    """Test status route."""
    response = test_client.get("status")
    assert response.status_code == 404


def test_version(test_client):
    """Test version route."""
    response = test_client.get("version")
    assert response.status_code == 200


def test_code_changes(test_client):
    """Test code_changes route."""
    response = test_client.get("code_changes")
    assert response.status_code == 404


def test_datasets(test_client):
    """Test datasets route."""
    response = test_client.get("datasets")
    assert response.status_code == 200


def test_monitor(test_client):
    """Test monitor route."""
    response = test_client.get("monitor")
    assert response.status_code == 200


def test_packages(test_client):
    """Test packages route."""
    response = test_client.get("packages")
    assert response.status_code == 200
