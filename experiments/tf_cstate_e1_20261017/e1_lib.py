"""Shared helpers for E-1: frozen-source path setup, bitwise deep-equal, variant-vs-frozen source diff check."""
from __future__ import annotations

import dataclasses
import difflib
import hashlib
from pathlib import Path
import re
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent

# Frozen directories (read only).  deinlab keeps the sp_afdm_* sources under *_reviewed_* names (identical md5, see SOURCE_MD5.txt).
FROZEN_SRC_CANDIDATES = (
    ('sp_afdm_frozen_20260920', 'sp_afdm_frozen_reviewed_20260921'),          # physical.py, messages.py
    ('sp_afdm_native_joint_20260921', 'sp_afdm_native_joint_reviewed_20260921'),  # twofft.py
)
FROZEN_FLAT = ('tf_cstate_validation_20260922', 'tf_geometry_reopen_20260922')  # compact_state.py, geometry_validation.py, geometry_reopen.py


def prepare_paths():
    """Put the frozen math modules (physical, messages, twofft, compact_state) and this directory on sys.path (idempotent)."""
    paths = []
    for names in FROZEN_SRC_CANDIDATES:
        for name in names:
            if (EXPERIMENTS / name / 'src').is_dir():
                paths.append(EXPERIMENTS / name / 'src')
                break
    paths += [EXPERIMENTS / d for d in FROZEN_FLAT]
    paths.append(HERE)
    for p in paths:
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


def md5_file(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


SKIP_KEYS = ('elapsed_seconds', 'stage_timing', 'seconds')  # wall-clock fields only (decoder.metadata.seconds, kernel elapsed/stage timing)


def deep_equal(a, b, path='', skip=SKIP_KEYS, out=None):
    """Bitwise structural comparison; returns the list of mismatch paths (empty list == identical).

    Dataclasses are compared field-wise irrespective of class identity (frozen vs variant ExchangeResult / Path); keys named in
    ``skip`` (wall-clock timing) are ignored.  Floats and arrays are compared bit for bit.
    """
    out = [] if out is None else out
    if len(out) > 20:
        return out
    if dataclasses.is_dataclass(a) and not isinstance(a, type):
        a = {f.name: getattr(a, f.name) for f in dataclasses.fields(a)}
    if dataclasses.is_dataclass(b) and not isinstance(b, type):
        b = {f.name: getattr(b, f.name) for f in dataclasses.fields(b)}
    if isinstance(a, dict) and isinstance(b, dict):
        ka, kb = [k for k in a if k not in skip], [k for k in b if k not in skip]
        if set(ka) != set(kb):
            out.append(f'{path}: keys differ {sorted(set(ka) ^ set(kb))}')
            return out
        for k in ka:
            deep_equal(a[k], b[k], f'{path}.{k}', skip, out)
        return out
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        a, b = np.asarray(a), np.asarray(b)
        if a.dtype != b.dtype or a.shape != b.shape or np.ascontiguousarray(a).tobytes() != np.ascontiguousarray(b).tobytes():
            out.append(f'{path}: array differs (dtype {a.dtype}/{b.dtype}, shape {a.shape}/{b.shape})')
        return out
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            out.append(f'{path}: length {len(a)} != {len(b)}')
            return out
        for i, (x, y) in enumerate(zip(a, b)):
            deep_equal(x, y, f'{path}[{i}]', skip, out)
        return out
    if isinstance(a, (float, np.floating)) and isinstance(b, (float, np.floating)):
        if not (np.float64(a).tobytes() == np.float64(b).tobytes()):
            out.append(f'{path}: {a!r} != {b!r}')
        return out
    if a != b:
        out.append(f'{path}: {a!r} != {b!r}')
    return out


# ----------------------------------------------------------------------------- variant-vs-frozen source diff
_ALLOWED_INSERT_PREFIXES = (
    '# E-1 variant', '# (md5', '# through _gamma_cross', '# gamma_mode ("full"',
    'if gamma_mode', 'elif gamma_mode', 'raise ValueError("gamma_mode must be full or diag")',
    'return np.zeros((len(a), len(b)), dtype=complex)', 'gamma = np.diag(np.diag(gamma))')
_TOKEN = re.compile(r', gamma_mode(?:: str = "full"|="full"|)(?=[)\]:,\n]|$)')


def normalize_variant_line(line):
    line = line.replace('geometry_reopen_variant', 'geometry_reopen')
    return _TOKEN.sub('', line)


def variant_diff_problems(frozen_path, variant_path):
    """Empty list iff the variant is the frozen file plus only gamma_mode additions (inserted lines on the allow-list,
    ', gamma_mode...' argument tokens, and the import redirect geometry_reopen -> geometry_reopen_variant)."""
    old = Path(frozen_path).read_text().splitlines()
    new = Path(variant_path).read_text().splitlines()
    kept = [normalize_variant_line(l) for l in new if not l.strip().startswith(_ALLOWED_INSERT_PREFIXES)]
    if kept == old:
        return []
    return [l for l in difflib.unified_diff(old, kept, 'frozen', 'variant-normalised', lineterm='', n=0)][:40]
