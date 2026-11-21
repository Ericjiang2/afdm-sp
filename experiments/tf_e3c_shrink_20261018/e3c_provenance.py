"""Resolve historical frozen source locations, retaining their original digests."""
from __future__ import annotations
import hashlib
from pathlib import Path

ALIASES={
    'sp_afdm_native_joint_20260921':'sp_afdm_native_joint_reviewed_20260921',
    'sp_afdm_frozen_20260920':'sp_afdm_frozen_reviewed_20260921',
}


def resolve_frozen(root, manifest, loaded_md5=None, loaded_paths=None):
    root=Path(root)
    loaded_md5=loaded_md5 or {}
    loaded_paths=loaded_paths or {}
    result={}
    for line in Path(manifest).read_text().splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        expected,rel=line.split()
        declared=Path(rel)
        candidates=[root/declared]
        if declared.parts[0] in ALIASES:
            candidates.append(root/ALIASES[declared.parts[0]]/Path(*declared.parts[1:]))
        # Context records the actual loaded source, possibly under reviewed aliases.
        loaded=loaded_paths.get(declared.stem)
        if loaded:
            lp=Path(loaded)
            if not lp.is_absolute():
                lp=root.parent/lp
            # A recorded import is authoritative, even if missing or wrong.
            candidates=[lp]
        actual=next((p for p in candidates if p.is_file()),None)
        if actual is None:
            raise FileNotFoundError(f'frozen source absent: {rel}; candidates: {candidates}')
        blob=actual.read_bytes()
        md5=hashlib.md5(blob).hexdigest()
        if md5!=expected:
            raise RuntimeError(f'frozen source md5 mismatch {rel} via {actual}: {md5} != {expected}')
        loaded_digest=loaded_md5.get(declared.stem)
        if loaded_digest is not None and loaded_digest!=expected:
            raise RuntimeError(f'loaded frozen module mismatch: {declared.stem}')
        result[rel]=dict(actual_path=str(actual.resolve()),expected_md5=expected,actual_md5=md5,
                         loaded_md5=loaded_digest,sha256=hashlib.sha256(blob).hexdigest())
    return result
