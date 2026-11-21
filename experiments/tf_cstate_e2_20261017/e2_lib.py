"""Shared helpers for E-2: path setup (frozen math modules + the frozen E-1 variants), deep-equal (from E-1), guard-diff check."""
from __future__ import annotations

import difflib
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
E1_DIR = EXPERIMENTS / 'tf_cstate_e1_20261017'
if str(E1_DIR) not in sys.path:
    sys.path.insert(0, str(E1_DIR))
import e1_lib  # noqa: E402  (frozen E-1 helper; md5 in SOURCE_MD5.txt)

deep_equal = e1_lib.deep_equal
md5_file = e1_lib.md5_file


def prepare_paths():
    """Frozen math modules (physical, messages, twofft, compact_state), the frozen E-1 variants and this directory on sys.path."""
    e1_lib.prepare_paths()  # frozen src dirs + E-1 dir
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))


# ----------------------------------------------------------------------------- guard-variant vs E-1 variant source diff
_ALLOWED_INSERT_PREFIXES = (
    '# E-2 guard variant', '# (md5 f513f8d3', '# ("off" default', '# and to every local',
    'from codelay_guard import', 'if codelay_guard', 'equal = equal | conflict_matrix', 'mask &= ~hits_group',
    'raise ValueError("codelay_guard')
_TOKENS = (
    re.compile(r' or path_conflicts\(test, others, len\(Y\), codelay_guard\)'),
    re.compile(r', codelay_guard="off", n=None'),
    re.compile(r', codelay_guard="off"'),
    re.compile(r', codelay_guard, len\(Y\)'),
    re.compile(r', codelay_guard(?=\))'),
)


def normalize_guard_line(line):
    for t in _TOKENS:
        line = t.sub('', line)
    return line


def guard_diff_problems(e1_variant_path, e2_path):
    """Empty list iff the E-2 file is the E-1 variant plus only codelay_guard additions."""
    old = Path(e1_variant_path).read_text().splitlines()
    new = Path(e2_path).read_text().splitlines()
    kept = [normalize_guard_line(l) for l in new if not l.strip().startswith(_ALLOWED_INSERT_PREFIXES)]
    if kept == old:
        return []
    return [l for l in difflib.unified_diff(old, kept, 'e1-variant', 'e2-normalised', lineterm='', n=0)][:40]
