"""Test squash-api models."""

import pytest
from sqlalchemy.sql import null

from squash.models import MeasurementModel


@pytest.fixture(scope="module")
def null_measurement():
    """Create a measurement with a null value."""
    measurement = MeasurementModel(job_id=1, metric_id=1)
    return measurement


@pytest.mark.unit
def test_new_user(new_user):
    """Test user cretion with hashed password."""
    assert new_user.username == "mole"
    assert new_user.verify_password("desert") is True


@pytest.mark.unit
def test_null_measurement(null_measurement):
    """Test whether default value for a measurement is null."""
    assert null_measurement.value is null()
