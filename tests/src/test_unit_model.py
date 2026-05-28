"""
tests/test_unit_model.py — Unit tests for the model.
"""
import numpy as np
import pytest

from model import train, predict


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def trained_model(tmp_path, monkeypatch):
    """Train a model in a temporary directory before each test.

    Args:
        tmp_path: Pytest temporary directory path.
        monkeypatch: Pytest monkeypatch fixture to modify environment variables.
    """
    monkeypatch.setenv("MODEL_PATH", str(tmp_path / "model.joblib"))
    X = np.random.randn(100, 4)
    y = (X[:, 0] > 0).astype(int)
    train(X, y)


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

def test_prediction_returns_expected_fields():
    """Test that predict returns the expected dictionary keys."""
    result = predict([1.0, 2.0, 3.0, 4.0])
    assert "prediction" in result
    assert "probability" in result


def test_probability_within_valid_range():
    """Test that probability value is between 0.0 and 1.0."""
    result = predict([1.0, 2.0, 3.0, 4.0])
    assert 0.0 <= result["probability"] <= 1.0


def test_prediction_is_integer():
    """Test that prediction value is an integer."""
    result = predict([1.0, 2.0, 3.0, 4.0])
    assert isinstance(result["prediction"], int)
