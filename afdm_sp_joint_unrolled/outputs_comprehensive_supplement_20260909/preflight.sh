#!/usr/bin/env bash
set -u
RUN="/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909"
export TMPDIR="$RUN/tmp" TEMP="$RUN/tmp" TMP="$RUN/tmp"
export NUMBA_CACHE_DIR="$RUN/tmp/numba" MPLCONFIGDIR="$RUN/tmp/matplotlib" XDG_CACHE_HOME="$RUN/tmp/cache"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$RUN/source-v1"
PY=/home/guoyikun/.conda/envs/AFDM/bin/python
mkdir -p "$TMPDIR" "$NUMBA_CACHE_DIR" "$MPLCONFIGDIR" "$XDG_CACHE_HOME"
cd "$RUN/source-v1"
printf '%s\n' "$$" > "$RUN/preflight.pid"
date -u +%FT%TZ > "$RUN/preflight.started"
run_unit() {
 timeout --signal=TERM --kill-after=15s 600s "$PY" -m unittest -v afdm_sp_joint_unrolled.test_direction_data_receiver afdm_sp_joint_unrolled.test_direction_physical_receiver afdm_sp_joint_unrolled.test_direction_detector afdm_sp_joint_unrolled.test_direction_factorial afdm_sp_joint_unrolled.test_direction_structure > "$RUN/unit.log" 2>&1
 printf '%s\n' "$?" > "$RUN/unit.exit"
}
run_algebra() {
 timeout --signal=TERM --kill-after=15s 600s "$PY" -m afdm_sp_joint_unrolled.direction_structure_audit --physical-out "$RUN/physical-map.json" --geometry-out "$RUN/pilot-geometry.json" --cpu-seconds 450 > "$RUN/algebra.log" 2>&1
 printf '%s\n' "$?" > "$RUN/algebra.exit"
}
run_unit & U=$!
run_algebra & A=$!
printf '%s %s\n' "$U" "$A" > "$RUN/preflight.children"
wait "$U"
wait "$A"
date -u +%FT%TZ > "$RUN/preflight.finished"
"$PY" -c 'import json,pathlib; p=pathlib.Path("/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909"); s={k:int((p/(k+".exit")).read_text()) for k in ["unit","algebra"]}; (p/"preflight-status.json").write_text(json.dumps({"exit_codes":s,"passed":all(v==0 for v in s.values()),"scope":"source-bound unit and real generator algebra; no full receiver campaign"},indent=2)+"\n")'
