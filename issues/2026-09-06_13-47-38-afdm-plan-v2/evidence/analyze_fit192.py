"""Validate the exact registered fit matrix and preserve its evidence."""
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
import tarfile


def wilson(k, n):
    z = 1.959963984540054
    p = k/n
    center = (p+z*z/(2*n))/(1+z*z/n)
    radius = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return [center-radius, center+radius]


def analyze(archive, output):
    with tarfile.open(archive) as tar:
        raw = {m.name: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    queue = json.loads(raw['queue-status.json'])
    assert queue['complete'] and len(queue['runs']) == 3
    assert all(r['exit_code'] == 0 for r in queue['runs'])
    batches, statuses, cells = [], [], []
    for rep in (30, 31, 32):
        status = json.loads(raw[f'rep{rep}/status.json'])
        rows = [json.loads(s) for s in raw[f'rep{rep}/frames.jsonl'].splitlines()]
        assert status['complete'] and not status.get('failure')
        assert status['computed_frames'] == status['completed_frames'] == len(rows) == 64
        assert [(r['split'], r['replicate'], r['frame_index'], r['snr']) for r in rows] == [
            ('D_cal', rep, i, 8) for i in range(64)]
        assert status['config']['receiver_shell'] == 'direct40'
        assert status['calibration_sha256'] == '74f23844a95ea36ea90490f7aa5fca76bd14ff8a97f954f4387a4e85c852444e'
        for r in rows:
            assert set(r['arms']) == {'a0', 'baseline'}
            assert r['nomination_cap'] == r['active_cap'] == 40
            for arm, result in r['arms'].items():
                assert result['finite']
                trace = result['capacity_trace']
                assert len([t for t in trace if t['stage'] == 'outer']) == 10
                assert trace[0]['stage'] == 'initial' and trace[-1]['stage'] == 'final'
                for t in trace:
                    assert len(set(t['atom_ids'])) == t['unique_count'] <= t['limit']
                    assert t['limit'] == (48 if t['stage'] == 'temporary' else 40)
                assert result['support_repair_enabled'] == (arm == 'baseline')
                if arm == 'a0':
                    assert not result['rounds'] and result['shared_scorer_preparation_seconds'] == 0
        for arm in ('a0', 'baseline'):
            errors = sum(r['arms'][arm]['info_errors'] > 0 for r in rows)
            cells.append(dict(replicate=rep, arm=arm, n=64, frame_errors=errors, FER=errors/64,
                              info_bit_errors=sum(r['arms'][arm]['info_errors'] for r in rows)))
        batches.extend(rows); statuses.append(status)
    for key in ('source_sha256', 'checkpoint_sha256', 'ldpc_sha256', 'calibration_sha256', 'device'):
        assert all(s[key] == statuses[0][key] for s in statuses)
    assert len({r['channel_seed'] for r in batches}) == len({r['input_hashes']['y'] for r in batches}) == 192
    pooled = {}
    for arm in ('a0', 'baseline'):
        k = sum(r['arms'][arm]['info_errors'] > 0 for r in batches)
        pooled[arm] = dict(frame_errors=k, n=192, FER=k/192, descriptive_wilson95=wilson(k, 192))
    reference = 'a0' if pooled['a0']['frame_errors'] <= pooled['baseline']['frame_errors'] else 'baseline'
    within = .05 <= pooled[reference]['FER'] <= .20
    result = dict(scope='development fit; not confirmatory', cells=cells, pooled=pooled,
        selected_reference=reference, selected_reference_label='A0' if reference == 'a0' else 'A2',
        selection_rule='lower pooled FER, exact tie selects simpler A0', snr=8,
        calibration_triggered=not within, working_point_status='frozen' if within else 'needs_baseline_calibration',
        paired_a2_win=sum(r['arms']['a0']['info_errors'] > 0 and r['arms']['baseline']['info_errors'] == 0 for r in batches),
        paired_a2_harm=sum(r['arms']['a0']['info_errors'] == 0 and r['arms']['baseline']['info_errors'] > 0 for r in batches),
        queue=queue, subprocess_seconds=sum(r['ended_at']-r['started_at'] for r in queue['runs']),
        cpu_core_hours=4*sum(r['ended_at']-r['started_at'] for r in queue['runs'])/3600,
        artifact_sha256={name: hashlib.sha256(value).hexdigest() for name, value in raw.items()},
        remote_root=statuses[0]['config']['out'].rsplit('/', 1)[0],
        failures=['initial launcher argparse rejection; zero receiver tasks started; corrected within original deadline'],
        completed_receiver_evaluations=384, trace_checks='192 paired frames; every outer/final and temporary bound checked',
        prior_sha256=statuses[0]['calibration_sha256'])
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    output.with_suffix('.tar.gz').write_bytes(gzip.compress(Path(archive).read_bytes(), mtime=0))
    print(json.dumps({k: result[k] for k in ['pooled', 'selected_reference_label', 'calibration_triggered', 'paired_a2_win', 'paired_a2_harm']}, indent=2))


if __name__ == '__main__':
    analyze(Path(sys.argv[1]), Path(sys.argv[2]))
