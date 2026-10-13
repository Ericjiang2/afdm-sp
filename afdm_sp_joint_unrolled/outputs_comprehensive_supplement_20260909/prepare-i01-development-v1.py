"""Extract a source-bound development snapshot; run tests only, no receiver F."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

R = Path('/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-sha256', required=True)
    args = parser.parse_args()
    archive = R / 'i01-development-source-v1.zip'
    if hashlib.sha256(archive.read_bytes()).hexdigest() != args.archive_sha256:
        raise ValueError('archive digest mismatch')
    root = R / 'source-i01-development-v1'
    root.mkdir()
    with zipfile.ZipFile(archive) as bundle:
        for name in bundle.namelist():
            rel = Path(name)
            if rel.is_absolute() or '..' in rel.parts:
                raise ValueError('invalid archive member')
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(bundle.read(name))
    manifest = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((root / 'source').rglob('*.py'))}
    with (root / 'source-manifest.json').open('x') as stream:
        json.dump(manifest, stream, indent=2)
    inputs = R / 'i01-development-inputs-v1'
    inputs.mkdir()
    input_hashes = {}
    for name in ('data-protocol.json', 'development-protocol.json', 'quote-summary.json'):
        data = (root / 'inputs' / name).read_bytes()
        with (inputs / name).open('xb') as stream:
            stream.write(data)
        input_hashes[name] = hashlib.sha256(data).hexdigest()
    env = dict(os.environ, PYTHONPATH=str(root / 'source'), PYTHONDONTWRITEBYTECODE='1',
               OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               NUMEXPR_NUM_THREADS='1', TMPDIR=str(R / 'tmp'),
               MPLCONFIGDIR=str(R / 'tmp/matplotlib'), XDG_CACHE_HOME=str(R / 'tmp/cache'))
    tests = ['test_supplement_feedback_run', 'test_supplement_feedback',
             'test_supplement_feedback_adapter', 'test_supplement_feedback_diagnostic',
             'test_supplement_feedback_schedule', 'test_supplement_baselines']
    subprocess.run(['/home/guoyikun/.conda/envs/AFDM/bin/python', '-m', 'unittest',
                    *['afdm_sp_joint_unrolled.' + t for t in tests]], cwd=root, env=env,
                   check=True, timeout=120)
    print(json.dumps(dict(status='prepared_tested_not_launched', source=str(root),
                          package_files=len(manifest), inputs=input_hashes, reserved_F=0)))


if __name__ == '__main__':
    main()
