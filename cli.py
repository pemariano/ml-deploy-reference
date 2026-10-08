"""
tests/test_cli.py — Unit tests for the CLI.

Run with:
    uv run pytest tests/test_cli.py -v
"""

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

import cli as cli_module
from cli import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestTrainCommand:
    def test_given_mocked_model_when_running_train_then_calls_model_train_once_and_exits_successfully(
        self, runner
    ):
        with patch.object(cli_module, "model_train") as mock_train:
            result = runner.invoke(cli, ["train"])

        assert result.exit_code == 0
        mock_train.assert_called_once_with()

    def test_given_mocked_model_when_running_train_then_prints_progress_and_success_messages(
        self, runner
    ):
        with patch.object(cli_module, "model_train"):
            result = runner.invoke(cli, ["train"])

        assert "Training model..." in result.output
        assert "Model trained and saved successfully." in result.output

    def test_given_model_training_fails_when_running_train_then_propagates_exception_without_success_message(
        self, runner
    ):
        with patch.object(
            cli_module, "model_train", side_effect=RuntimeError("training failed")
        ):
            result = runner.invoke(cli, ["train"])

        assert result.exit_code != 0
        assert isinstance(result.exception, RuntimeError)
        assert "Model trained and saved successfully." not in result.output


class TestPredictCommand:
    def test_given_valid_features_when_running_predict_then_calls_model_and_outputs_json_result(
        self, runner
    ):
        fake_result = {"prediction": 1, "probability": 0.87}

        with patch.object(
            cli_module, "model_predict", return_value=fake_result
        ) as mock_predict:
            result = runner.invoke(cli, ["predict", "--features", "1.0,2.0,3.0,4.0"])

        assert result.exit_code == 0
        mock_predict.assert_called_once_with([1.0, 2.0, 3.0, 4.0])
        assert json.loads(result.output) == fake_result

    @pytest.mark.parametrize(
        "raw_features, expected",
        [
            ("1,2,3,4", [1.0, 2.0, 3.0, 4.0]),
            (" 1.0 , 2.5 ,  3 , -4.2 ", [1.0, 2.5, 3.0, -4.2]),
            ("1e3,2e-2,3,4", [1000.0, 0.02, 3.0, 4.0]),
        ],
    )
    def test_given_different_numeric_formats_when_running_predict_then_parses_values_as_floats(
        self, runner, raw_features, expected
    ):
        with patch.object(cli_module, "model_predict", return_value={}) as mock_predict:
            result = runner.invoke(cli, ["predict", "--features", raw_features])

        assert result.exit_code == 0
        mock_predict.assert_called_once_with(expected)

    @pytest.mark.parametrize(
        "raw_features",
        ["a,b,c,d", "1.0,abc,3.0,4.0", "1.0,,3.0,4.0", ""],
    )
    def test_given_non_numeric_features_when_running_predict_then_fails_with_bad_parameter_and_skips_model(
        self, runner, raw_features
    ):
        with patch.object(cli_module, "model_predict") as mock_predict:
            result = runner.invoke(cli, ["predict", "--features", raw_features])

        assert result.exit_code == 2
        assert "All features must be numeric values" in result.output
        mock_predict.assert_not_called()

    def test_given_missing_features_option_when_running_predict_then_fails_with_missing_option_error(
        self, runner
    ):
        with patch.object(cli_module, "model_predict") as mock_predict:
            result = runner.invoke(cli, ["predict"])

        assert result.exit_code == 2
        assert "--features" in result.output
        mock_predict.assert_not_called()

    def test_given_model_file_is_missing_when_running_predict_then_propagates_exception(
        self, runner
    ):
        with patch.object(
            cli_module,
            "model_predict",
            side_effect=FileNotFoundError("model not found"),
        ):
            result = runner.invoke(cli, ["predict", "--features", "1,2,3,4"])

        assert result.exit_code != 0
        assert isinstance(result.exception, FileNotFoundError)
