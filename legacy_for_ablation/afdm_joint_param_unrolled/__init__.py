# Lazy package init — submodules are imported on demand.
# Eager imports here caused the full torch+scipy+matplotlib chain to load
# at package-import time, which hangs on Windows (DLL/CUDA init race).
# Users should import submodules directly, e.g.:
#   from afdm_joint_param_unrolled.afdm_joint_param import build_param_joint_model
