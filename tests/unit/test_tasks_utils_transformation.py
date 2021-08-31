"""Test squash-api tasks/utils/transformation module."""

import pytest

from squash.tasks.utils.transformation import Transformer


@pytest.fixture(scope="module")
def data():
    """Create a test data."""
    data = {
        "measurements": [
            {"metric": "package.metric", "value": 0.0},
            {"metric": "package.pmetric", "value": 0.0},
            {"metric": "package.p.metric", "value": 0.0},
        ]
    }
    return data


@pytest.mark.unit
def test_get_meas_by_package(data):
    """Test get_meas_by_package method."""
    t = Transformer("", data)

    result = t.get_meas_by_package()

    assert "package" in result
    assert "metric=0.0" in result["package"]
    assert "pmetric=0.0" in result["package"]
    assert "p.metric=0.0" in result["package"]
