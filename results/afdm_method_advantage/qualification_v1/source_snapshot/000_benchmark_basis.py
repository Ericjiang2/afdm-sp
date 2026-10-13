"""One measured reliability permutation on actual frozen H; no receiver frame."""
import hashlib
import json
from pathlib import Path
import platform
import time
import numpy as np
from candidates import reliable_basis, ROOT

path=ROOT/'experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz'
h=np.load(path)['H']
llr=np.random.default_rng(915).normal(size=h.shape[1])  # synthetic reliability only
start=time.perf_counter()
b=reliable_basis(h,llr)
elapsed=time.perf_counter()-start
assert not np.any(h@b['anchor']%2)
# Exact binary generator verification, done after the timed basis construction.
assert not np.any(h@b['generator']%2)
out=dict(scope='single local GF2 basis construction on real parity matrix with synthetic LLR, not receiver throughput or FER', matrix_shape=list(h.shape), rank=int(b['rank']), information_dimension=len(b['free']), basis_seconds=elapsed, generator_bytes=b['generator'].nbytes, host=platform.platform(), numpy=np.__version__, input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), generator_legal=True)
(Path(__file__).parent/'basis_benchmark.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
