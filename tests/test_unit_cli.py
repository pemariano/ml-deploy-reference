"""
tests/test_unit_cli.py — Unit tests for the CLI.

Run with:
    uv run pytest tests/test_unit_cli.py -v
"""

import json
from unittest.mock import patch

import numpy as np
import pytest
from click.testing import CliRunner

import cli as cli_module
from cli import cli


@pytest.fixture
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# Main group
# ---------------------------------------------------------------------------
class TestCliGroup:
    def test_given_help_flag_when_invoking_cli_then_lists_available_commands(
        self, runner
    ):
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "train" in result.output
        assert "predict" in result.output

    def test_given_no_arguments_when_invoking_cli_then_shows_usage(self, runner):
        result = runner.invoke(cli, [])

        # Depending on the click version, a group without a subcommand exits with 0 or 2
        assert result.exit_code in (0, 2)
        assert "Usage" in result.output

    def test_given_unknown_command_when_invoking_cli_then_fails_with_no_such_command(
        self, runner
    ):
        result = runner.invoke(cli, ["unknown"])

        assert result.exit_code == 2
        assert "No such command" in result.output


# ---------------------------------------------------------------------------
# Command: train
# ---------------------------------------------------------------------------
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
        assert "training failed" in str(result.exception)
        assert "Model trained and saved successfully." not in result.output


# ---------------------------------------------------------------------------
# Command: predict
# ---------------------------------------------------------------------------
class TestPredictCommand:
    def test_given_valid_features_when_running_predict_then_calls_model_with_float_list(
        self, runner
    ):
        fake_result = {"prediction": 1, "probability": 0.87}

        with patch.object(
            cli_module, "model_predict", return_value=fake_result
        ) as mock_predict:
            result = runner.invoke(cli, ["predict", "--features", "1.0,2.0,3.0,4.0"])

        assert result.exit_code == 0
        mock_predict.assert_called_once_with([1.0, 2.0, 3.0, 4.0])

    def test_given_model_result_when_running_predict_then_outputs_indented_json(
        self, runner
    ):
        fake_result = {"prediction": 1, "probability": 0.87}

        with patch.object(cli_module, "model_predict", return_value=fake_result):
            result = runner.invoke(cli, ["predict", "--features", "1,2,3,4"])

        assert json.loads(result.output) == fake_result
        # indent=2 -> multiline output
        assert result.output.strip() == json.dumps(fake_result, indent=2)

    def test_given_features_with_surrounding_spaces_when_running_predict_then_strips_whitespace(
        self, runner
    ):
        with patch.object(
            cli_module, "model_predict", return_value={"prediction": 0}
        ) as mock_predict:
            result = runner.invoke(
                cli, ["predict", "--features", " 1.0 , 2.5 ,  3 , -4.2 "]
            )

        assert result.exit_code == 0
        mock_predict.assert_called_once_with([1.0, 2.5, 3.0, -4.2])

    @pytest.mark.parametrize(
        "raw_features, expected",
        [
            ("1,2,3,4", [1.0, 2.0, 3.0, 4.0]),
            ("-1.5,0,0.0,2.7", [-1.5, 0.0, 0.0, 2.7]),
            ("1e3,2e-2,3,4", [1000.0, 0.02, 3.0, 4.0]),
            ("5", [5.0]),
            ("1.0,2.0", [1.0, 2.0]),
        ],
    )
    def test_given_numeric_feature_string_when_running_predict_then_parses_values_as_floats(
        self, runner, raw_features, expected
    ):
        with patch.object(
            cli_module, "model_predict", return_value={"ok": True}
        ) as mock_predict:
            result = runner.invoke(cli, ["predict", "--features", raw_features])

        assert result.exit_code == 0
        mock_predict.assert_called_once_with(expected)

    def test_given_integer_features_when_running_predict_then_passes_native_python_floats(
        self, runner
    ):
        with patch.object(cli_module, "model_predict", return_value={}) as mock_predict:
            runner.invoke(cli, ["predict", "--features", "1,2,3,4"])

        features = mock_predict.call_args.args[0]
        assert all(isinstance(value, float) for value in features)

    @pytest.mark.parametrize(
        "raw_features",
        [
            "a,b,c,d",
            "1.0,abc,3.0,4.0",
            "1.0;2.0;3.0;4.0",
            "1.0,,3.0,4.0",
            "1.0,2.0,3.0,",
            "",
            ",",
            "one,two,three",
        ],
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
        assert "Missing option" in result.output
        assert "--features" in result.output
        mock_predict.assert_not_called()

    def test_given_features_option_without_value_when_running_predict_then_fails_and_skips_model(
        self, runner
    ):
        with patch.object(cli_module, "model_predict") as mock_predict:
            result = runner.invoke(cli, ["predict", "--features"])

        assert result.exit_code == 2
        mock_predict.assert_not_called()

    def test_given_help_flag_when_running_predict_then_shows_features_option_description(
        self, runner
    ):
        result = runner.invoke(cli, ["predict", "--help"])

        assert result.exit_code == 0
        assert "--features" in result.output
        assert "1.0,2.0,3.0,4.0" in result.output

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

    def test_given_nested_model_result_when_running_predict_then_outputs_valid_json(
        self, runner
    ):
        fake_result = {
            "prediction": 1,
            "probabilities": [0.1, 0.9],
            "meta": {"version": "1.0"},
        }

        with patch.object(cli_module, "model_predict", return_value=fake_result):
            result = runner.invoke(cli, ["predict", "--features", "1,2,3,4"])

        assert result.exit_code == 0
        assert json.loads(result.output) == fake_result

    def test_given_numpy_type_in_model_result_when_running_predict_then_fails_with_type_error(
        self, runner
    ):
        """json.dumps cannot serialize arbitrary objects (e.g. np.int64)."""
        with patch.object(
            cli_module, "model_predict", return_value={"prediction": np.int64(1)}
        ):
            result = runner.invoke(cli, ["predict", "--features", "1,2,3,4"])

        assert result.exit_code != 0
        assert isinstance(result.exception, TypeError)
