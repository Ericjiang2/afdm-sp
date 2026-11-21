#!/usr/bin/env bash
# idea-funnel l02 paired injection: 10 single-thread shards of l2_l02_inject.py (driver_c1e with fixed (I_A, I_R) pairs)
export CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/data/guoyikun/tmp XDG_CACHE_HOME=/data/guoyikun/tmp/cache_headroom MPLCONFIGDIR=/data/guoyikun/tmp/cache_headroom TORCH_HOME=/data/guoyikun/tmp/cache_headroom
PY=/home/guoyikun/.conda/envs/AFDM/bin/python; D=/data/guoyikun/00inbox/AFDM-channel-estimation/ideas/l2; OUT=$D/out12
cd $D
for i in 0 1 2 3 4 5 6 7 8 9; do
  $PY -B $D/l2_l02_inject.py --mode generate --out $OUT --Ls 28 --snr-list 6.5 --Ir 0.11,0.12,0.21,0.22 --frames 100 --shard $i --nshard 10 > $OUT/logs/shard_$i.log 2>&1 &
done
wait
$PY -B $D/l2_l02_inject.py --mode merge --out $OUT --Ls 28 --snr-list 6.5 --Ir 0.11,0.12,0.21,0.22 --frames 100 > $OUT/logs/merge.log 2>&1
echo DONE > $OUT/logs/done.txt
