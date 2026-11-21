"""Truth-bearing offline matrix error ledger, separate from estimators."""
import numpy as np

from afdm_sp_joint_unrolled.representation_ledger import merged_truth_ledger
from afdm_sp_joint_unrolled.v3_protocol import coherent_error_components


def initial_error(system, frame, coefficients, support):
    h=np.asarray(coefficients)
    kmax=system.k_max_cap; width=2*kmax+1
    ledger=merged_truth_ledger(frame['params'],kmax)
    truth={e['column']:complex(e['real'],e['imag']) for e in ledger['entries']
           if e['column'] is not None and e['delay']<=system.l_max_cap
           and complex(e['real'],e['imag'])!=0}
    S=set(support);T=set(truth)
    def reconstruct(values):
        ids=np.array(list(values),dtype=int)
        if not len(ids):return np.zeros_like(frame['H'])
        return system.gen_h_daft(np.array(list(values.values())),ids//width,ids%width-kmax)
    estimate=reconstruct({i:h[i] for i in support})
    parts=dict(missing=reconstruct({i:truth[i] for i in T-S}),
               gain=reconstruct({i:truth[i]-h[i] for i in T&S}),
               false=reconstruct({i:-h[i] for i in S-T}),
               representation=frame['H']-reconstruct(truth))
    error=coherent_error_components(frame['H'],parts)
    direct=float(np.linalg.norm(frame['H']-estimate)**2/np.linalg.norm(frame['H'])**2)
    if abs(error['total']-direct)>1e-8*max(1,direct):
        raise ValueError('channel error components do not reconstruct actual estimate')
    values=np.array([abs(v)**2 for v in truth.values()])
    weak={i for i,v in truth.items() if abs(v)**2<=np.median(values)} if len(values) else set()
    error.update(nmse=direct,K=len(S),true_count=len(T),missed_count=len(T-S),false_count=len(S-T),
                 weak_true_count=len(weak),weak_missed_count=len(weak-S),
                 weak_missing_energy=float(np.linalg.norm(reconstruct({i:truth[i] for i in weak-S}))**2/np.linalg.norm(frame['H'])**2),
                 threshold_sensitivity_true_ids=[i for i,v in truth.items() if abs(v)**2>=1e-4*values.sum()],
                 physical_paths=int(frame['params']['taps']),merged_entries=ledger['K_unique_merged'])
    return error
