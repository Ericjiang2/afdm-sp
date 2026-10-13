"""Hash finished remote artifacts and bundle only bounded small evidence."""
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path('/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_acquisition_shortburst_20261007')


def digests(path):
    sha, md5 = hashlib.sha256(), hashlib.md5()
    with path.open('rb') as handle:
        for block in iter(lambda:handle.read(1024*1024), b''):
            sha.update(block)
            md5.update(block)
    return sha.hexdigest(), md5.hexdigest()


def main():
    required_phases = {'P', 'A'}
    folders = sorted(p.parent for p in (ROOT/'execution').glob('*/registration.json'))
    completed = {}
    for folder in folders:
        attempt = json.loads((folder/'attempt.json').read_text())
        registration = json.loads((folder/'registration.json').read_text())
        phase = registration['config']['phase']
        if attempt['status'] == 'complete':
            completed.setdefault(phase, []).append(folder.name)
    if not required_phases.issubset(completed):
        raise ValueError('missing successful phases: '+str(sorted(required_phases-set(completed))))
    stages, inventory = [], []
    for folder in folders:
        stage = folder.name
        attempt = json.loads((folder/'attempt.json').read_text())
        registration = json.loads((folder/'registration.json').read_text())
        stages.append(dict(stage=stage, status=attempt['status'], wall_seconds=attempt['wall_seconds'],
                           peak_rss_bytes=attempt['peak_rss_bytes'],
                           wall_reservation=registration['wall_cap_seconds'],
                           observations=registration['config']['new_observations'],
                           geometry_reservation=registration['config']['new_geometry_probes']))
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                sha, md5 = digests(path)
                inventory.append(dict(path=str(path), bytes=path.stat().st_size, sha256=sha, md5=md5))
    snapshot = ROOT/'source_v1'
    manifest = json.loads((snapshot/'SOURCE_MANIFEST.json').read_text())
    for path, digest in manifest['sha256'].items():
        if digests(snapshot/path)[0] != digest:
            raise ValueError('snapshot changed: '+path)
    report = dict(stages=stages, completed_stages_by_phase=completed, inventory=inventory, source_manifest_reverified=True,
                  total_stage_bytes=sum(row['bytes'] for row in inventory),
                  total_reserved_seconds=sum(row['wall_reservation'] for row in stages),
                  total_registered_observations=sum(row['observations'] for row in stages),
                  total_geometry_reserved=sum(row['geometry_reservation'] for row in stages),
                  total_stage_wall_seconds=sum(row['wall_seconds'] for row in stages),
                  max_process_peak_rss_bytes=max(row['peak_rss_bytes'] for row in stages),
                  provenance='Absolute remote paths; MD5 and SHA256 include all saved raw and source snapshots',
                  selection='Registered stage files below 10 MB including small NPZ; larger files remain remote with full paths and MD5/SHA256')
    with (ROOT/'REMOTE_INVENTORY.json').open('x') as handle:
        json.dump(report,handle,separators=(',',':'))
        handle.write('\n')
    summary = {k:v for k,v in report.items() if k != 'inventory'}
    summary['inventory_file'] = dict(path=str(ROOT/'REMOTE_INVENTORY.json'),
                                     md5=digests(ROOT/'REMOTE_INVENTORY.json')[1])
    with (ROOT/'RESOURCE_RESULTS.json').open('x') as handle:
        json.dump(summary,handle,indent=2)
        handle.write('\n')
    selected = [p for p in ROOT.iterdir() if p.is_file() and p.suffix in ('.json','.log','.sh')]
    selected += [p for p in (ROOT/'design_reference').iterdir() if p.is_file()]
    selected += [p for folder in folders for p in folder.rglob('*') if p.is_file()]
    with tarfile.open(ROOT/'small_evidence.tar.gz','x:gz') as archive:
        for path in sorted(selected):
            if path.stat().st_size >= 10_000_000:
                continue
            archive.add(path,arcname=str(path.relative_to(ROOT)),recursive=False)
    print(json.dumps({k:v for k,v in report.items() if k not in ('inventory','stages')}))


if __name__ == '__main__':
    main()
