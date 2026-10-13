# source me: single-thread CPU env (same exports as launch.sh)
export CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/data/guoyikun/tmp XDG_CACHE_HOME=/data/guoyikun/tmp/cache_headroom
export MPLCONFIGDIR=/data/guoyikun/tmp/cache_headroom TORCH_HOME=/data/guoyikun/tmp/cache_headroom
