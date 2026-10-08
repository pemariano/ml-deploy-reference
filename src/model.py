"""
model.py — Placeholder of a ML model.
Focus on the MLOps pipeline.
"""

import os
import logging

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

logger = logging.getLogger()


MODEL_PATH = os.getenv("MODEL_PATH", "model.joblib")


def _generate_training_data():
    """Generate synthetic training data for demonstration purposes."""
    logger.info("Generating training data...")
    X = np.random.randn(200, 4)
    y = (X[:, 0] + X[:, 1] > 0).astype(int)
    return X, y


def train(X: np.ndarray, y: np.ndarray) -> LogisticRegression:
    """
    Train the model and persist it to disk.

    Args:
        X: Feature matrix of shape (n_samples, n_features).
        y: Target vector of shape (n_samples,).

    Returns:
        Trained LogisticRegression model.
    """
    X, y = _generate_training_data()
    model = LogisticRegression(max_iter=200)
    model.fit(X, y)
    joblib.dump(model, MODEL_PATH)
    return model


def load() -> LogisticRegression:
    """
    Load the model saved on disk.

    Returns:
        Loaded LogisticRegression model.
    """
    return joblib.load(MODEL_PATH)


def predict(features: list[float]) -> dict:
    """
    Make a prediction from a list of features.

    Args:
        features: List of feature values for a single sample.

    Returns:
        Dictionary containing:
            - prediction: The predicted class label.
            - probability: The confidence probability (0-1) rounded to 4 decimal places.
    """
    model = load()
    X = np.array(features).reshape(1, -1)
    prediction = int(model.predict(X)[0])
    probability = float(model.predict_proba(X).max())
    return {"prediction": prediction, "probability": round(probability, 4)}
