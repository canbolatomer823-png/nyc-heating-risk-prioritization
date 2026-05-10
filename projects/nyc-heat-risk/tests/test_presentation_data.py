from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from reporting.build_presentation_data import parse_glmm_random_intercept_sd


class PresentationDataTest(unittest.TestCase):
    def test_parse_glmm_random_intercept_sd_reads_effect_column(self) -> None:
        csv_text = """model,term,coefficient,p_value,conf_low,conf_high,effect,posterior_sd
binomial_glmm,Intercept,-4.0,0.0,-4.1,-3.9,0.01,0.03
binomial_glmm,sd_building_random_intercept,-0.04,,,,0.9611169675,0.0446
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "coefficients.csv"
            path.write_text(csv_text, encoding="utf-8")
            value = parse_glmm_random_intercept_sd(path)

        self.assertEqual(value, 0.9611)


if __name__ == "__main__":
    unittest.main()
