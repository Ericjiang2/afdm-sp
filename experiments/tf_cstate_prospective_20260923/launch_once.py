"""One unattended registered campaign, with a real Git seal before truth access."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
import traceback


CAMPAIGN = 'tf_cstate_prospective_20260923'
PROJECT = Path('/data/guoyikun/00inbox/AFDM-channel-estimation')
PYTHON = '/home/guoyikun/.conda/envs/AFDM/bin/python'


def write_json(path, value):
    with Path(path).open('w') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def sha256(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            value.update(chunk)
    return value.hexdigest()


def git(repo, *args):
    return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null',
        '-c', 'commit.gpgsign=false', '-C', str(repo), *args])


def commit(repo, message):
    git(repo, 'add', '--all')
    git(repo, '-c', 'user.name=TF prospective evidence',
        '-c', 'user.email=tf-prospective@invalid', 'commit', '-m', message)
    return git(repo, 'rev-parse', 'HEAD').decode().strip()


def check_local_registration_binding(protocol_root):
    """Verify the local Git-show attestation; remote Git is verified separately."""
    registration = protocol_root/'registration.json'
    binding = json.loads((protocol_root/'local_git_binding.json').read_text())
    content = registration.read_bytes()
    blob = hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
    if (re.fullmatch(r'[0-9a-f]{40}', binding.get('git_commit', '')) is None
            or binding.get('registration_sha256') != hashlib.sha256(content).hexdigest()
            or binding.get('committed_blob_sha1') != blob
            or not binding.get('committed_path', '').endswith('/protocol/registration.json')):
        raise ValueError('local registration Git-show binding differs')
    return binding


def check_executable_lock(project, registration):
    experiments = (project/'experiments').resolve()
    for name, expected in registration['registration_source_hashes'].items():
        relative = Path(name)
        source = (experiments/relative).resolve()
        if (relative.is_absolute() or '..' in relative.parts
                or not source.is_relative_to(experiments)
                or sha256(source) != expected):
            raise ValueError(f'precommitted executable differs: {name}')


def phase(root, name, command, env, timeout_seconds):
    logs = root/'launch'/name
    logs.mkdir()
    started = time.time()
    record = dict(phase=name, argv=command, start_epoch=started, status='running')
    write_json(logs/'lifecycle.json', record)
    with (logs/'stdout.log').open('wb') as stdout, (logs/'stderr.log').open('wb') as stderr:
        process = subprocess.Popen(command, env=env, cwd=str(root),
            stdout=stdout, stderr=stderr, start_new_session=True)
        record['pid'] = process.pid
        write_json(logs/'lifecycle.json', record)
        try:
            returncode = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            record.update(status='invalid_timeout', finish_epoch=time.time(),
                          exit_code=process.returncode)
            write_json(logs/'lifecycle.json', record)
            raise TimeoutError(f'{name} exceeded its registered safety limit')
    record.update(status='complete' if returncode == 0 else 'invalid_exit',
                  finish_epoch=time.time(), exit_code=returncode)
    write_json(logs/'lifecycle.json', record)
    if returncode:
        raise RuntimeError(f'{name} exited {returncode}; see {logs}/stderr.log')


def copy_metadata(source, destination):
    destination.mkdir(parents=True)
    for path in sorted(source.iterdir()):
        if path.is_file() and path.suffix in ('.json', '.jsonl'):
            shutil.copy2(path, destination/path.name)


def verify_seal_bytes(root):
    seal = json.loads((root/'observed_seal.json').read_text())
    actual = {str(path.relative_to(root)):sha256(path) for path in root.rglob('*')
              if path.is_file() and path.name != 'observed_seal.json'}
    if seal.get('status') != 'pass' or seal.get('files') != actual:
        raise ValueError('observed artifact seal differs before Git commit')


def check_evidence_size(*roots):
    size = sum(path.stat().st_size for root in roots for path in root.rglob('*')
               if path.is_file())
    if size >= 32*1024**3:
        raise RuntimeError('registered 32GiB phase evidence limit reached')


def inventory(root):
    """Record remote artifact locations without copying large data off-host."""
    files = []
    for dirname in ('population_observed', 'population_truth', 'observed',
                    'analysis', 'verification'):
        for path in sorted((root/dirname).rglob('*')):
            if not path.is_file():
                continue
            md5, sha = hashlib.md5(), hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024*1024), b''):
                    md5.update(block)
                    sha.update(block)
            files.append(dict(path=str(path), bytes=path.stat().st_size,
                              sha256=sha.hexdigest(), md5=md5.hexdigest()))
    write_json(root/'remote_artifacts.json', dict(root=str(root), files=files,
        file_count=len(files), total_bytes=sum(row['bytes'] for row in files)))


def run(project):
    project = project.resolve()
    if project != PROJECT or not project.is_relative_to('/data/guoyikun'):
        raise ValueError('one-shot launcher is restricted to its registered project')
    root = project/'results'/CAMPAIGN
    code = project/'experiments'/CAMPAIGN
    source = project/'experiments/sp_afdm_native_joint_reviewed_20260921'
    baseline = project/'experiments/sp_afdm_frozen_reviewed_20260921'
    protocol = root/'protocol'
    launch = root/'launch'
    launch.mkdir()  # Existing launch directory rejects every automatic retry.
    for name in ('tmp', 'cache'):
        (root/name).mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES='', OPENBLAS_NUM_THREADS='1',
        OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1',
        VECLIB_MAXIMUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1',
        TMPDIR=str(root/'tmp'), XDG_CACHE_HOME=str(root/'cache'),
        MPLCONFIGDIR=str(root/'cache'), TORCH_HOME=str(root/'cache'),
        SPAFDM_BASELINE_ROOT=str(baseline),
        PYTHONPATH=':'.join(str(x) for x in (source/'src', baseline/'src', code,
            project/'experiments/tf_cstate_validation_20260922',
            project/'experiments/tf_geometry_reopen_20260922',
            project/'experiments/tf_production_gap_audit_20260922')))
    status = dict(schema='tf-cstate-prospective-pipeline/1', pid=os.getpid(),
                  started_epoch=time.time(), status='running', phase='registration')
    write_json(root/'pipeline_status.json', status)
    write_json(launch/'environment.json', {key:env[key] for key in (
        'CUDA_VISIBLE_DEVICES', 'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS',
        'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS',
        'TMPDIR', 'XDG_CACHE_HOME', 'PYTHONPATH', 'SPAFDM_BASELINE_ROOT')})
    try:
        registration_file = protocol/'registration.json'
        registration = json.loads(registration_file.read_text())
        binding = check_local_registration_binding(protocol)
        check_executable_lock(project, registration)
        if (registration.get('status') != 'locked'
                or registration['protocol_sha256'] != sha256(protocol/'PROTOCOL.md')
                or registration['random_namespace_sha256'] != sha256(protocol/'random_namespace.json')):
            raise ValueError('registered protocol or namespace changed before launch')
        repo = root/'evidence_git'
        repo.mkdir()
        git(repo, 'init', '-b', 'codex/tf-cstate-prospective')
        shutil.copytree(protocol, repo/'registration')
        registered_commit = commit(repo, 'Register fixed prospective protocol before generation')
        if git(repo, 'show', registered_commit+':registration/registration.json') != registration_file.read_bytes():
            raise ValueError('actual remote registration Git blob differs')
        status.update(registration_commit=registered_commit,
                      local_registration_commit=binding['git_commit'])
        status['phase'] = 'runtime_check'
        write_json(root/'pipeline_status.json', status)
        runtime_probe = ('import json,platform,numpy,scipy,torch; '
            'print(json.dumps(dict(python=platform.python_version(),'
            'numpy=numpy.__version__,scipy=scipy.__version__,torch=torch.__version__)))')
        phase(root, 'runtime_check', [PYTHON, '-B', '-c', runtime_probe], env, 120)
        runtime = json.loads((launch/'runtime_check/stdout.log').read_text())
        if runtime != registration['expected_runtime_versions']:
            raise ValueError('registered runtime versions differ before generation')
        common = ['--registration', str(registration_file),
                  '--source', str(source), '--baseline', str(baseline)]
        population = root/'population_observed'
        truth = root/'population_truth'
        observed = root/'observed'
        status['phase'] = 'generation'
        write_json(root/'pipeline_status.json', status)
        phase(root, 'generation', [PYTHON, '-B', str(code/'generate_population.py'),
            *common, '--registration-commit', registered_commit,
            '--observed-out', str(population), '--truth-out', str(truth),
            '--seconds', '10800'], env, 10860)
        check_evidence_size(population, truth)
        check_executable_lock(project, registration)
        status['phase'] = 'receiving'
        write_json(root/'pipeline_status.json', status)
        phase(root, 'receiving', [PYTHON, '-B', str(code/'run_prospective.py'),
            *common, '--registration-commit', registered_commit,
            '--population-observed', str(population), '--out', str(observed),
            '--seconds', '10800'], env, 10860)
        check_evidence_size(observed)
        status['phase'] = 'observed_git_seal'
        write_json(root/'pipeline_status.json', status)
        check_executable_lock(project, registration)
        verify_seal_bytes(observed)
        verify_seal_bytes(population)
        copy_metadata(observed, repo/'observed')
        copy_metadata(population, repo/'population_observed')
        # This file contains only truth artifact hashes, never truth values.
        shutil.copy2(truth/'truth_seal.json', repo/'population_truth_seal.json')
        sealed_commit = commit(repo, 'Seal complete observed decisions before opening truth')
        content = (observed/'observed_seal.json').read_bytes()
        if git(repo, 'show', sealed_commit+':observed/observed_seal.json') != content:
            raise ValueError('actual observed Git seal differs')
        git(repo, 'merge-base', '--is-ancestor', registered_commit, sealed_commit)
        write_json(root/'seal_binding.json', dict(evidence_git=str(repo),
            registration_commit=registered_commit, observed_seal_commit=sealed_commit,
            observed_seal_sha256=hashlib.sha256(content).hexdigest(),
            committed_path='observed/observed_seal.json'))
        status.update(observed_seal_commit=sealed_commit, phase='analysis')
        write_json(root/'pipeline_status.json', status)
        analysis_args = [*common, '--evidence-git', str(repo),
            '--seal-commit', sealed_commit, '--population-observed', str(population),
            '--truth-root', str(truth), '--observed', str(observed)]
        phase(root, 'analysis', [PYTHON, '-B', str(code/'analyze_prospective.py'),
            *analysis_args, '--out', str(root/'analysis')], env, 10800)
        status['phase'] = 'independent_recount'
        write_json(root/'pipeline_status.json', status)
        phase(root, 'verification', [PYTHON, '-B', str(code/'verify_prospective.py'),
            *analysis_args, '--registration-commit', registered_commit,
            '--analysis', str(root/'analysis'),
            '--out', str(root/'verification')], env, 10800)
        check_executable_lock(project, registration)
        report = (root/'analysis/RESULTS.md').read_text()
        report = re.sub(r'(\]\()(?!(?:https?://|/|#))([^)]+)(\))',
                        lambda match: match[1]+'analysis/'+match[2]+match[3], report)
        report += ('\n## Independent recount and immutable registration\n\n'
            'Independent saved-artifact verification completed successfully; '
            'see [verification/receipt.json](verification/receipt.json).\n\n'
            f'Local registration commit: `{binding["git_commit"]}`. '
            f'Remote registration commit: `{registered_commit}`. '
            f'Observed seal commit: `{sealed_commit}`.\n\n'
            'This one-shot campaign has stopped. No optimization or rerun followed.\n')
        (root/'RESULTS.md').write_text(report)
        status['phase'] = 'artifact_inventory'
        write_json(root/'pipeline_status.json', status)
        inventory(root)
        status.update(status='completed', phase='finished', finished_epoch=time.time(),
                      exit_code=0, report=str(root/'RESULTS.md'))
        write_json(root/'pipeline_status.json', status)
    except BaseException as error:
        status.update(status='invalid', finished_epoch=time.time(), exit_code=1,
                      exception=repr(error), traceback=traceback.format_exc())
        write_json(root/'pipeline_status.json', status)
        (root/'RESULTS.md').write_text('# INVALID prospective campaign\n\n'
            f'The fixed campaign stopped in phase `{status["phase"]}`.\n\n'
            f'Error: `{error!r}`.\n\n'
            'No valid prospective reliability claim is made. Completed/failed '
            'artifacts remain unchanged. No automatic repair or rerun occurred. '
            'See pipeline_status.json and launch/<phase>/ logs.\n')
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', type=Path, default=PROJECT)
    run(parser.parse_args().project)
