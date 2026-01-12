import unittest
from unittest.mock import patch

from ml_serve_core.utils.storage_strategy import (
    ModelSizeDetector,
    StrategySelector,
    determine_storage_strategy,
)


class TestModelSizeDetector(unittest.TestCase):
    def setUp(self):
        self.detector = ModelSizeDetector(tracking_uri="http://mlflow.local")

    def test_extract_run_and_path_runs_uri(self):
        uri = "runs:/run_id_123/model_path"
        run_id, path = self.detector._extract_run_and_path(uri)
        self.assertEqual(run_id, "run_id_123")
        self.assertEqual(path, "model_path")

    def test_extract_run_and_path_models_uri_version(self):
        uri = "models:/my_model/1"
        
        with patch.object(ModelSizeDetector, "_get_model_version", return_value={
            "run_id": "run_id_456",
            "source": "s3://bucket/run_id_456/artifacts/model_dir"
        }):
            run_id, path = self.detector._extract_run_and_path(uri)
        self.assertEqual(run_id, "run_id_456")
        self.assertEqual(path, "model_dir")

    def test_extract_run_and_path_models_uri_stage(self):
        uri = "models:/my_model/Production"
        
        mock_version = {
            "run_id": "run_id_789",
            "source": "s3://bucket/run_id_789/artifacts/model_dir"
        }
        with patch.object(ModelSizeDetector, "_get_latest_version", return_value=mock_version):
            run_id, path = self.detector._extract_run_and_path(uri)
        self.assertEqual(run_id, "run_id_789")
        self.assertEqual(path, "model_dir")

    def test_get_model_size_bytes_with_no_tracking_uri(self):
        detector = ModelSizeDetector()
        size = detector.get_model_size_bytes("runs:/run_id/model")
        self.assertIsNone(size)

    def test_get_model_size_bytes_delegates_to_sum(self):
        with patch.object(ModelSizeDetector, "_extract_run_and_path", return_value=("run_id", "artifact")):
            with patch.object(ModelSizeDetector, "_sum_artifacts", return_value=1024):
                size = self.detector.get_model_size_bytes("runs:/run_id/artifact")
                self.assertEqual(size, 1024)

    def test_extract_run_and_path_mlflow_artifacts_uri(self):
        uri = "mlflow-artifacts:/exp_id/run_id_abc/artifacts/model_path"
        run_id, path = self.detector._extract_run_and_path(uri)
        self.assertEqual(run_id, "run_id_abc")
        self.assertEqual(path, "model_path")

    def test_extract_run_and_path_mlflow_artifacts_uri_fallback(self):
        uri = "mlflow-artifacts:/exp_id/run_id_xyz/custom_path"
        run_id, path = self.detector._extract_run_and_path(uri)
        self.assertEqual(run_id, "run_id_xyz")
        self.assertEqual(path, "custom_path")


class TestStrategySelector(unittest.TestCase):
    def setUp(self):
        self.selector = StrategySelector()

    def test_select_unknown(self):
        self.assertEqual(self.selector.select(None), "emptydir")
        self.assertEqual(self.selector.select(0), "emptydir")

    def test_select_small(self):
        # 500 MB
        size = 500 * 1024 * 1024
        self.assertEqual(self.selector.select(size), "emptydir")

    def test_select_medium(self):
        # 2 GB
        size = 2 * 1024 * 1024 * 1024
        self.assertEqual(self.selector.select(size), "pvc")

    def test_select_large(self):
        # 10 GB
        size = 10 * 1024 * 1024 * 1024
        self.assertEqual(self.selector.select(size), "pvc")

    def test_format_size(self):
        self.assertEqual(self.selector.format_size(None), "unknown")
        self.assertEqual(self.selector.format_size(100), "100.00 B")
        self.assertEqual(self.selector.format_size(1024), "1.00 KB")
        self.assertEqual(self.selector.format_size(1024 * 1024 * 1.5), "1.50 MB")
        self.assertEqual(self.selector.format_size(1024 * 1024 * 1024 * 2), "2.00 GB")


class TestDetermineStorageStrategy(unittest.TestCase):
    def test_auto_uses_detector_and_selector(self):
        with patch.object(ModelSizeDetector, "get_model_size_bytes", return_value=2 * 1024 * 1024 * 1024):
            with patch.object(StrategySelector, "select", return_value="pvc"):
                strategy = determine_storage_strategy(
                    user_strategy="auto",
                    model_uri="models:/my_model/1",
                    tracking_uri="http://mlflow.local",
                    username="user",
                    password="pass",
                )
                self.assertEqual(strategy, "pvc")

    def test_invalid_strategy_raises_value_error(self):
        with self.assertRaises(ValueError):
            determine_storage_strategy(
                user_strategy="invalid",
                model_uri="models:/my_model/1",
            )

    def test_user_specified_strategy(self):
        strategy = determine_storage_strategy(
            user_strategy="emptydir",
            model_uri="models:/my_model/1",
        )
        self.assertEqual(strategy, "emptydir")

if __name__ == '__main__':
    unittest.main()
