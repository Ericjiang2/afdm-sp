"""Private immutable recorder adaptation; every project Python input is committed."""
import hashlib
import importlib.util
from pathlib import Path
import subprocess

from experiments.afdm_coherent_structure_20261006 import protocol as frozen
from experiments.afdm_shared_channel_20261004.common import dump

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent


def adapter():
    spec = importlib.util.spec_from_file_location('_phase_private_protocol', frozen.__file__)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT, module.PACKAGE = ROOT, PACKAGE

    def record(path, value):
        if path.name == 'registration.json':
            value = dict(value, schema='phase-information-pilot-attempt/1',
                         evidence_level='exploratory paired single-path CFO pilot; not CONF or production')
        dump(path, value)

    module.dump = record
    return module


def committed_project_sources(paths):
    """Extend the reused recorder's task-only HEAD gate to all project helpers."""
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()
    inventory = {}
    for path in sorted({Path(value).resolve() for value in paths}):
        if not path.is_relative_to(ROOT) or path.suffix != '.py':
            continue
        relative = str(path.relative_to(ROOT))
        tracked = subprocess.run(['git', 'ls-files', '--full-name', '--', relative], cwd=ROOT,
                                 check=True, capture_output=True, text=True).stdout.strip()
        if not tracked:
            raise ValueError(f'uncommitted project source: {relative}')
        committed = subprocess.run(['git', 'show', f'{head}:{tracked}'], cwd=ROOT, check=True,
                                   capture_output=True).stdout
        if committed != path.read_bytes():
            raise ValueError(f'project source differs from HEAD: {relative}')
        inventory[relative] = hashlib.sha256(committed).hexdigest()
    return dict(head=head, project_python_sha256=inventory)


def run(stage, config, sources, calculate, *, artifact_root, wall_seconds=300):
    if config['new_observations'] != 7680 or config['new_geometry_probes'] != 0:
        raise ValueError('pilot requires exactly 7680 vectors and zero geometry probes')
    module = adapter()
    bound = [*module.project_sources(), *PACKAGE.glob('*.py'), *sources]
    identity = committed_project_sources(bound)

    def checked(output):
        dump(output/'committed_project_sources.json', identity)
        result = calculate(output)
        if result['new_observations'] != config['new_observations']:
            raise RuntimeError('pilot observation accounting is incomplete')
        return result

    return module.run(stage, config, bound, checked, artifact_root=artifact_root,
                      wall_seconds=wall_seconds)


def import_inventory():
    module = adapter()
    inventory = module.module_source_inventory()
    return dict(all_paths=[str(path.relative_to(ROOT)) for path in module.project_sources()],
                excluded_virtual_modules=inventory['excluded'])
