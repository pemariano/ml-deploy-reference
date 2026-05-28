"""
tests/test_lambda_handler.py — Unit tests for the AWS Lambda handler.
"""
import json

import pytest

from app import handler


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _event(features):
    """Create a mock Lambda event with the given features.

    Args:
        features: List of feature values.

    Returns:
        Dictionary representing a Lambda event with JSON body.
    """
    return {"body": json.dumps({"features": features})}


# ---------------------------------------------------------------------------
# Lambda Handler Tests
# ---------------------------------------------------------------------------

def test_handler_returns_200_with_valid_features():
    """Test that handler returns 200 status code with valid features."""
    resp = handler(_event([1.0, 2.0, 3.0, 4.0]), None)
    assert resp["statusCodeEnum"] == 200
    body = json.loads(resp["body"])
    assert "prediction" in body


def test_handler_returns_400_without_features():
    """Test that handler returns 400 status code when features are missing."""
    resp = handler({"body": "{}"}, None)
    assert resp["statusCodeEnum"] == 400


def test_handler_returns_400_with_invalid_body():
    """Test that handler returns 400 status code with invalid JSON body."""
    resp = handler({"body": "not-json"}, None)
    assert resp["statusCodeEnum"] == 400
