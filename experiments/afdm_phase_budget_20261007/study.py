"""Run two registered deterministic integration stages on SSH."""
import argparse
import json
from pathlib import Path

from . import thread_binding  # noqa: F401 -- bind the recorder's deferred dependency before snapshotting.
from .audit import audit, validate_primary
from .quadrature import calculate
from .protocol import run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact-root', type=Path, required=True)
    parser.add_argument('--phase', choices=('Q', 'A'), required=True)
    args = parser.parse_args()
    config_path = Path(__file__).with_name('STUDY_CONFIG.json')
    config = json.loads(config_path.read_text())
    config['phase'] = args.phase
    sources = [config_path]
    if args.phase == 'Q':
        def callback(output):
            return calculate(config)
    else:
        source = args.artifact_root/'execution/Q/results.json'
        sources.extend((source, args.artifact_root/'execution/Q/attempt.json',
                        args.artifact_root/'execution/Q/registration.json'))
        validate_primary(source, config)
        def callback(output):
            return audit(source, config)
    run(args.phase, config, sources, callback, artifact_root=args.artifact_root, wall_seconds=60)


if __name__ == '__main__':
    main()
