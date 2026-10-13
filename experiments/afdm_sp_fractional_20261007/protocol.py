"""Private binding to the existing immutable mathematical-study recorder."""
import importlib.util
from pathlib import Path

from experiments.afdm_coherent_structure_20261006 import protocol as frozen
from experiments.afdm_phase_information_20261006.protocol import committed_project_sources
from experiments.afdm_shared_channel_20261004.common import dump

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent


def adapter():
    spec = importlib.util.spec_from_file_location('_sp_fractional_private_protocol', frozen.__file__)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT, module.PACKAGE = ROOT, PACKAGE
    return module


def run(stage, config, calculate, *, artifact_root):
    if (config['seed'] != 'none' or config['new_observations'] != 0 or
            config['new_geometry_probes'] != 3 or config['receiver_calls'] != 0 or config['decoder_calls'] != 0):
        raise ValueError('fixed deterministic three-geometry contract required')
    module = adapter()
    sources = [*module.project_sources(), *PACKAGE.glob('*.py')]
    identity = committed_project_sources(sources)

    def checked(output):
        dump(output/'committed_project_sources.json', identity)
        result = calculate(output)
        if (result['new_observations'] != 0 or result['geometry_probes'] != 3 or
                result['receiver_calls'] != 0 or result['decoder_calls'] != 0):
            raise RuntimeError('deterministic work accounting mismatch')
        return result

    return module.run(stage, config, sources, checked, artifact_root=artifact_root, wall_seconds=180)


def import_inventory():
    module = adapter()
    return dict(all_paths=[str(path.relative_to(ROOT)) for path in
                           sorted(set(module.project_sources()) | set(PACKAGE.glob('*.py')))])
