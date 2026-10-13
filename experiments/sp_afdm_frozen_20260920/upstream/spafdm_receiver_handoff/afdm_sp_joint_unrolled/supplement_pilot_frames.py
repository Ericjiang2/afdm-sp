"""Generator-side pilot substitution with shared exogenous block and power audit."""
import copy
from types import MappingProxyType
import numpy as np
from .direction_data import CampaignFrame,validate_observed
from .budgeted_support_diagnostics import array_hash
from .supplement_pilots import paired_observations,waveform_metrics


def pilot_frames(frame,pilots,*,c1,c2,rho=.5,prefix_length=102,papr_limit_db=12.,peak_power_limit=16.,
                 preserve_original_p0=False):
    """Truth access is confined to constructing observations, never receiver kwargs."""
    scenario=frame.metadata.get('scenario')
    # Old nominal snapshots predate explicit generator metadata. Counterexample
    # frames must name their generator; a scenario label alone is insufficient.
    generator=frame.metadata.get('generator','truncated_daft' if scenario=='G0' else None)
    if scenario not in ('G0','integer','overlap') or generator!='truncated_daft':
        raise ValueError('pilot adapter requires a registered truncated-DAFT scene')
    if type(preserve_original_p0) is not bool:
        raise ValueError('preserve_original_p0 must be boolean')
    truth=frame._truth
    for k in ('H','data','noise','info','coded'):
        if array_hash(truth[k])!=frame.metadata['input_hashes'][k]:raise ValueError('common external block hash changed')
    for k in ('y','pilot'):
        if array_hash(frame.observed[k])!=frame.metadata['input_hashes'][k]:raise ValueError('original observation changed')
    expected=np.sqrt(rho)*pilots['p0']
    if not np.allclose(expected,frame.observed['pilot'],rtol=1e-12,atol=1e-12):raise ValueError('p0 differs from frozen original')
    observations,common=paired_observations(truth['H'],truth['data'],truth['noise'],pilots,rho=rho,sigma2=float(frame.observed['sigma2']))
    np.testing.assert_allclose(observations['p0']['y'],frame.observed['y'],rtol=1e-12,atol=1e-12,
                               err_msg='p0 pairing reconstruction differs from source')
    if preserve_original_p0:
        observations['p0']={k:np.array(v,copy=True) for k,v in frame.observed.items()}
    frames={}
    for name,observed in observations.items():
        observed['sigma2']=np.asarray(observed['sigma2']);observed['constellation']=np.array(frame.observed['constellation'],copy=True)
        validate_observed(observed,len(truth['data']))
        for v in observed.values():v.flags.writeable=False
        _,_,power=waveform_metrics(pilots[name],truth['data'],rho=rho,c1=c1,c2=c2,prefix_length=prefix_length,
                                  papr_limit_db=papr_limit_db,peak_power_limit=peak_power_limit)
        metadata=copy.deepcopy(frame.metadata)
        metadata.update(pilot_id=name,pilot_common=common,power=power,original_y_sha256=frame.metadata['input_hashes']['y'],
            pilot_reconstruction='Hp+(Hx+noise); p0 agrees numerically, not asserted bit-exact to original H(p+x)+noise')
        if preserve_original_p0 and name=='p0':
            metadata['pilot_reconstruction']='original p0 observations retained after numerical reconstruction check'
        metadata['input_hashes'].update(y=array_hash(observed['y']),pilot=array_hash(observed['pilot']))
        frames[name]=CampaignFrame(MappingProxyType(observed),metadata,truth)
    return frames
