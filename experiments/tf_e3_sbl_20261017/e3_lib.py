"""Shared helpers for E-3: frozen-source path setup (read-only imports of the frozen E-1 helper)."""
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
E1_DIR = EXPERIMENTS / 'tf_cstate_e1_20261017'
if str(E1_DIR) not in sys.path:
    sys.path.insert(0, str(E1_DIR))
import e1_lib  # noqa: E402  (frozen E-1 helper: prepare_paths, deep_equal, md5_file; md5 in SOURCE_MD5.txt)

deep_equal = e1_lib.deep_equal
md5_file = e1_lib.md5_file


def prepare_paths():
    """Frozen math modules (physical, messages, twofft, compact_state, geometry_reopen) and this directory on sys.path (idempotent)."""
    e1_lib.prepare_paths()
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
