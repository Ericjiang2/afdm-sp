"""Supplement the checksum-bound historical audit with manifest schemas it missed."""
import argparse
from collections import Counter
import gzip
import json
import os
from pathlib import Path
import re

from audit_delta import BASE, CONFIG_AUDIT, NUMAX, SINCE, covered
from frames import WATCH_SUFFIXES, EXTRA_SUFFIXES, scan_file, structured_frames, ranges

# These are exactly the extra JSON field names interpreted by structured_frames.
EXTRA = re.compile(
    rb'"(?:frame_ranges|frame_intervals|frame_ids|frames_used|frames_inclusive|inclusive_block|'
    rb'first_frame|frame_first|frame_start|start_frame|frame_lo)"\s*:', re.I)
NON_RUN_AUDITS = {BASE, CONFIG_AUDIT, NUMAX}


def scan(root):
    hits, errors, counts = {}, {}, Counter()
    roots = [root/'experiments', root/'issues', root/'results', root/'.mission', root/'.trellis/tasks']
    roots.extend((root/'afdm_sp_joint_unrolled').glob('outputs_*'))
    for scope in (p for p in roots if p.is_dir()):
        issue = scope == root/'issues'
        for folder, dirs, files in os.walk(scope):
            dirs[:] = [d for d in dirs if d not in ('__pycache__', 'gamma0_exchange_20261120', '11-20-gamma0-exchange')]
            for name in files:
                suffix = name.lower()
                is_json = suffix.endswith(('.json', '.json.gz'))
                if name.startswith('._') or not (
                        is_json or suffix.endswith('.csv') or (issue and suffix.endswith(WATCH_SUFFIXES + EXTRA_SUFFIXES))):
                    continue
                path = Path(folder)/name
                relative = path.relative_to(root)
                label = str(relative)
                if label in NON_RUN_AUDITS:
                    continue
                try:
                    if is_json and not issue and covered(relative) and path.stat().st_ctime < SINCE.timestamp():
                        counts['old_metadata_extra_fields'] += 1
                        opener = gzip.open if suffix.endswith('.gz') else open
                        with opener(path, 'rb') as handle:
                            raw = handle.read()
                        frames = structured_frames(json.loads(raw)) if EXTRA.search(raw) else set()
                    else:
                        counts['additional_full_metadata'] += 1
                        frames = scan_file(path, label)
                    if frames:
                        hits[label] = ranges(frames)
                except (OSError, ValueError, EOFError) as exc:
                    errors[label] = f'{type(exc).__name__}: {exc}'
    return dict(scanned=dict(counts), frame_hits=hits, errors=errors)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    print(json.dumps(scan(args.root), indent=2, sort_keys=True))
