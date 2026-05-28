"""
app.py — AWS Lambda handler.
Receives events from API Gateway (proxy integration) and return predictions.
"""
import json
import logging

from src.model import predict
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
    logger.info("Event received: %s", json.dumps(event))

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(StatusCodeEnum.BAD_REQUEST, {"Error": "Body isn't valid JSON."})

    features = body.get("features")
    if not features or not isinstance(features, list):
        return _response(StatusCodeEnum.BAD_REQUEST, {"Error": "Field 'features' is required and must be a list."})

    try:
        result = predict(features)
        logger.info("Prediction: %s", result)
        return _response(StatusCodeEnum.SUCCESS, result)
    except Exception as exc:
        logger.exception("Error in prediction.")
        return _response(StatusCodeEnum.INTERNAL_SERVER_ERROR, {"Error": str(exc)})


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
        "statusCodeEnum": status_code.value,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
