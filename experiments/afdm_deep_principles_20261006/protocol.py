"""Private adapter over the existing source/budget/failure admission chain."""
import importlib.util
from pathlib import Path

from experiments.afdm_coherent_structure_20261006 import protocol as frozen
from experiments.afdm_shared_channel_20261004.common import dump

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent


def adapter():
    spec = importlib.util.spec_from_file_location('_deep_private_protocol', frozen.__file__)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT, module.PACKAGE = ROOT, PACKAGE

    def record(path, value):
        if path.name == 'registration.json':
            value = dict(value, schema='deep-principles-attempt/1',
                         evidence_level='registered deterministic mathematical checks; zero random observations')
        dump(path, value)

    module.dump = record
    return module


def run(stage, config, sources, calculate, *, artifact_root, wall_seconds=600):
    if config['new_observations'] != 0:
        raise ValueError('deep-principles stages authorize zero observations')
    return adapter().run(stage, config, [*PACKAGE.glob('*.py'), *sources], calculate,
                         artifact_root=artifact_root, wall_seconds=wall_seconds)


def import_inventory():
    module = adapter()
    inventory = module.module_source_inventory()
    return dict(paths=[str(path) for path in module.project_sources()],
                excluded_virtual_modules=inventory['excluded'])
