"""
cli.py — Command-line interface for training and invoking the model.

Usage:
    python cli.py train
    python cli.py predict --features "1.0,2.0,3.0,4.0"
"""

import json

import click
import numpy as np

from src.model import predict as model_predict
from src.model import train as model_train


@click.group()
def cli():
    """CLI for managing the ML model lifecycle."""


@cli.command()
def train():
    """Train the model with synthetic data and save it to disk."""
    click.echo("Generating training data...")
    X = np.random.randn(200, 4)
    y = (X[:, 0] + X[:, 1] > 0).astype(int)

    click.echo("Training model...")
    model_train(X, y)
    click.echo("✅ Model trained and saved successfully.")


@cli.command()
@click.option(
    "--features",
    required=True,
    help="Numeric features separated by commas. Example: 1.0,2.0,3.0,4.0",
)
def predict(features: str):
    """Make a prediction from features provided via the CLI."""
    try:
        X = [float(f.strip()) for f in features.split(",")]
    except ValueError:
        raise click.BadParameter(
            "All features must be numeric values separated by commas."
        )

    result = model_predict(X)
    click.echo(json.dumps(result, indent=2))


if __name__ == "__main__":
    cli()
