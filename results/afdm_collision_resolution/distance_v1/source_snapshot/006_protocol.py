"""Task paths around a private instance of the frozen admission implementation."""
import importlib.util
from pathlib import Path

from experiments.afdm_shared_channel_20261004.common import dump, hashes

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent
MISSION = ROOT/'.mission/20261005_15-21-29-afdm-collision-resolution'
ARTIFACT = ROOT/'results/afdm_collision_resolution'
IMPLEMENTATION = ROOT/'experiments/afdm_efficient_information/protocol.py'


def _engine():
    spec = importlib.util.spec_from_file_location('_collision_private_admission', IMPLEMENTATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT, module.PACKAGE = ROOT, PACKAGE
    module.MISSION, module.ARTIFACT = MISSION, ARTIFACT
    return module


def committed_sources(paths):
    return _engine().committed_sources(paths)


def run(stage, config, sources, calculate, wall_seconds=600):
    engine = _engine()
    engine.committed_sources = committed_sources
    return engine.run(stage, config, [Path(__file__), *sources], calculate, wall_seconds)
