"""One user-authorized offline recovery of the sealed, failed analysis phase.

The original campaign remains invalid. This script never generates observations
or invokes either receiver; it writes only under a new recovery result root.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import traceback


PROJECT = Path('/data/guoyikun/00inbox/AFDM-channel-estimation')
CAMPAIGN = 'tf_cstate_prospective_20260923'
PYTHON = '/home/guoyikun/.conda/envs/AFDM/bin/python'
RECOVERY_ANALYZER_SHA256 = '1f29bf3de0687abb5830baff5e2aa4eb97fdf18323b10c81cb07c9b7145c770b'
LOCAL_BINDING_KEYS = {'git_commit', 'committed_path', 'registration_sha256',
                      'committed_blob_sha1', 'verification'}
VERIFICATION_TEXT = 'actual local git show byte equality and git rev-parse object identity'


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: dict) -> None:
    with path.open('w') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def phase(root: Path, name: str, argv: list[str], env: dict[str, str]) -> None:
    directory = root / 'logs' / name
    directory.mkdir(parents=True)
    record = {'argv': argv, 'status': 'running', 'started_epoch': time.time()}
    write_json(directory / 'lifecycle.json', record)
    with (directory / 'stdout.log').open('wb') as stdout, \
         (directory / 'stderr.log').open('wb') as stderr:
        try:
            finished = subprocess.run(argv, cwd=PROJECT, env=env,
                                      stdout=stdout, stderr=stderr,
                                      timeout=10800, check=False)
        except subprocess.TimeoutExpired as error:
            record.update(status='invalid_timeout', finished_epoch=time.time())
            write_json(directory / 'lifecycle.json', record)
            raise TimeoutError(f'{name} exceeded 10800 seconds') from error
    record.update(status='complete' if finished.returncode == 0 else 'invalid_exit',
                  finished_epoch=time.time(), exit_code=finished.returncode)
    write_json(directory / 'lifecycle.json', record)
    if finished.returncode:
        raise RuntimeError(f'{name} exited {finished.returncode}; see {directory}/stderr.log')


def run() -> None:
    campaign = PROJECT / 'results' / CAMPAIGN
    code = PROJECT / 'experiments' / CAMPAIGN
    root = campaign / 'recovery_20260923'
    if root.exists():
        raise FileExistsError('one-time recovery output already exists')
    original = json.loads((campaign / 'pipeline_status.json').read_text())
    if (original.get('status') != 'invalid' or original.get('phase') != 'analysis'
            or original.get('exit_code') != 1):
        raise ValueError('original campaign is not the registered analysis failure')
    stderr = (campaign / 'launch/analysis/stderr.log').read_text()
    if 'ValueError: local preregistration Git-show receipt differs' not in stderr:
        raise ValueError('original failure reason differs')
    for name in ('generation', 'receiving'):
        life = json.loads((campaign / 'launch' / name / 'lifecycle.json').read_text())
        if life.get('status') != 'complete' or life.get('exit_code') != 0:
            raise ValueError(f'{name} was not complete')
    protocol = campaign / 'protocol'
    registration = json.loads((protocol / 'registration.json').read_text())
    binding = json.loads((protocol / 'local_git_binding.json').read_text())
    if set(binding) != LOCAL_BINDING_KEYS or binding['verification'] != VERIFICATION_TEXT:
        raise ValueError('only the known local binding schema mismatch is recoverable')
    if sha256(code / 'analyze_recovery.py') != RECOVERY_ANALYZER_SHA256:
        raise ValueError('recovery analyzer source differs')
    original_analyzer = code / 'analyze_prospective.py'
    expected = registration['registration_source_hashes'][
        f'{CAMPAIGN}/analyze_prospective.py']
    if sha256(original_analyzer) != expected:
        raise ValueError('frozen original analyzer source differs')
    for relative, digest in registration['registration_source_hashes'].items():
        if sha256(PROJECT / 'experiments' / relative) != digest:
            raise ValueError(f'frozen registered source differs: {relative}')
    evidence_git = campaign / 'evidence_git'
    seal_commit = original['observed_seal_commit']
    registration_commit = original['registration_commit']
    for commit, relative, disk in (
        (registration_commit, 'registration/registration.json',
         protocol / 'registration.json'),
        (registration_commit, 'registration/local_git_binding.json',
         protocol / 'local_git_binding.json'),
        (seal_commit, 'observed/observed_seal.json',
         campaign / 'observed/observed_seal.json'),
        (seal_commit, 'population_truth_seal.json',
         campaign / 'population_truth/truth_seal.json'),
    ):
        actual = subprocess.check_output(['git', '-C', str(evidence_git), 'show',
                                          f'{commit}:{relative}'])
        if actual != disk.read_bytes():
            raise ValueError(f'sealed Git object differs: {relative}')
    subprocess.run(['git', '-C', str(evidence_git), 'merge-base',
                    '--is-ancestor', registration_commit, seal_commit], check=True)

    root.mkdir()
    status = dict(schema='tf-cstate-postfailure-recovery/1', status='running',
                  phase='analysis', started_epoch=time.time(),
                  original_campaign_status='invalid',
                  original_registration_commit=registration_commit,
                  original_observed_seal_commit=seal_commit,
                  original_analyzer_sha256=expected,
                  recovery_analyzer_sha256=RECOVERY_ANALYZER_SHA256,
                  change='Accept exact fifth local binding key and its exact value only')
    write_json(root / 'status.json', status)
    source = PROJECT / 'experiments/sp_afdm_native_joint_reviewed_20260921'
    baseline = PROJECT / 'experiments/sp_afdm_frozen_reviewed_20260921'
    env = os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES='', OPENBLAS_NUM_THREADS='1',
               OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1',
               VECLIB_MAXIMUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1',
               TMPDIR=str(root), XDG_CACHE_HOME=str(root), MPLCONFIGDIR=str(root),
               TORCH_HOME=str(root), SPAFDM_BASELINE_ROOT=str(baseline),
               PYTHONPATH=':'.join(str(path) for path in (
                   source / 'src', baseline / 'src', code,
                   PROJECT / 'experiments/tf_cstate_validation_20260922',
                   PROJECT / 'experiments/tf_geometry_reopen_20260922',
                   PROJECT / 'experiments/tf_production_gap_audit_20260922')))
    common = ['--evidence-git', str(evidence_git),
              '--seal-commit', seal_commit,
              '--registration', str(protocol / 'registration.json'),
              '--population-observed', str(campaign / 'population_observed'),
              '--truth-root', str(campaign / 'population_truth'),
              '--observed', str(campaign / 'observed'),
              '--source', str(source), '--baseline', str(baseline)]
    try:
        phase(root, 'analysis', [PYTHON, '-B', str(code / 'analyze_recovery.py'),
                                 *common, '--out', str(root / 'analysis')], env)
        status['phase'] = 'independent_verification'
        write_json(root / 'status.json', status)
        phase(root, 'verification', [PYTHON, '-B', str(code / 'verify_prospective.py'),
                                     *common, '--registration-commit', registration_commit,
                                     '--analysis', str(root / 'analysis'),
                                     '--out', str(root / 'verification')], env)
        receipt = json.loads((root / 'verification/receipt.json').read_text())
        if receipt.get('status') != 'pass':
            raise ValueError('independent recovery verification did not pass')
        status.update(status='completed', phase='finished', finished_epoch=time.time(),
                      analysis_summary_sha256=sha256(root / 'analysis/summary.json'),
                      verification_receipt_sha256=sha256(root / 'verification/receipt.json'))
        write_json(root / 'status.json', status)
    except BaseException as error:
        status.update(status='failed', error=repr(error), phase=status['phase'],
                      finished_epoch=time.time(), traceback=traceback.format_exc())
        write_json(root / 'status.json', status)
        raise


if __name__ == '__main__':
    run()
