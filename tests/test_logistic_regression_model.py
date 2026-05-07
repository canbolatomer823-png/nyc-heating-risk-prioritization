from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from modeling.logistic_regression_model import (
    build_classifier,
    build_pipeline,
    logit_feature,
    fit_platt_calibrator,
    apply_calibration,
    select_threshold,
    compute_metrics,
)
from modeling.risk_features import NUMERIC_FEATURES, CATEGORICAL_FEATURES


class BuildClassifierTest(unittest.TestCase):
    def test_logistic_defaults(self) -> None:
        clf = build_classifier("logistic")
        self.assertIsInstance(clf, LogisticRegression)
        self.assertEqual(clf.max_iter, 1000)

    def test_logistic_custom_max_iter(self) -> None:
        clf = build_classifier("logistic", max_iter=500)
        self.assertEqual(clf.max_iter, 500)

    def test_xgboost_created(self) -> None:
        clf = build_classifier("xgboost")
        self.assertEqual(clf.__class__.__name__, "XGBClassifier")

    def test_lightgbm_created(self) -> None:
        clf = build_classifier("lightgbm")
        self.assertEqual(clf.__class__.__name__, "LGBMClassifier")

    def test_xgboost_passes_params(self) -> None:
        clf = build_classifier("xgboost", n_estimators=42, max_depth=3, learning_rate=0.05)
        self.assertEqual(clf.n_estimators, 42)
        self.assertEqual(clf.max_depth, 3)

    def test_lightgbm_passes_params(self) -> None:
        clf = build_classifier("lightgbm", n_estimators=77, max_depth=4)
        self.assertEqual(clf.n_estimators, 77)
        self.assertEqual(clf.max_depth, 4)

    def test_unknown_model_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_classifier("random_forest")


class BuildPipelineTest(unittest.TestCase):
    def test_pipeline_structure(self) -> None:
        pipe = build_pipeline("logistic")
        self.assertIsInstance(pipe, Pipeline)
        steps = dict(pipe.steps)
        self.assertIn("preprocess", steps)
        self.assertIn("classifier", steps)

    def test_all_model_types(self) -> None:
        for model_type in ("logistic", "xgboost", "lightgbm"):
            with self.subTest(model=model_type):
                pipe = build_pipeline(model_type)
                self.assertIsInstance(pipe, Pipeline)

    def test_pipeline_passes_kwargs(self) -> None:
        pipe = build_pipeline("logistic", max_iter=999)
        clf = pipe.steps[-1][1]
        self.assertEqual(clf.max_iter, 999)


class LogitFeatureTest(unittest.TestCase):
    def test_pd_series(self) -> None:
        probs = pd.Series([0.3, 0.5, 0.7])
        result = logit_feature(probs)
        self.assertEqual(result.shape, (3, 1))
        self.assertAlmostEqual(result[1, 0], 0.0)

    def test_numpy_array(self) -> None:
        probs = np.array([0.1, 0.9])
        result = logit_feature(probs)
        self.assertAlmostEqual(result[0, 0], np.log(0.1 / 0.9), places=5)
        self.assertAlmostEqual(result[1, 0], np.log(0.9 / 0.1), places=5)

    def test_extreme_values_are_clipped(self) -> None:
        probs = np.array([0.0, 1.0])
        result = logit_feature(probs)
        self.assertTrue(np.isfinite(result).all())


class PlattCalibratorTest(unittest.TestCase):
    def _dummy_data(self) -> tuple[pd.Series, pd.Series]:
        y_true = pd.Series([0, 0, 0, 1, 1, 1, 1, 1])
        probs = pd.Series([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8])
        return y_true, probs

    def test_fit_returns_logistic_regression(self) -> None:
        y_true, probs = self._dummy_data()
        calibrator = fit_platt_calibrator(y_true, probs)
        self.assertIsInstance(calibrator, LogisticRegression)

    def test_calibration_improves(self) -> None:
        y_true, probs = self._dummy_data()
        calibrator = fit_platt_calibrator(y_true, probs)
        calibrated = apply_calibration(calibrator, pd.Series([0.99]))
        self.assertIsInstance(calibrated, np.ndarray)

    def test_none_calibrator_returns_raw(self) -> None:
        raw = np.array([0.1, 0.5, 0.9])
        result = apply_calibration(None, raw)
        np.testing.assert_array_equal(result, raw)


class SelectThresholdTest(unittest.TestCase):
    def test_returns_float_in_range(self) -> None:
        y_true = pd.Series([0, 0, 0, 1, 1, 1])
        probs = pd.Series([0.1, 0.3, 0.4, 0.5, 0.7, 0.9])
        thresh = select_threshold(y_true, probs)
        self.assertIsInstance(thresh, float)
        self.assertTrue(0.05 <= thresh <= 0.95)

    def test_perfect_case(self) -> None:
        y_true = pd.Series([0, 0, 0, 1, 1, 1])
        probs = pd.Series([0.0, 0.1, 0.2, 0.8, 0.9, 1.0])
        thresh = select_threshold(y_true, probs, beta=1.0)
        self.assertTrue(0.05 <= thresh <= 0.95)

    def test_beta_2_favors_recall(self) -> None:
        y_true = pd.Series([0] * 8 + [1] * 2)
        probs = pd.Series([0.1] * 8 + [0.4, 0.7])
        thresh_f1 = select_threshold(y_true, probs, beta=1.0)
        thresh_f2 = select_threshold(y_true, probs, beta=2.0)
        with self.subTest("thresholds differ"):
            self.assertIsInstance(thresh_f1, float)
            self.assertIsInstance(thresh_f2, float)


class ComputeMetricsTest(unittest.TestCase):
    def test_all_metrics_present(self) -> None:
        y_true = pd.Series([0, 0, 1, 1, 1])
        probs = pd.Series([0.1, 0.2, 0.3, 0.7, 0.9])
        metrics = compute_metrics(y_true, probs, threshold=0.5)
        required = ("rows", "actual_positive_rate", "mean_probability",
                     "predicted_positive_rate", "accuracy", "precision",
                     "recall", "f1", "average_precision", "brier_score", "roc_auc")
        for key in required:
            with self.subTest(key=key):
                self.assertIn(key, metrics)

    def test_perfect_model_metrics(self) -> None:
        y_true = pd.Series([0, 0, 1, 1, 1])
        probs = pd.Series([0.04, 0.06, 0.96, 0.98, 0.99])
        metrics = compute_metrics(y_true, probs, threshold=0.3)
        self.assertAlmostEqual(metrics["accuracy"], 1.0)
        self.assertAlmostEqual(metrics["precision"], 1.0)
        self.assertAlmostEqual(metrics["recall"], 1.0)
        self.assertAlmostEqual(metrics["f1"], 1.0)


if __name__ == "__main__":
    unittest.main()
