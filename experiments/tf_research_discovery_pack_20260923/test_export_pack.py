from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_pack import (cohort_of, json_value, native_round_summaries,
                         nearest_control, observed_geometry, safe_path)
from read_artifact import load


def test_truth_labels_stay_separate_from_observed_control_distance():
    anchor = dict(observation_id="s650_f0004", snr_centi_db="650")
    controls = [dict(observation_id="s600_f0000", snr_centi_db="600", true_path_count=1),
                dict(observation_id="s650_f0002", snr_centi_db="650", true_path_count=9),
                dict(observation_id="s650_f0003", snr_centi_db="650", true_path_count=1)]
    observed = {"s650_f0004": dict(tf_complete_seconds=.31, baseline_syndrome_weight=4),
                "s650_f0002": dict(tf_complete_seconds=.32, baseline_syndrome_weight=4),
                "s650_f0003": dict(tf_complete_seconds=.35, baseline_syndrome_weight=1)}
    assert nearest_control(anchor, controls, observed) == "s650_f0002"


def test_cohort_requires_a_real_saved_outcome():
    assert cohort_of(dict(tf_correct="True", rescue="False",
                          remaining_triggered_failure="False")) == "tf_success"
    assert cohort_of(dict(tf_correct="False", rescue="True",
                          remaining_triggered_failure="False")) == "rescued"
    assert cohort_of(dict(observation_id="x", tf_correct="False", rescue="False",
                          remaining_triggered_failure="True")) == "remaining_failure"
    assert cohort_of(dict(observation_id="x", tf_correct="True", rescue="False",
                          remaining_triggered_failure="True")) == "remaining_failure"
    with pytest.raises(ValueError, match="unclassified"):
        cohort_of(dict(observation_id="x", tf_correct="False", rescue="False",
                       remaining_triggered_failure="False"))


def test_observed_geometry_and_scalar_trace_views():
    raw = dict(baseline_arrays=dict(r1_delays=np.array([2, 2]),
                                    r1_dopplers=np.array([.25, -.25])))
    assert observed_geometry(raw) == ([2, 2], [.25, -.25])
    trace = dict(iteration=np.int64(3), gain=np.complex128(1 + 2j),
                 vector=np.arange(128))
    shown = json_value(trace)
    assert shown["iteration"] == 3
    assert shown["gain"] == {"real": 1., "imag": 2.}
    assert shown["vector"] == {"saved_in_trace_artifact": True,
                               "shape": [128], "dtype": "int64"}


def test_saved_native_round_summary_and_explicit_missingness():
    arrays = dict(r0_input_llr=np.array([-2., 2.]),
                  r0_app=np.array([-3., 3.]),
                  r0_check=np.array([-1., 1.]),
                  r0_mu=np.array([1 + 1j, 0j]),
                  r0_variance=np.array([.2, .4]),
                  r0_gains=np.array([3 + 4j]),
                  r0_gain_variance=np.array([.1]),
                  r0_ce_history=np.array([5., 4.]),
                  r0_inference_trace=[dict(iteration=0)])
    rows = native_round_summaries(arrays)
    assert rows[0]["input_llr"]["rms"] == 2.
    assert rows[0]["gain_magnitude"]["mean"] == 5.
    assert rows[0]["ce_objective_last"] == 4.
    assert rows[0]["inference_iterations"] == 1
    assert rows[0]["observed_residual"] is None
    assert rows[1]["app_llr"] is None


def test_pack_reader_round_trip_and_path_boundary(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                           "sp_afdm_frozen_20260920" / "src"))
    from evidence import save_artifact
    path = tmp_path / "trace.npz"
    save_artifact(path, dict(score=np.array([[1., 2.]]), steps=(1, 2)),
                  dict(kind="observed_tf_trace", observation_id="s650_f0000"))
    payload, identity = load(path)
    assert np.array_equal(payload["score"], [[1., 2.]])
    assert payload["steps"] == (1, 2)
    assert identity["kind"] == "observed_tf_trace"
    assert safe_path(tmp_path, "trace.npz") == path
    with pytest.raises(ValueError, match="unsafe"):
        safe_path(tmp_path, "../truth.npz")
