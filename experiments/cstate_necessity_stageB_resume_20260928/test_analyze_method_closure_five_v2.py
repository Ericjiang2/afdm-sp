"""Synthetic contract for the single-field postfailure paid-ledger recovery."""

from __future__ import annotations

from pathlib import Path
import tempfile
from types import SimpleNamespace

import pytest

import analyze_method_closure_five_v2 as recovery


def test_prefix_omits_stream_ids_but_continuation_requires_exact_ids() -> None:
    input_row = {"observation_sha256": "input", "observation_hash": "observation",
                 "stream_ids": {"channel": "fixed", "noise": "fixed"}}
    prefix = {"kind": "prefix", "input_sha256": "input",
              "observation_hash": "observation"}
    recovery.validate_paid_input(prefix, input_row)
    with pytest.raises(ValueError, match="schema unexpectedly changed"):
        recovery.validate_paid_input({**prefix, "stream_ids": input_row["stream_ids"]},
                                     input_row)
    continuation = {**prefix, "kind": "continuation",
                    "stream_ids": input_row["stream_ids"]}
    recovery.validate_paid_input(continuation, input_row)
    with pytest.raises(ValueError, match="continuation stream identity"):
        recovery.validate_paid_input({**continuation, "stream_ids": {}}, input_row)
    with pytest.raises(ValueError, match="continuation stream identity"):
        recovery.validate_paid_input({key: value for key, value in continuation.items()
                                      if key != "stream_ids"}, input_row)


def test_raw_stream_identity_still_fails_closed() -> None:
    input_row = {"observation_hash": "observation", "stream_ids": {"noise": "fixed"}}
    paid = {"arm": "F0", "input_sha256": "input"}
    raw = {"observation_id": "s650_f0000", "arm": "F0",
           "input_sha256": "input", "observation_hash": "observation",
           "stream_ids": input_row["stream_ids"]}
    recovery.validate_raw_input(raw, paid, "s650_f0000", input_row)
    with pytest.raises(ValueError, match="raw semantic identity"):
        recovery.validate_raw_input({**raw, "stream_ids": {"noise": "other"}}, paid,
                                    "s650_f0000", input_row)


def test_erratum_hash_fails_before_any_truth_path_access() -> None:
    with tempfile.TemporaryDirectory() as directory:
        erratum = Path(directory) / "erratum.json"
        erratum.write_text('{}')
        args = SimpleNamespace(analysis_erratum=erratum,
                               analysis_erratum_sha256="0" * 64)
        with pytest.raises(ValueError, match="erratum transfer SHA"):
            recovery.verify_pretruth(args)
