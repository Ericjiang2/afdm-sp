#!/usr/bin/env python
"""Fresh-frame audit for slot_mismatch (task 10-19-slot-mismatch).  Read-only.

Reuses the scanner of tf_split_prosp_20261018/verify_frames.py unchanged (imported as a module; only its SKIP_DIRS is overridden so that the
split-principle block 7000..7199 is scanned too).  Reports, for each candidate block, the frames already seen through the P1 stream
(entropy 2261fde3..., domain TCRF) in configs/rows under experiments/*/out, plus every integer in the block in .py/.sh/.md/.json source text.

Usage: python frame_audit.py --root <.../experiments> --out <file.json> --blocks 7000:8000,8000:8200
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent


def load_scanner(root):
    path = Path(root) / 'tf_split_prosp_20261018' / 'verify_frames.py'
    spec = importlib.util.spec_from_file_location('verify_frames', path)
    vf = importlib.util.module_from_spec(spec)
    sys.modules['verify_frames'] = vf
    spec.loader.exec_module(vf)
    vf.SKIP_DIRS = {'__pycache__', '_archive', HERE.name}
    return vf


def static_hits(root, lo, hi):
    pat = re.compile(r'(?<![\d.\w])(\d{4,5})(?![\d.\w])')
    hits = []
    for p in sorted(Path(root).rglob('*')):
        parts = set(p.parts)
        if p.suffix not in ('.py', '.sh', '.md') or '_archive' in parts or '__pycache__' in parts or HERE.name in parts or 'out' in parts:
            continue
        try:
            for i, line in enumerate(p.read_text(errors='replace').splitlines(), 1):
                for m in pat.finditer(line):
                    if lo <= int(m.group(1)) < hi:
                        hits.append(dict(file=str(p.relative_to(root)), line=i, value=int(m.group(1)), text=line.strip()[:160]))
        except OSError:
            pass
    return hits


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--root', type=Path, required=True)
    a.add_argument('--out', type=Path, required=True)
    a.add_argument('--blocks', default='7000:8000,8000:8200')
    a = a.parse_args()
    vf = load_scanner(a.root)
    files, secs = vf.scan_out(a.root)
    p1_used, all_used = set(), set()
    for r in files:
        all_used |= r['frames']
        if r['p1']:
            p1_used |= r['frames']
    res = dict(files_scanned=len(files), seconds=round(secs, 1), p1_used_frame_ranges=vf.ranges(p1_used), blocks={})
    for b in a.blocks.split(','):
        lo, hi = (int(x) for x in b.split(':'))
        p1_hit = vf.overlaps(p1_used, lo, hi)
        res['blocks'][b] = dict(
            p1_hit_frames=vf.ranges(p1_hit), p1_fresh=not p1_hit,
            p1_hit_files={r['file']: vf.ranges(vf.overlaps(r['frames'], lo, hi)) for r in files if r['p1'] and vf.overlaps(r['frames'], lo, hi)},
            non_p1_hit_files={r['file']: dict(frames=vf.ranges(vf.overlaps(r['frames'], lo, hi)), other_entropy=r['other_entropy'])
                              for r in files if (not r['p1']) and vf.overlaps(r['frames'], lo, hi)},
            static_hits=static_hits(a.root, lo, hi))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=1, sort_keys=True) + '\n')
    for b, v in res['blocks'].items():
        print(b, 'P1 fresh:', v['p1_fresh'], 'P1 hit frames:', v['p1_hit_frames'], 'P1 hit files:', list(v['p1_hit_files'])[:6],
              'non-P1 hit files:', len(v['non_p1_hit_files']), 'static hits:', len(v['static_hits']))
    print('P1 used ranges:', res['p1_used_frame_ranges'])


if __name__ == '__main__':
    main()
