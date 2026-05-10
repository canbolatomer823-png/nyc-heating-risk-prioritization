from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from aws.artifact_store import derive_s3_key
from aws.render_deployment_assets import load_env_file, render_text


class DeriveS3KeyTest(unittest.TestCase):
    def test_simple(self) -> None:
        self.assertEqual(derive_s3_key("prefix", "key"), "prefix/key")

    def test_double_slash(self) -> None:
        self.assertEqual(derive_s3_key("prefix/", "/key"), "prefix/key")

    def test_empty_prefix(self) -> None:
        self.assertEqual(derive_s3_key("", "key"), "key")
        self.assertEqual(derive_s3_key("/", "/key"), "key")

    def test_nested_key(self) -> None:
        self.assertEqual(
            derive_s3_key("nyc-heat-risk/latest", "models/bundle.joblib"),
            "nyc-heat-risk/latest/models/bundle.joblib",
        )

    def test_prefix_without_slash(self) -> None:
        self.assertEqual(derive_s3_key("data", "file.csv"), "data/file.csv")


class LoadEnvFileTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp_dir.name)

    def tearDown(self) -> None:
        self._tmp_dir.cleanup()

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_env_file(self.tmp_path / "nonexistent.env")

    def test_valid_env(self) -> None:
        env_content = (
            "AWS_REGION=us-east-1\n"
            "AWS_ACCOUNT_ID=123456789012\n"
            "ARTIFACT_BUCKET=my-bucket\n"
            "ARTIFACT_PREFIX=prefix\n"
            "ECR_REPOSITORY=my-repo\n"
            "EKS_CLUSTER_NAME=my-cluster\n"
            "IRSA_ROLE_ARN=arn:aws:iam::123:role/test\n"
            "IMAGE_TAG=0.1\n"
        )
        env_file = self.tmp_path / "valid.env"
        env_file.write_text(env_content)
        values = load_env_file(env_file)
        self.assertEqual(values["AWS_REGION"], "us-east-1")
        self.assertEqual(values["AWS_ACCOUNT_ID"], "123456789012")

    def test_missing_key_raises(self) -> None:
        env_content = "AWS_REGION=us-east-1\n"
        env_file = self.tmp_path / "partial.env"
        env_file.write_text(env_content)
        with self.assertRaises(ValueError) as ctx:
            load_env_file(env_file)
        self.assertIn("Missing required keys", str(ctx.exception))

    def test_invalid_line_raises(self) -> None:
        env_content = "no-equals-sign\n"
        env_file = self.tmp_path / "invalid.env"
        env_file.write_text(env_content)
        with self.assertRaises(ValueError):
            load_env_file(env_file)

    def test_comment_lines_ignored(self) -> None:
        content = (
            "# comment line\n"
            "AWS_REGION=us-east-1\n"
            "AWS_ACCOUNT_ID=123456789012\n"
            "ARTIFACT_BUCKET=my-bucket\n"
            "ARTIFACT_PREFIX=prefix\n"
            "ECR_REPOSITORY=my-repo\n"
            "EKS_CLUSTER_NAME=my-cluster\n"
            "IRSA_ROLE_ARN=arn:aws:iam::123:role/test\n"
            "IMAGE_TAG=0.1\n"
        )
        env_file = self.tmp_path / "with_comments.env"
        env_file.write_text(content)
        values = load_env_file(env_file)
        self.assertEqual(values["AWS_REGION"], "us-east-1")


class RenderTextTest(unittest.TestCase):
    def _sample_values(self) -> dict[str, str]:
        return {
            "AWS_ACCOUNT_ID": "123456789012",
            "AWS_REGION": "us-east-1",
            "ECR_REPOSITORY": "my-repo",
            "IMAGE_TAG": "0.1",
            "IRSA_ROLE_ARN": "arn:aws:iam::123:role/test-role",
            "ARTIFACT_BUCKET": "my-artifact-bucket",
            "ARTIFACT_PREFIX": "nyc-heat-risk/latest",
        }

    def test_irsa_replacement(self) -> None:
        template = "role: REPLACE_WITH_IRSA_ROLE_ARN"
        result = render_text(template, self._sample_values())
        self.assertIn("arn:aws:iam::123:role/test-role", result)
        self.assertNotIn("REPLACE_WITH", result)

    def test_ecr_image_replacement(self) -> None:
        template = "image: REPLACE_WITH_ECR/nyc-heat-risk-api:0.1"
        result = render_text(template, self._sample_values())
        self.assertIn("123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo:0.1", result)

    def test_bucket_replacement(self) -> None:
        template = "bucket: replace-me-artifact-bucket"
        result = render_text(template, self._sample_values())
        self.assertIn("my-artifact-bucket", result)
        self.assertNotIn("replace-me", result)

    def test_no_replacement_needed(self) -> None:
        template = "clean text with no placeholders"
        result = render_text(template, self._sample_values())
        self.assertEqual(result, template)


if __name__ == "__main__":
    unittest.main()
