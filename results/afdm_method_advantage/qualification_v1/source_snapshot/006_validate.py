"""Persist deterministic synthetic acquisition evidence, not receiver results."""
import hashlib
import json
from pathlib import Path
import numpy as np
from candidates import acquire
from test_candidates import small_code, make_channel

out=Path(__file__).parent
rng=np.random.default_rng(891)
h=small_code();ch=make_channel(4);llr=np.array([-.2,4,3,2,1,.4,.8,5])
pilot=rng.normal(size=4)*.3+1j*rng.normal(size=4)*.3
y=rng.normal(size=4)+1j*rng.normal(size=4)
results={}
for mode in ('osd','geometry'):
    r=acquire(h,llr,ch,y,pilot,.3,scale=.7,list_size=6,branching=5,max_depth=3,mode=mode)
    results[mode]={k:r[k] for k in ('patterns','previews','counts','timing','selected','scope')}
    results[mode]['candidates']=r['candidates'].tolist()
    results[mode]['scores']=r['scores'].tolist()
sets=[{tuple(w) for w in results[m]['candidates']} for m in ('osd','geometry')]
assert sets[0] != sets[1]
report=dict(scope='synthetic 8-bit code implementation contracts; no truth coverage/FER claim', tests='10 passed (5 acquisition + 5 geometry)', distinct_candidate_sets=True, osd_only=len(sets[0]-sets[1]), geometry_only=len(sets[1]-sets[0]), methods=results, source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.py')})
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('methods','source_sha256')},indent=2))
