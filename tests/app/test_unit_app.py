"""
tests/test_app.py — Unit tests for the Lambda handler.

Run with:
    uv run pytest tests/test_app.py -v
"""

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import app as app_module
from app import handler

N_FEATURES = 4


@pytest.fixture(autouse=True)
def mock_load():
    """Replace the model loader with a stub that exposes n_features_in_."""
    with patch.object(
        app_module, "load", return_value=SimpleNamespace(n_features_in_=N_FEATURES)
    ) as mock:
        yield mock


def make_event(body):
    """Build an API Gateway proxy event with a JSON-encoded body."""
    return {"body": json.dumps(body)}


class TestHandlerSuccess:
    def test_given_valid_features_when_handling_event_then_returns_200_with_prediction(
        self,
    ):
        fake_result = {"prediction": 1, "probability": 0.87}

        with patch.object(
            app_module, "predict", return_value=fake_result
        ) as mock_predict:
            response = handler(make_event({"features": [1, 2.5, 3, 4]}), None)

        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == fake_result
        mock_predict.assert_called_once_with([1, 2.5, 3, 4])

    def test_given_valid_features_when_handling_event_then_response_follows_api_gateway_proxy_format(
        self,
    ):
        with patch.object(app_module, "predict", return_value={"prediction": 0}):
            response = handler(make_event({"features": [1, 2, 3, 4]}), None)

        assert set(response) == {"statusCode", "headers", "body"}
        assert response["headers"] == {"Content-Type": "application/json"}
        assert isinstance(response["body"], str)


class TestHandlerBadRequest:
    @pytest.mark.parametrize("event", [{"body": "not json"}, {"body": "{invalid"}])
    def test_given_invalid_json_body_when_handling_event_then_returns_400_and_skips_model(
        self, event
    ):
        with patch.object(app_module, "predict") as mock_predict:
            response = handler(event, None)

        assert response["statusCode"] == 400
        assert "valid JSON" in json.loads(response["body"])["Error"]
        mock_predict.assert_not_called()

    @pytest.mark.parametrize("body", [[1, 2, 3], "text", 42])
    def test_given_json_body_that_is_not_an_object_when_handling_event_then_returns_400(
        self, body
    ):
        with patch.object(app_module, "predict") as mock_predict:
            response = handler(make_event(body), None)

        assert response["statusCode"] == 400
        assert "JSON object" in json.loads(response["body"])["Error"]
        mock_predict.assert_not_called()

    @pytest.mark.parametrize(
        "event",
        [
            {},  # no body key at all
            {"body": None},
            make_event({}),
            make_event({"features": None}),
            make_event({"features": "1,2,3,4"}),
            make_event({"features": []}),
            make_event({"features": ["a", "b"]}),
            make_event({"features": [1, None, 3]}),
            make_event({"features": [1, True, 3]}),
            make_event({"features": {"a": 1}}),
            make_event({"features": [1, float("nan"), 3, 4]}),
            make_event({"features": [1, float("inf"), 3, 4]}),
        ],
    )
    def test_given_missing_or_invalid_features_when_handling_event_then_returns_400_and_skips_model(
        self, event
    ):
        with patch.object(app_module, "predict") as mock_predict:
            response = handler(event, None)

        assert response["statusCode"] == 400
        assert "features" in json.loads(response["body"])["Error"]
        mock_predict.assert_not_called()

    @pytest.mark.parametrize("features", [[1, 2], [1, 2, 3, 4, 5]])
    def test_given_wrong_number_of_features_when_handling_event_then_returns_400_with_expected_count_and_skips_model(
        self, features
    ):
        with patch.object(app_module, "predict") as mock_predict:
            response = handler(make_event({"features": features}), None)

        assert response["statusCode"] == 400
        assert json.loads(response["body"]) == {
            "Error": f"Expected {N_FEATURES} features, got {len(features)}."
        }
        mock_predict.assert_not_called()


class TestHandlerServerError:
    def test_given_unexpected_model_failure_when_handling_event_then_returns_500_without_leaking_details(
        self,
    ):
        with patch.object(
            app_module,
            "predict",
            side_effect=RuntimeError("secret internal path /opt/model.joblib"),
        ):
            response = handler(make_event({"features": [1, 2, 3, 4]}), None)

        assert response["statusCode"] == 500
        assert json.loads(response["body"]) == {"Error": "Internal server error."}
        assert "secret" not in response["body"]

    def test_given_model_raises_value_error_when_handling_event_then_returns_500_without_leaking_details(
        self,
    ):
        with patch.object(
            app_module,
            "predict",
            side_effect=ValueError("X has 4 features, but LogisticRegression ..."),
        ):
            response = handler(make_event({"features": [1, 2, 3, 4]}), None)

        assert response["statusCode"] == 500
        assert json.loads(response["body"]) == {"Error": "Internal server error."}

    def test_given_model_file_is_missing_when_handling_event_then_returns_500_and_skips_predict(
        self, mock_load
    ):
        mock_load.side_effect = FileNotFoundError("model not found")

        with patch.object(app_module, "predict") as mock_predict:
            response = handler(make_event({"features": [1, 2, 3, 4]}), None)

        assert response["statusCode"] == 500
        assert json.loads(response["body"]) == {"Error": "Internal server error."}
        mock_predict.assert_not_called()
