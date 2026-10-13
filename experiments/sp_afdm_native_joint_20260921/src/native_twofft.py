"""Complete observed-input native pipeline using an existing frozen pilot initializer.
No truth accepted. The initial 515-column dictionary is NOT charged as O(NP) memory.
No I1 outer loop is used. Code construction is an amortized static operation.
"""
import time
import numpy as np
from receiver import pilot_front,decoder_messages
from messages import moments
from twofft import time_refine,scalar_joint

def receive(observation,system,code,rounds=2,iterations=20,ce_mode='soft',gain_mode='joint',checkpoint_sink=None,record_states=False):
    if len(observation['y'])!=1024 or system.rho!=.5:raise ValueError('frozen native interface: N=1024, rho=0.5')
    if rounds<1:raise ValueError('at least one coded round required')
    if checkpoint_sink is not None and not callable(checkpoint_sink):raise TypeError('checkpoint_sink must be callable')
    if set(observation)-{'y','pilot','sigma2'}:raise ValueError('Only observed inputs are accepted')
    st=time.perf_counter();s=pilot_front(observation,system,code);tp=time.perf_counter()-st
    arrays={};events=[]
    for r in range(rounds):
        t=time.perf_counter()
        c,detail=time_refine(observation['y'],observation['pilot'],s['mu'],s['v'],s['delays'],s['dopplers'],s['gains'],system.c1,system.c2,observation['sigma2'],mode=ce_mode,max_paths=8,rounds=2)
        tc=time.perf_counter()-t;t=time.perf_counter()
        o=scalar_joint(observation['y'],observation['pilot'],c,observation['sigma2'],pd=1-system.rho,prior=s['prior'],iterations=iterations,gain_mode=gain_mode,record_states=record_states)
        ti=time.perf_counter()-t;t=time.perf_counter()
        dec=decoder_messages(code,np.clip(o['extrinsic'],-20,20),maxiter=50)
        td=time.perf_counter()-t;s['prior']=np.clip(dec['raw_check_extrinsic'],-20,20)
        s['mu'],s['v'],_=moments(np.clip(dec['raw_app'],-20,20),1-system.rho)
        s['delays']=c.delays;s['dopplers']=c.dopplers;s['gains']=o['gains']
        events.append(dict(round=r,ce=tc,inference=ti,decoder=td,ready=time.perf_counter()-st,decoder_iterations=int(dec['iterations']),inference_iterations=iterations,ce_evaluations=detail['evaluations'],inference_fft_count=o['fft_count'],ce_fft_count=detail['fft_count']))
        round_arrays={'decoded':dec['decoded'],'input_llr':dec['incoming_llr'],'app':dec['raw_app'],
                      'check':dec['raw_check_extrinsic'],'delays':c.delays,'dopplers':c.dopplers,
                      'gains':o['gains'],'gain_variance':o['gain_variance'],'ce_gains':c.gains,
                      'mu':o['mu'],'variance':o['variance'],'ce_history':np.array(detail['history']),
                      'ce_gamma':detail['gamma'],'inference_trace':o['trace']}
        if record_states:round_arrays['inference_states']=o['states']
        arrays.update({f'r{r}_{k}':v for k,v in round_arrays.items()})
        # Optional caller-owned checkpoint capture survives a later numerical failure.
        # It must not change decisions; any callback cost remains in complete time.
        if checkpoint_sink is not None:
            checkpoint_sink(dict(events[-1],snapshot=round_arrays), dec['decoded'].copy())
    return dec,arrays,dict(seconds=time.perf_counter()-st,pilot_seconds=tp,events=events)
