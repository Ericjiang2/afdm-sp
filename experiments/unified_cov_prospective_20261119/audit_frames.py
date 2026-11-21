"""Read archived frame identifiers and range declarations, without running any receiver."""

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tf_split_prosp_20261018'))
from verify_frames import config_frames, ranges

INITIAL = 4400
BLOCK = 200
P1 = b'2261fde33dab09d1'
FRAME = re.compile(rb'"(?:frame|frame_id|frame_index)"\s*:\s*(\d+)')
RANGE = re.compile(
    r'"((?:[\w]+_)?frames|(?:[\w]+_)?frame_range)"\s*:\s*\[\s*(\d+)\s*,\s*(\d+)\s*\]'
)
ARGUMENT = re.compile(
    r'--(frame-offset|frame-start|start-frame|frame-stop|frame-end|end-frame|n-frames|frames)'
    r'(?:=|[\s"\x27,]+)(\d+)'
)
WATCH_SUFFIXES = ('.json', '.jsonl', '.jsonl.gz', '.json.gz', '.yaml', '.yml', '.toml', '.sh')
THIS_EXPERIMENT = 'unified_cov_prospective_20261119'


def path_stream(path, head):
    if P1 in head:
        return 'P1'
    if not path.name.startswith(('rows', 'main-', 'data_')):
        return 'unclassified'
    for config in (*path.parent.glob('*config*.json'), *path.parent.glob('*CONFIG*.json')):
        if P1 in config.read_bytes():
            return 'P1'
    return 'unclassified'


def manifest_frames(text):
    frames = set()
    # Preserve both endpoints where old config schemas leave the convention implicit.
    for _, start, end in RANGE.findall(text):
        start, end = int(start), int(end)
        if 0 <= start <= end <= 1_000_000:
            frames.update(range(max(INITIAL, start), end + 1))
    args = {name: int(n) for name, n in ARGUMENT.findall(text)}
    if args:
        start = next((args[k] for k in ('frame-offset', 'frame-start', 'start-frame') if k in args), 0)
        end = next((args[k] for k in ('frame-stop', 'frame-end', 'end-frame') if k in args), None)
        if end is None and (count := args.get('n-frames', args.get('frames'))) is not None:
            end = start + count - 1
        if end is not None and start <= end <= 1_000_000:
            frames.update(range(max(INITIAL, start), end + 1))
    return frames


def scan_file(path, structured):
    frames = set()
    opener = gzip.open if path.name.endswith('.gz') else open
    with opener(path, 'rb') as handle:
        head = handle.read(65536)
        handle.seek(0)
        if structured:
            data = handle.read()
            frames.update(int(m[1]) for m in FRAME.finditer(data))
            if path.name.endswith(('.json', '.json.gz')):
                doc = json.loads(data)
                frames.update(config_frames(doc))
            frames.update(manifest_frames(data.decode('utf-8')))
        else:
            for line in handle:
                frames.update(int(m[1]) for m in FRAME.finditer(line))
    return frames, head


def scan(root):
    groups = {
        'experiments': sorted(path for path in (root / 'experiments').glob('*/out')
                              if path.parent.name != THIS_EXPERIMENT),
        'historical': sorted((root / 'afdm_sp_joint_unrolled').glob('outputs_*')),
    }
    scanned, hits, errors, archived_smoke = Counter(), [], [], []
    for scope, directories in groups.items():
        scanned[f'{scope}_roots'] = len(directories)
        for directory in directories:
            for path in sorted(directory.rglob('*')):
                if not path.is_file() or not path.name.lower().endswith(WATCH_SUFFIXES):
                    continue
                structured = not path.name.endswith(('.jsonl', '.jsonl.gz'))
                scanned[f'{scope}_' + ('metadata' if structured else 'rows')] += 1
                try:
                    seen, head = scan_file(path, structured)
                    if overlap := sorted(frame for frame in seen if frame >= INITIAL):
                        record = dict(file=str(path.relative_to(root)), frames=ranges(overlap),
                                      stream=path_stream(path, head))
                        if 'smoke' in path.name and set(range(8400, 8412)).issubset(seen):
                            archived_smoke.append(record['file'])
                        hits.append(record)
                except (OSError, ValueError, EOFError) as exc:
                    errors.append(dict(file=str(path.relative_to(root)), error=type(exc).__name__))
    return dict(scanned=dict(scanned), hits=hits, errors=errors, smoke_8400_8411=archived_smoke)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    print(json.dumps(scan(args.root), sort_keys=True))


if __name__ == '__main__':
    main()
