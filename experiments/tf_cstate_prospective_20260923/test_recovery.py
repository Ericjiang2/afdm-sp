"""Guard the postfailure analysis retry against source drift and log collisions."""
from __future__ import annotations

import difflib
import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import retry_failed_analysis as retry  # noqa: E402


def test_recovery_analyzer_changes_only_known_receipt_schema():
    directory = Path(__file__).resolve().parent
    original = (directory / 'analyze_prospective.py').read_text()
    amended = (directory / 'analyze_recovery.py').read_text()
    changed = list(difflib.unified_diff(original.splitlines(), amended.splitlines()))
    deleted = [line for line in changed if line.startswith('-') and not line.startswith('---')]
    inserted = [line for line in changed if line.startswith('+') and not line.startswith('+++')]
    assert deleted == ["-                              'committed_blob_sha1'}"]
    assert inserted == [
        "+                              'committed_blob_sha1','verification'}",
        "+            or local_binding['verification'] !=",
        "+               'actual local git show byte equality and git rev-parse object identity'",
    ]
    assert hashlib.sha256(amended.encode()).hexdigest() == retry.RECOVERY_ANALYZER_SHA256
    protocol = directory.parents[1] / 'results/tf_cstate_prospective_20260923/protocol'
    registration = json.loads((protocol / 'registration.json').read_text())
    assert hashlib.sha256(original.encode()).hexdigest() == registration[
        'registration_source_hashes'][
            'tf_cstate_prospective_20260923/analyze_prospective.py']


def test_retry_phase_keeps_logs_outside_analyzer_output(tmp_path, monkeypatch):
    monkeypatch.setattr(retry, 'PROJECT', tmp_path)
    root = tmp_path / 'recovery'
    root.mkdir()
    retry.phase(root, 'analysis', [sys.executable, '-B', '-c', 'print("ready")'], {})
    assert not (root / 'analysis').exists()
    assert json.loads((root / 'logs/analysis/lifecycle.json').read_text())['exit_code'] == 0
    assert (root / 'logs/analysis/stdout.log').read_text().strip() == 'ready'
    with pytest.raises(RuntimeError, match='exited 3'):
        retry.phase(root, 'verification', [sys.executable, '-B', '-c', 'raise SystemExit(3)'], {})
    assert json.loads((root / 'logs/verification/lifecycle.json').read_text())['exit_code'] == 3
