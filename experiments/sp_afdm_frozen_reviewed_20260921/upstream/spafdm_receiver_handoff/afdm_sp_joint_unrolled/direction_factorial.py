"""Eight-cell offline CSI factorial. Never a deployable receiver interface."""
from __future__ import annotations
import time

import numpy as np
import torch

from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.direction_receiver import terminal_decode
from afdm_sp_joint_unrolled.direction_detector import terminal as ep_terminal
from afdm_sp_joint_unrolled.supplement_detectors import terminal as catalog_terminal


def residual_ledger(snapshot,H_cancel,H_data):
    """Exact z-H_data*x residual; all three interference cross terms retained."""
    Htrue=snapshot['Htrue'];pilot=snapshot['pilot'];data=snapshot['data']
    terms={'pilot_channel_error':(Htrue-H_cancel)@pilot,
           'data_channel_error':(Htrue-H_data)@data,
           'thermal_noise':np.sqrt(snapshot['sigma2_thermal'])*snapshot['noise']}
    residual=snapshot['y']-H_cancel@pilot-H_data@data
    total=sum(terms.values())
    norm=max(1.,float(np.linalg.norm(snapshot['y'])))
    closure=float(np.linalg.norm(residual-total)/norm)
    if closure>1e-10:raise AssertionError('factorial residual identity failed')
    n=len(pilot)
    energies={k:float(np.vdot(v,v).real/n) for k,v in terms.items()}
    names=list(terms)
    cross={f'{a}:{b}':float(2*np.vdot(terms[a],terms[b]).real/n)
           for i,a in enumerate(names) for b in names[i+1:]}
    energy=float(np.vdot(residual,residual).real/n)
    energy_closure=energy-sum(energies.values())-sum(cross.values())
    if abs(energy_closure)>1e-10*max(1.,energy):
        raise AssertionError('factorial residual energy identity failed')
    return {'energies':energies,'cross_terms':cross,'residual_mean_square':energy,
            'relative_vector_closure':closure,'energy_closure':energy_closure,
            'tolerance':1e-10,'definition':'y-H_cancel*pilot-H_data*true_scaled_data'}


def run_factorial(snapshot,code,*,device='cpu',before_call,on_cell=None,detectors=('BP','EP10')):
    """Each callback fires before one actual terminal attempt, including failures.

    Truth is confined to this diagnostic container. The detector receives only
    cancelled y, selected H, fixed variance, constellation and known code.
    Returns raw small outputs for evidence writers; does not publish files.
    """
    if not callable(before_call):raise ValueError('explicit budget before_call callback required')
    if on_cell is not None and not callable(on_cell):raise ValueError('on_cell must be callable')
    required={'Hhat','Htrue','y','pilot','data','noise','sigma2_thermal',
              'constellation','sigma2_terminal','info','coded'}
    if not required<=set(snapshot):raise ValueError('incomplete terminal snapshot')
    s={k:np.array(snapshot[k],copy=True) for k in required}
    n=len(s['y'])
    if (s['y'].shape!=(n,) or s['Hhat'].shape!=(n,n) or s['Htrue'].shape!=(n,n)
            or any(s[k].shape!=(n,) for k in ('pilot','data','noise'))
            or s['constellation'].shape!=(4,) or s['info'].shape!=(code['k'],)
            or s['coded'].shape!=(code['n'],) or code['n']!=2*n
            or any(not np.isfinite(v).all() for v in s.values())):
        raise ValueError('invalid factorial snapshot dimensions/finite values')
    for key in ('sigma2_thermal','sigma2_terminal'):
        if s[key].ndim!=0 or np.iscomplexobj(s[key]) or s[key]<=0:
            raise ValueError('positive scalar noise variances required')
    if any(np.any((s[k]!=0)&(s[k]!=1)) for k in ('coded','info')):
        raise ValueError('binary truth labels required for offline evaluation')
    # Validate the stored physical observation before spending a detector call.
    residual_ledger(s,s['Hhat'],s['Hhat'])
    sigma=float(s['sigma2_terminal'])
    dev=torch.device(device)
    if dev.type=='cuda' and not torch.cuda.is_available():raise ValueError('requested CUDA unavailable')
    if not isinstance(detectors,tuple) or len(detectors)!=2 or len(set(detectors))!=2:
        raise ValueError('H factorial requires two distinct detector ids')
    cells=[]
    for cancel_source in ('estimated','true'):
        for data_source in ('estimated','true'):
            for detector in detectors:
                cell_id=f'cancel_{cancel_source}__data_{data_source}__{detector}'
                Hc=s['Hhat'] if cancel_source=='estimated' else s['Htrue']
                Hd=s['Hhat'] if data_source=='estimated' else s['Htrue']
                # Fresh cancellation, H and detector state for every cell.
                z=(s['y']-Hc@s['pilot']).copy()
                channel=Hd.copy()
                Hc_hash=array_hash(Hc);Hd_hash=array_hash(channel)
                metadata={'cell_id':cell_id,'cancel_source':cancel_source,'data_source':data_source,
                          'detector':detector,'sigma2_terminal':sigma,'call_type':'terminal',
                          'truth_access_level':'CSI_oracle' if 'true' in (cancel_source,data_source) else 'none',
                          'diagnostic_only':True}
                before_call(dict(metadata))
                if dev.type=='cuda':
                    torch.cuda.synchronize(dev);torch.cuda.reset_peak_memory_stats(dev)
                wall=time.perf_counter();cpu=time.process_time()
                if detector=='BP':
                    result=terminal_decode(z,channel,sigma,s['constellation'].copy(),code,device=dev,audit=True)
                    diagnostics={'detector_id':'existing-BP20','graphs':result['graphs'],
                                 'moment_semantics':'existing Gaussian BP aggregate'}
                    hard=result['x_hard']
                    covariance_source={'kind':'BP scalar-noise graph built fresh','H_sha256':Hd_hash}
                elif detector=='EP10':
                    result=ep_terminal(z,channel,sigma,s['constellation'].copy(),code,device=dev)
                    diagnostics=dict(result['diagnostics'],graph_status='dense real EP; no sparse BP graph',
                                     Hdata_nonzero_entries=int(np.count_nonzero(channel)))
                    hard=result['hard']
                    covariance_source={'kind':'EP fresh real Gaussian precision and dense covariance diagonal',
                                       'H_sha256':Hd_hash}
                else:
                    result=catalog_terminal(z,channel,sigma,s['constellation'].copy(),code,detector,device=str(dev))
                    diagnostics=dict(result['diagnostics'],detector_id=detector)
                    hard=result['x_hard']
                    covariance_source={'kind':'catalog detector graph built fresh','H_sha256':Hd_hash,
                                       'detector_id':detector}
                if dev.type=='cuda':torch.cuda.synchronize(dev)
                seconds=time.perf_counter()-wall;cpu_seconds=time.process_time()-cpu
                peak=int(torch.cuda.max_memory_allocated(dev)) if dev.type=='cuda' else 0
                if array_hash(z)!=array_hash(s['y']-Hc@s['pilot']) or array_hash(channel)!=Hd_hash:
                    raise AssertionError('detector mutated diagnostic observation/channel')
                error=int(np.count_nonzero(result['info_hat']!=s['info']))
                cells.append(dict(metadata,seconds=seconds,CPU_seconds=cpu_seconds,peak_gpu_bytes=peak,
                    H_cancel_source={'source':cancel_source,'sha256':Hc_hash},
                    H_data_source={'source':data_source,'sha256':Hd_hash},H_cov_source=covariance_source,
                    sigma_source='common frozen snapshot sigma2_terminal; not reestimated per cell',
                    z_hash=array_hash(z),residual=residual_ledger(s,Hc,Hd),
                    mu=result['mu'].copy(),var=result['var'].copy(),llr=result['llr'].copy(),
                    decoded=result['decoded'].copy(),info_hat=result['info_hat'].copy(),hard=hard.copy(),
                    info_errors=error,FER=int(error>0),decode_ok=result['decode_ok'],
                    diagnostics=diagnostics,support_status='not reestimated; no oracle support claim',
                    llr_sha256=array_hash(result['llr']),decoded_sha256=array_hash(result['decoded'])))
                if on_cell is not None:
                    on_cell(cells[-1])
    normal={'status':'not_available_in_snapshot'}
    if 'decoded' in snapshot:
        decoded=np.asarray(snapshot['decoded'])
        if decoded.shape!=(code['n'],) or np.any((decoded!=0)&(decoded!=1)):
            raise ValueError('invalid normal decoded snapshot')
        baseline=cells[0]
        errors=int(np.count_nonzero(decoded[code['free_cols']]!=s['info']))
        normal={'status':'recorded_separately','decoded':decoded.copy(),'decoded_sha256':array_hash(decoded),
                'info_errors':errors,'FER':int(errors>0),
                'comparison_cell':baseline['cell_id'],
                'decoded_equal':bool(np.array_equal(decoded,baseline['decoded'])),
                'differing_bits':int(np.count_nonzero(decoded!=baseline['decoded'])),
                'interpretation':'Replay comparison measured, not assumed identical; native GPU BP may differ in last bits.'}
    return {'cells':cells,'normal_output':normal,'fixed_sigma2_terminal':sigma,
            'calls_attempted':8,'scope':'offline factorial only; no cell is registered as a deployable candidate'}
