"""Export a minimal SSH snapshot from committed bytes, never working-tree blobs."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[3]
MISSION = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'afdm_sp_joint_unrolled/outputs_acquisition_optimized_20261007'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    head = git('rev-parse', 'HEAD').decode().strip()
    prefix = git('rev-parse', '--show-prefix').decode().strip()
    inventory = json.loads((MISSION/'dispatch/import_paths.json').read_text())
    sources = {p for p in inventory['all_paths'] if p.startswith('experiments/')}
    sources.update(str(p.relative_to(ROOT)) for p in
                   (ROOT/'experiments/afdm_acquisition_optimized_20261007').glob('*.py'))
    # Namespace packages may acquire real initializers; preserve any that exist.
    for name in list(sources):
        for parent in Path(name).parents:
            candidate = ROOT/parent/'__init__.py'
            if candidate.is_file():
                sources.add(str(candidate.relative_to(ROOT)))
    contents = {}
    for name in sorted(sources):
        blob = git('show', f'{head}:{prefix}{name}')
        if blob != (ROOT/name).read_bytes():
            raise ValueError('working source differs from committed bytes: '+name)
        contents[name] = blob
    for filename, path in [('STUDY_CONFIG.json', ROOT/'experiments/afdm_acquisition_optimized_20261007/STUDY_CONFIG.json'),
                           ('run_contract.json', MISSION/'run_contract.json'),
                           ('launch_v1.sh', OUTPUT/'launch_v1.sh'),
                           ('bootstrap_remote.py', MISSION/'dispatch/bootstrap_remote.py'),
                           ('harvest_remote.py', MISSION/'dispatch/harvest_remote.py')]:
        relative = str(path.relative_to(ROOT))
        blob = git('show', f'{head}:{prefix}{relative}')
        if blob != path.read_bytes():
            raise ValueError('uncommitted control: '+relative)
        contents['frozen_control/'+filename] = blob
        if filename == 'STUDY_CONFIG.json':
            contents['experiments/afdm_acquisition_optimized_20261007/STUDY_CONFIG.json'] = blob
    manifest = dict(local_commit=head, project_git_prefix=prefix,
                    provenance='All payload bytes extracted from this local Git commit; remote snapshot has its own commit',
                    sha256={name:hashlib.sha256(data).hexdigest() for name,data in contents.items()})
    contents['SOURCE_MANIFEST.json'] = (json.dumps(manifest,indent=2)+'\n').encode()
    target = OUTPUT/'source_v1.tar.gz'
    with target.open('xb') as stream, tarfile.open(fileobj=stream,mode='w:gz') as archive:
        for name,data in contents.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            archive.addfile(info,io.BytesIO(data))
    with (OUTPUT/'SOURCE_MANIFEST.json').open('xb') as handle:
        handle.write(contents['SOURCE_MANIFEST.json'])
    print(json.dumps(dict(tar=str(target),bytes=target.stat().st_size,files=len(contents),
                          sha256=hashlib.sha256(target.read_bytes()).hexdigest(),local_commit=head)))


if __name__ == '__main__':
    main()
