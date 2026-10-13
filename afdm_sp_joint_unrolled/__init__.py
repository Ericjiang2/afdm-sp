# Lazy package init — submodules are imported on demand.
# Eager imports here caused the full torch+scipy+matplotlib chain to load
# at package-import time, which hangs on Windows (DLL/CUDA init race).
# Users should import submodules directly, e.g.:
#   from afdm_sp_joint_unrolled.run_sp_unfolding import AFDMSystem
