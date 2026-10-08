"""
tests/test_unit_model.py — Unit tests for the model module.

Run with:
    uv run pytest tests/test_unit_model.py -v
"""

import json
from unittest.mock import patch

import joblib
import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

from src import model as model_module


@pytest.fixture
def model_path(tmp_path, monkeypatch):
    """Redirect MODEL_PATH to a temporary file so tests never touch the real model."""
    path = tmp_path / "model.joblib"
    monkeypatch.setattr(model_module, "MODEL_PATH", str(path))
    model_module.load.cache_clear()
    yield path
    model_module.load.cache_clear()


@pytest.fixture
def trained_model(model_path):
    np.random.seed(0)
    return model_module.train()


class TestTrain:
    def test_given_writable_model_path_when_training_then_returns_fitted_logistic_regression(
        self, model_path
    ):
        model = model_module.train()

        assert isinstance(model, LogisticRegression)
        assert model.coef_.shape == (1, 4)

    def test_given_writable_model_path_when_training_then_persists_model_to_model_path(
        self, model_path
    ):
        model_module.train()

        assert model_path.exists()
        assert isinstance(joblib.load(model_path), LogisticRegression)

    def test_given_trained_model_when_predicting_known_samples_then_learns_the_sum_rule(
        self, trained_model
    ):
        """The model must learn that class is 1 when X[0] + X[1] > 0."""
        assert trained_model.predict([[2.0, 2.0, 0.0, 0.0]])[0] == 1
        assert trained_model.predict([[-2.0, -2.0, 0.0, 0.0]])[0] == 0


class TestLoad:
    def test_given_saved_model_when_loading_then_returns_equivalent_model(
        self, trained_model
    ):
        loaded = model_module.load()

        assert isinstance(loaded, LogisticRegression)
        np.testing.assert_array_equal(loaded.coef_, trained_model.coef_)

    def test_given_no_saved_model_when_loading_then_raises_file_not_found(
        self, model_path
    ):
        with pytest.raises(FileNotFoundError):
            model_module.load()

    def test_given_saved_model_when_loading_twice_then_reads_file_only_once(
        self, trained_model
    ):
        with patch.object(
            model_module.joblib, "load", wraps=model_module.joblib.load
        ) as spy_load:
            first = model_module.load()
            second = model_module.load()

        assert first is second
        spy_load.assert_called_once()

    def test_given_cached_model_when_training_again_then_load_returns_the_new_model(
        self, trained_model
    ):
        cached = model_module.load()

        retrained = model_module.train()
        reloaded = model_module.load()

        assert reloaded is not cached
        np.testing.assert_array_equal(reloaded.coef_, retrained.coef_)


class TestPredict:
    def test_given_trained_model_when_predicting_then_returns_prediction_and_probability(
        self, trained_model
    ):
        result = model_module.predict([1.0, 2.0, 3.0, 4.0])

        assert set(result) == {"prediction", "probability"}
        assert result["prediction"] in (0, 1)
        assert 0.5 <= result["probability"] <= 1.0
        assert result["probability"] == round(result["probability"], 4)

    def test_given_trained_model_when_predicting_then_result_is_json_serializable(
        self, trained_model
    ):
        result = model_module.predict([1.0, 2.0, 3.0, 4.0])

        assert isinstance(result["prediction"], int)
        assert isinstance(result["probability"], float)
        json.dumps(result)  # must not raise

    @pytest.mark.parametrize(
        "features, expected_class",
        [
            ([2.0, 2.0, 0.0, 0.0], 1),
            ([-2.0, -2.0, 0.0, 0.0], 0),
        ],
    )
    def test_given_clearly_separable_features_when_predicting_then_returns_expected_class(
        self, trained_model, features, expected_class
    ):
        result = model_module.predict(features)

        assert result["prediction"] == expected_class

    def test_given_no_saved_model_when_predicting_then_raises_file_not_found(
        self, model_path
    ):
        with pytest.raises(FileNotFoundError):
            model_module.predict([1.0, 2.0, 3.0, 4.0])

    def test_given_wrong_number_of_features_when_predicting_then_raises_value_error(
        self, trained_model
    ):
        with pytest.raises(ValueError):
            model_module.predict([1.0, 2.0])
