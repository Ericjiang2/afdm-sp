"""Pure schedule/budget guards; no estimator or receiver execution."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

import pytest

from f1_reproduce import _phase_guard


def _write(root: Path, name: str, score: int) -> None:
    (root / name).write_text(json.dumps({'records': [{'coordinate_scores': score}]}) + '\n')


def test_fixed_branches_and_no_retry() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / 'output'
        assert _phase_guard(argparse.Namespace(out=root, mode='direct-fast')) == []
        with pytest.raises(FileExistsError):
            _phase_guard(argparse.Namespace(out=root, mode='direct-fast'))
        journal = root / 'attempts.jsonl'
        journal.write_text('{}\n')
        _write(root, 'direct_fast.json', 995)
        assert len(_phase_guard(argparse.Namespace(out=root, mode='wrapper-fast'))) == 1
        journal.write_text('{}\n{}\n')
        _write(root, 'wrapper_fast.json', 995)
        assert len(_phase_guard(argparse.Namespace(out=root, mode='direct-reference'))) == 2
        journal.write_text('{}\n{}\n{}\n')
        _write(root, 'direct_reference.json', 995)
        assert len(_phase_guard(argparse.Namespace(out=root, mode='history'))) == 3
        with pytest.raises(ValueError):
            _phase_guard(argparse.Namespace(out=root, mode='focused'))
        _write(root, 'wrapper_fast.json', 1002)
        assert len(_phase_guard(argparse.Namespace(out=root, mode='focused'))) == 3
        with pytest.raises(ValueError):
            _phase_guard(argparse.Namespace(out=root, mode='history'))
