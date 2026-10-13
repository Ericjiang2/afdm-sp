"""Persist already-used actual integration components without creating nodes."""
import time

import numpy as np


def save_used_components(path,model,theta,step=None):
    key=(tuple(np.asarray(theta,float)),step)
    if key not in model._cache:
        raise ValueError('audit persistence requires an already-used cached component set')
    start=time.perf_counter(); used=model._cache[key]; branch=used['branch']
    payload=dict(public_theta=np.asarray(theta),nodes=model.nodes,quadrature_weights=model.weights,
        means=used['means'],logweights=used['logweights'],order=np.array(model.order),phases=np.array(model.phases),
        score_step=np.array(0. if step is None else step),has_derivatives=np.array(used['derivatives'] is not None),
        quadrature_mass_error=np.array(used['quadrature_mass_error']),
        gram=branch['geometry']['gram'],response=branch['geometry'][model.model],
        pdp=branch['pdp']['pdp'],pdp_weights=branch['pdp']['weights'])
    if used['derivatives'] is not None: payload['derivatives']=used['derivatives']
    np.savez_compressed(path,**payload)
    return dict(path=str(path.name),seconds=time.perf_counter()-start,bytes=path.stat().st_size,
                new_nodes=0,new_component_evaluations=0,scope='already-used cache only, raw independent-audit input')
