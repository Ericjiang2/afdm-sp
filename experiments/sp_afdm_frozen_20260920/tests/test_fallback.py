"""Synthetic control-flow test only; no radio performance inference."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS'):os.environ[k]='1'
import sys,numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));import receiver as r
code={};called=[]
def ff(*args):return dict(seconds=0.,decision_timeline=[dict(ready_absolute=r.time.perf_counter(),decoded=np.array([0,1]))],channel_llr=np.array([1.,-1.]))
r.front=ff;r.extract_info=lambda c,d:d
r.finish=lambda *args:(_ for _ in ()).throw(FloatingPointError('synthetic'))
a,_=r.run({},None,None,code,{})
assert np.array_equal(a['decoded'],[0,1]) and a['events'][0]['stage']=='numerical_fallback'
r.pilot_front=lambda *args:dict(seconds=0.)
def nf(*args):
 if called:raise FloatingPointError('synthetic round2')
 called.append(1)
 return dict(decoded=np.array([0,1]),info_hat=np.array([0,1]),llr=np.array([1.,-1.]),seconds=.4,refit_seconds=.1,detector_seconds=.2,decoder_seconds=.1,instrumentation_seconds=0.,decoder_records=[dict(iterations=1,raw_app=np.array([1.,-1.]))],arrays=dict(final_check=np.array([0.,0.]),final_input=np.array([1.,-1.]),final_app=np.array([1.,-1.]),path_delays=np.array([0]),path_dopplers=np.array([0]),path_gains=np.array([1.])),events=[])
r.finish=nf
b,_=r.run_native({},None,{},dict(coded_rounds=2))
assert np.array_equal(b['decoded'],[0,1]) and b['events'][-1]['stage']=='numerical_fallback'
assert b['refit_seconds']==.1 and b['detector_seconds']==.2 and b['decoder_seconds']==.1
assert b['failed_round_seconds']>=0 and b['decoder_records'][0]['round']==0
failed=b['round_timings'][-1]
assert failed['status']=='numerical_failure'
assert all(failed[k] is None for k in ('refit_seconds','detector_seconds','decoder_seconds','instrumentation_seconds'))
print('PASS checkpoint/native completed-output fallback')
