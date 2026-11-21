"""Synthetic interface test only; no radio evidence or timing claim."""
import os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=Path(os.environ.get('SPAFDM_BASELINE_ROOT','/mnt/data/prior_frozen/SP_AFDM_Design_Freeze'))
sys.path[:0]=[str(ROOT/'src'),str(BASE/'src'),str(BASE)]
import numpy as np
from types import SimpleNamespace
import native_twofft as m
calls=[0]; checkpoints=[]
m.pilot_front=lambda *_:dict(mu=np.zeros(1024,complex),v=np.full(1024,.5),prior=np.zeros(2048),delays=np.array([0]),dopplers=np.array([0.]),gains=np.array([1.+0j]))
c=SimpleNamespace(delays=np.array([0]),dopplers=np.array([0.]),gains=np.array([1.+0j]))
m.time_refine=lambda *a,**k:(c,dict(history=[1.],evaluations=1,fft_count=3))
def fake_infer(*a,**k):
 calls[0]+=1
 if calls[0]==2:raise FloatingPointError('synthetic second-round failure')
 return dict(extrinsic=np.zeros(2048),gains=np.array([1.+0j]),gain_variance=np.array([.1]),mu=np.zeros(1024,complex),variance=np.full(1024,.5),fft_count=41)
m.scalar_joint=fake_infer
m.decoder_messages=lambda *a,**k:dict(raw_check_extrinsic=np.zeros(2048),raw_app=np.zeros(2048),incoming_llr=np.zeros(2048),decoded=np.zeros(2048,dtype=np.int8),iterations=1)
system=SimpleNamespace(rho=.5,c1=.004,c2=.0000002)
try:
 m.receive(dict(y=np.zeros(1024,complex),pilot=np.ones(1024,complex),sigma2=.1),system,None,checkpoint_sink=lambda e,b:checkpoints.append((e,b)))
 raise AssertionError('failure not propagated')
except FloatingPointError as e:
 assert str(e)=='synthetic second-round failure'
assert calls[0]==2 and len(checkpoints)==1
assert checkpoints[0][0]['round']==0 and checkpoints[0][0]['ready']>=0
assert checkpoints[0][1].shape==(2048,)
print('PASS synthetic checkpoint retained; second-round failure propagated; zero radio samples')
