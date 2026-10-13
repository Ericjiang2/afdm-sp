"""Adapt existing immutable recorder without changing frozen earlier studies."""
import importlib.util
from pathlib import Path

from experiments.afdm_coherent_structure_20261006 import protocol as frozen
from experiments.afdm_phase_information_20261006.protocol import committed_project_sources
from experiments.afdm_shared_channel_20261004.common import dump

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent


def adapter():
    spec = importlib.util.spec_from_file_location('_acquisition_private_protocol', frozen.__file__)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT, module.PACKAGE = ROOT, PACKAGE
    return module


def run(stage, config, sources, calculate, *, artifact_root, wall_seconds):
    module = adapter()
    bound = [*module.project_sources(), *PACKAGE.glob('*.py'), *sources]
    identity = committed_project_sources(bound)

    def checked(output):
        dump(output/'committed_project_sources.json', identity)
        result = calculate(output)
        for key in ('new_observations', 'geometry_probes'):
            expected = config['new_geometry_probes' if key == 'geometry_probes' else key]
            if result[key] != expected:
                raise RuntimeError(f'incomplete {key} accounting')
        return result

    return module.run(stage, config, bound, checked, artifact_root=artifact_root, wall_seconds=wall_seconds)


def import_inventory():
    module = adapter()
    return dict(all_paths=[str(path.relative_to(ROOT)) for path in module.project_sources()])
