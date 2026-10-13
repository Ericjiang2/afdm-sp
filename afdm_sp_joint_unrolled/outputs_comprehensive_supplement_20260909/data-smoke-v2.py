from pathlib import Path
import hashlib,json,time
import numpy as np
from afdm_sp_joint_unrolled.e1_ldpc import build_code
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
from afdm_sp_joint_unrolled.supplement_data import SupplementData
from afdm_sp_joint_unrolled.direction_data import campaign_rng as old_rng
from afdm_sp_joint_unrolled.supplement_data import campaign_rng as new_rng
base=Path(__file__).resolve().parent
started=time.monotonic()
code=build_code(cache_dir=base/'tmp')
system=_make_config_a(1024,2.,8,10.,4.)
data=SupplementData(base/'data-protocol.json',code)
frames=[data.make_frame(system,'engineering',0,s) for s in [7,8,9]]
for name in ['H','data','noise','info','coded']:
 for frame in frames[1:]:
  np.testing.assert_array_equal(frames[0]._truth[name],frame._truth[name])
assert not np.array_equal(old_rng('engineering',0,'noise').integers(0,2**31,16),new_rng('engineering',0,'noise').integers(0,2**31,16))
for f in frames:
 np.testing.assert_allclose(f.observed['y'],f._truth['H']@(f.observed['pilot']+f._truth['data'])+np.sqrt(f.observed['sigma2'])*f._truth['noise'],rtol=1e-12,atol=1e-12)
result={'status':'passed','evidence_kind':'real_N1024_G0_LDPC_generation_and_cross_SNR_pairing','frames_generated':3,'full_receivers_run':0,'wall_seconds':time.monotonic()-started,'protocol_sha256':data.protocol_sha256,'source_manifest':data.sources,'metadata':[f.metadata for f in frames],'scope':'engineering split only; no confirmation/holdout opened; no FER claim','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
with (base/'data-smoke-v2.json').open('x') as h:json.dump(result,h,indent=2,allow_nan=False)
print(json.dumps({'status':'passed','frames':3,'wall_seconds':result['wall_seconds']}))
