"""Private reuse of the existing immutable admission/attempt recorder."""
import importlib.util
import json
from pathlib import Path
import resource
import sys

from experiments.afdm_shared_channel_20261004.common import dump

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def module_source_inventory():
    """Separate actual import files from virtual module labels before resolving."""
    paths, excluded = set(), []
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename)
            if not path.is_absolute():
                # torch.ops/classes use virtual labels, not paths in the CWD.
                excluded.append(dict(module=name, filename=filename,
                                     reason='relative or virtual module label; not an absolute source path'))
                continue
            path = path.resolve()
            if path.is_relative_to(ROOT) and path.suffix == '.py':
                if not path.is_file():
                    raise FileNotFoundError(f'loaded project source is missing: {name}: {path}')
                paths.add(path)
    return dict(paths=sorted(paths), excluded=excluded)


def project_sources():
    """Bind the actually preloaded project dependency graph, including upstream."""
    return sorted(set(module_source_inventory()['paths']) |
                  {ROOT/'experiments/afdm_efficient_information/protocol.py',
                   ROOT/'experiments/afdm_higher_order_information/protocol.py',
                   PACKAGE/'thread_binding.py'})


def run(stage, config, sources, calculate, *, artifact_root, wall_seconds=1200):
    root = Path(artifact_root)
    if not root.is_absolute():
        raise ValueError('artifact root must be absolute')
    root = root.resolve()
    adapter = _load('_coherent_private_admission', ROOT/'experiments/afdm_efficient_information/protocol.py')
    adapter.ROOT, adapter.PACKAGE = ROOT, PACKAGE
    adapter.ARTIFACT, adapter.MISSION = root/'execution', root/'control'

    def recorder():
        module = _load('_coherent_private_recorder', ROOT/'experiments/afdm_higher_order_information/protocol.py')
        module.ROOT, module.PACKAGE = ROOT, PACKAGE
        module.ARTIFACT, module.MISSION = adapter.ARTIFACT, adapter.MISSION
        module.BINDING = PACKAGE/'thread_binding.py'
        return module

    adapter._recorder = recorder

    def record(path, value):
        if path.name == 'registration.json':
            value = dict(value, schema='coherent-structure-attempt/1',
                         evidence_level='registered mathematical/development study; no receiver or decoder',
                         deterministic_geometry_reservation=config['new_geometry_probes'],
                         excluded_virtual_modules=module_source_inventory()['excluded'])
        dump(path, value)

    adapter.dump = record
    contract = json.loads((adapter.MISSION/'run_contract.json').read_text())
    probes = config['new_geometry_probes']
    if isinstance(probes, bool) or not isinstance(probes, int) or probes < 0:
        raise ValueError('nonnegative integer geometry reservation required')
    reserved = sum(json.loads(p.read_text())['config'].get('new_geometry_probes', 0)
                   for p in adapter.ARTIFACT.glob('*/registration.json'))
    if reserved+probes > contract['max_geometry_probes']:
        raise ValueError('geometry probe reservation exceeded')

    def checked(output):
        result = calculate(output)
        if result['new_observations'] > config['new_observations'] or result['geometry_probes'] > probes:
            raise RuntimeError('actual work exceeded reservation')
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        peak *= 1 if sys.platform == 'darwin' else 1024
        if peak > contract['max_process_memory_bytes']:
            raise RuntimeError('whole-process peak memory exceeded contract')
        return result

    return adapter.run(stage, config, [*project_sources(), *sources], checked, wall_seconds)
