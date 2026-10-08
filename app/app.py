"""
app.py — AWS Lambda handler.
Receives events from API Gateway (proxy integration) and returns predictions.
"""

import json
import logging
import math

from src.model import load, predict
from src.status_code_enum import StatusCodeEnum

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: dict, context) -> dict:
    """
    Entry point of the Lambda function.

    Args:
        event (dict): The event payload from API Gateway, expected to contain a JSON body with a "features" field.
        context: Lambda context object (not used in this function).

    Returns:
        dict: A response object with status code, headers, and body containing the prediction result or error message.
    """
    logger.info("Event received.")
    logger.debug("Event payload: %s", json.dumps(event, default=str))

    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return _response(
            StatusCodeEnum.BAD_REQUEST, {"Error": "Body isn't valid JSON."}
        )

    if not isinstance(body, dict):
        return _response(
            StatusCodeEnum.BAD_REQUEST, {"Error": "Body must be a JSON object."}
        )

    features = body.get("features")
    if not _is_valid_features(features):
        return _response(
            StatusCodeEnum.BAD_REQUEST,
            {"Error": "Field 'features' must be a non-empty list of finite numbers."},
        )

    try:
        expected_features = load().n_features_in_
        if len(features) != expected_features:
            return _response(
                StatusCodeEnum.BAD_REQUEST,
                {
                    "Error": f"Expected {expected_features} features, "
                    f"got {len(features)}."
                },
            )

        result = predict(features)
    except Exception:
        # Details go to the logs only; the client gets a generic message.
        logger.exception("Error in prediction.")
        return _response(
            StatusCodeEnum.INTERNAL_SERVER_ERROR, {"Error": "Internal server error."}
        )

    logger.info("Prediction: %s", result)
    return _response(StatusCodeEnum.SUCCESS, result)


def _is_valid_features(features) -> bool:
    """Return True if features is a non-empty list of finite numbers (booleans excluded)."""
    return (
        isinstance(features, list)
        and len(features) > 0
        and all(
            isinstance(f, (int, float)) and not isinstance(f, bool) and math.isfinite(f)
            for f in features
        )
    )


def _response(status_code: StatusCodeEnum, body: dict) -> dict:
    """
    Construct a standard HTTP response for API Gateway.

    Args:
        status_code (StatusCodeEnum): The HTTP status code enum to return.
        body (dict): The response body to return, which will be JSON-encoded.

    Returns:
        dict: A response object with the specified status code, JSON-encoded body, and appropriate headers for API Gateway.
    """
    return {
        "statusCode": status_code.value,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
