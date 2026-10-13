"""Source-bound physical-context regression; opens no observation or truth payload."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import analyze_r2  # noqa: E402


def test_source_bound_context():
    baseline = ROOT / "experiments/sp_afdm_frozen_20260920"
    observed = ROOT / "results/tf_cgr_mechanism_20260923_v2/observed"
    args = SimpleNamespace(baseline=baseline, observed=observed)
    context = analyze_r2._source_bound_physical_context(args)
    assert context["n"] == 1024
    assert context["c1"] == 5 / 2048
    assert np.isclose(
        context["c2"], (np.sqrt(2) - 1) / (2 * 1024**2), rtol=0, atol=1e-20
    )
    assert context["factory_arguments"] == [1024, 2.0, 8, 10.0, 4.0]
    with TemporaryDirectory() as temp:
        fake = Path(temp)
        manifest = json.loads((observed / "manifest.json").read_text())
        name = "baseline/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/afdm_env.py"
        manifest["source_hashes"][name] = "0" * 64
        (fake / "manifest.json").write_text(json.dumps(manifest))
        try:
            analyze_r2._source_bound_physical_context(
                SimpleNamespace(baseline=baseline, observed=fake)
            )
        except ValueError:
            pass
        else:
            raise AssertionError("altered physical-context source was accepted")
    print("source-bound physical context and mismatch guard: pass")


if __name__ == "__main__":
    test_source_bound_context()
