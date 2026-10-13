"""Verify and initialize a new isolated snapshot under the authorized output."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

ROOT = Path('/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_phase_budget_20261007')


def main():
    os.chdir(ROOT)
    snapshot = ROOT/'source_v1'
    snapshot.mkdir(exist_ok=False)
    archive = ROOT/'source_v1.tar.gz'
    with tarfile.open(archive, 'r:gz') as bundle:
        for member in bundle.getmembers():
            target = snapshot/member.name
            if not member.isfile() or not target.resolve().is_relative_to(snapshot):
                raise ValueError('unsafe snapshot member: '+member.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as handle:
                handle.write(bundle.extractfile(member).read())
    manifest = json.loads((snapshot/'SOURCE_MANIFEST.json').read_text())
    for name, expected in manifest['sha256'].items():
        if hashlib.sha256((snapshot/name).read_bytes()).hexdigest() != expected:
            raise ValueError('snapshot digest mismatch: '+name)
    for name in ('bootstrap_remote.py', 'harvest_remote.py', 'launch_v1.sh'):
        if (ROOT/name).read_bytes() != (snapshot/'frozen_control'/name).read_bytes():
            raise ValueError('outer launcher differs from frozen committed bytes: '+name)
    env = dict(os.environ, GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1')

    def git(*args):
        return subprocess.check_output(['git', *args], cwd=snapshot, env=env).decode().strip()

    git('init', '--quiet', '--template=')
    git('add', '--', '.')
    git('-c', 'user.name=AFDM frozen research snapshot', '-c', 'user.email=local-snapshot@invalid',
        '-c', 'commit.gpgsign=false', 'commit', '-m', 'Freeze committed local research source '+manifest['local_commit'])
    control = ROOT/'control'
    control.mkdir(exist_ok=False)
    for name in ('STUDY_CONFIG.json', 'run_contract.json'):
        with (control/name).open('xb') as handle:
            handle.write((snapshot/'frozen_control'/name).read_bytes())
    record = dict(local_commit=manifest['local_commit'], remote_snapshot_commit=git('rev-parse', 'HEAD'),
                  snapshot=str(snapshot), source_files_verified=len(manifest['sha256']),
                  tar_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                  provenance='Independent remote Git snapshot of manifest-verified local committed bytes; commits intentionally differ',
                  old_remote_project='not a Git repository; no existing source directory overwritten')
    with (ROOT/'DEPLOYMENT.json').open('x') as handle:
        json.dump(record,handle,indent=2)
        handle.write('\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
