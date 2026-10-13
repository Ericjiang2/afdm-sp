"""Reuse the frozen physical generator through a split-specific module instance."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def physical_module(source, split):
    if type(split) is not int or split not in (0,1,2,3):
        raise ValueError("registered A/B seed split required")
    spec = spec_from_file_location("ab_physical_split_"+str(split),Path(source))
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    # The old file and old module instance remain unchanged. Both sources are
    # bound by the runner; generated metadata exposes this exact new namespace.
    module.SEED_PREFIX = (20260914,125851,split)
    return module
