"""Restricted structure fits; y/Phi only, no true gains or H input capability.

fit(y, Phi_I, I, arm, *, basis=None, incidence=None, sigma_terminal)
returns coefficients aligned ONLY to I and solver/rank diagnostics.
make_restricted_basis(system, geometry, I) is a separate geometry-oracle adapter.
"""
from __future__ import annotations
import numpy as np


def make_restricted_basis(system,geometry,I):
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import physical_cluster_weights
    if set(geometry)!={'taps','l_i','k_real'}:
        raise ValueError('geometry adapter accepts only taps/l_i/k_real, never gains')
    ids=_ids(I)
    return physical_cluster_weights(system,geometry)[ids].copy()


def _ids(I):
    ids=np.asarray(I)
    if ids.ndim!=1 or any(type(i) not in (int,np.int32,np.int64) for i in list(I)):
        raise ValueError('I must be integer atom IDs')
    ids=ids.astype(int)
    if len(set(ids.tolist()))!=len(ids) or np.any(ids<0) or np.any(ids>=515):
        raise ValueError('I must contain unique legal atoms')
    return ids


def _svd(a):
    u,s,vh=np.linalg.svd(a,full_matrices=False)
    threshold=np.finfo(float).eps*max(a.shape)*s[0] if len(s) else 0.
    rank=int(np.count_nonzero(s>threshold))
    return u,s,vh,rank,threshold


def _fit_ls(A,y):
    u,s,vh,r,tol=_svd(A)
    solution=vh[:r].conj().T@((u[:,:r].conj().T@y)/s[:r]) if r else np.zeros(A.shape[1],complex)
    return solution,{'rank':r,'singular_values':s.tolist(),'rank_threshold':float(tol)}


def sham_basis(basis,I):
    ids=_ids(I);L=np.asarray(basis,dtype=complex)
    if L.ndim!=2 or L.shape[0]!=len(ids) or not np.isfinite(L).all():raise ValueError('invalid restricted basis')
    phase=np.exp(2j*np.pi*np.mod((ids+1)*np.sqrt(2),1.))
    wrong=phase[:,None]*L
    u,s,_,r,tol=_svd(L);v,t,_,r_wrong,tol_wrong=_svd(wrong)
    distance=float(np.linalg.norm(u[:,:r]@u[:,:r].conj().T-v[:,:r_wrong]@v[:,:r_wrong].conj().T))
    return wrong,{'rank_link':r,'rank_sham':r_wrong,'singular_link':s.tolist(),
        'singular_sham':t.tolist(),'rank_threshold_link':float(tol),'rank_threshold_sham':float(tol_wrong),
        'projector_difference':distance,'sham_nontrivial':bool(distance>1e-10),
        'phase_rule':'exp(2pi*j*frac((atom_id+1)*sqrt(2)))',
        'incidence_preserved':bool(np.array_equal(L!=0,wrong!=0)),
        'group_sizes':np.count_nonzero(L,axis=0).tolist()}


def _group(A,y,groups,sigma):
    k=A.shape[1]
    norms=np.linalg.norm(A,axis=0)
    if np.any(norms<=0):raise ValueError('group fit requires nonzero response columns')
    lam=float(np.sqrt(sigma)*np.median(norms));rho=float(np.mean(norms**2))
    degree=np.zeros(k)
    for J in groups:degree[J]+=1
    if np.any(degree==0):raise ValueError('every active atom must belong to at least one group')
    gram=A.conj().T@A
    chol=np.linalg.cholesky(gram+rho*np.diag(degree))
    # scipy triangular solves reuse this single Cholesky factor for all iterations.
    from scipy.linalg import cho_solve
    rhs=A.conj().T@y
    g=np.zeros(k,complex);z=[np.zeros(len(J),complex) for J in groups]
    dual=[np.zeros(len(J),complex) for J in groups]
    total=sum(map(len,groups));weights=np.sqrt([len(J) for J in groups])
    converged=False
    for iteration in range(1,2001):
        right=rhs.copy()
        for J,v,u in zip(groups,z,dual):np.add.at(right,J,rho*(v-u))
        g=cho_solve((chol,True),right,check_finite=True)
        previous=[v.copy() for v in z]
        for j,J in enumerate(groups):
            v=g[J]+dual[j];norm=float(np.linalg.norm(v));threshold=lam*weights[j]/rho
            z[j]=max(0.,1-threshold/norm)*v if norm>0 else np.zeros_like(v)
            dual[j]+=g[J]-z[j]
        primal=float(np.sqrt(sum(np.linalg.norm(g[J]-v)**2 for J,v in zip(groups,z))))
        dual_sum=np.zeros(k,complex);u_sum=np.zeros(k,complex)
        for J,v,old,u in zip(groups,z,previous,dual):
            np.add.at(dual_sum,J,rho*(v-old));np.add.at(u_sum,J,rho*u)
        dual_res=float(np.linalg.norm(dual_sum))
        eps_pri=np.sqrt(total)*1e-7+1e-6*max(np.sqrt(sum(np.linalg.norm(g[J])**2 for J in groups)),
                                                        np.sqrt(sum(np.linalg.norm(v)**2 for v in z)))
        eps_dual=np.sqrt(k)*1e-7+1e-6*np.linalg.norm(u_sum)
        if not np.isfinite(g).all() or not np.isfinite([primal,dual_res]).all():
            raise FloatingPointError('nonfinite group ADMM state')
        if primal<=eps_pri and dual_res<=eps_dual:
            converged=True;break
    residual=y-A@g
    penalty=float(sum(w*np.linalg.norm(g[J]) for w,J in zip(weights,groups)))
    stationarity=float(np.linalg.norm(A.conj().T@(A@g-y)+u_sum))
    diagnostics={'iterations':iteration,'converged':converged,'lambda':lam,'rho':rho,
        'primal_residual':primal,'dual_residual':dual_res,'primal_tolerance':float(eps_pri),
        'dual_tolerance':float(eps_dual),'KKT_stationarity_residual':stationarity,
        'objective':float(.5*np.linalg.norm(residual)**2+lam*penalty),
        'penalty':penalty,'group_sizes':[len(J) for J in groups],
        'overlap_degree':degree.astype(int).tolist(),'cholesky_factorizations':1,
        'coefficient_dimension':k,'auxiliary_dimension':total,
        'auxiliary_semantics':'equality copies g[J]; not additional channel coefficients'}
    if not converged:raise RuntimeError(f'group ADMM did not converge within2000 iterations: {diagnostics}')
    return g,diagnostics


def fit(y,Phi_I,I,arm,*,basis=None,incidence=None,sigma_terminal):
    ids=_ids(I);A=np.asarray(Phi_I,dtype=complex);y=np.asarray(y,dtype=complex)
    if (y.ndim!=1 or A.shape!=(len(y),len(ids)) or not np.isfinite(A).all()
            or not np.isfinite(y).all() or np.ndim(sigma_terminal)!=0
            or np.iscomplexobj(sigma_terminal) or not np.isfinite(sigma_terminal) or sigma_terminal<=0):
        raise ValueError('invalid observed fit dimensions/variance/finite inputs')
    if arm not in ('free','group','link','sham'):raise ValueError('unknown restricted structure arm')
    if arm=='free' and (basis is not None or incidence is not None):raise ValueError('free fit accepts no geometry')
    L=None;groups=None
    if arm in ('link','sham'):
        L=np.asarray(basis,dtype=complex)
        if L.ndim!=2 or L.shape[0]!=len(ids) or not np.isfinite(L).all():raise ValueError('invalid L_I')
        if incidence is not None:raise ValueError('link/sham accept basis only')
    if arm=='group':
        if basis is not None:raise ValueError('group fit receives incidence only, not template weights')
        membership=np.asarray(incidence)
        if membership.ndim!=2 or membership.shape[0]!=len(ids) or membership.dtype!=bool:
            raise ValueError('incidence must be bool array (len(I),physical_slots)')
        groups=[np.flatnonzero(membership[:,j]) for j in range(membership.shape[1]) if membership[:,j].any()]
    diagnostic={'arm':arm,'atom_ids':ids.tolist(),'coefficient_dimension':len(ids)}
    if arm=='group':diagnostic['incidence']=membership.tolist()
    if not len(ids):
        return {'atom_ids':[],'coefficients':np.zeros(0,complex),
                'diagnostics':dict(diagnostic,zero_model=True,rank=0,iterations=0,converged=True,residual_squared=float(np.linalg.norm(y)**2),
                                   reason='empty common I; retained frame, no fit performed')}
    _,obs_s,_,obs_rank,obs_tol=_svd(A)
    diagnostic.update(observation_rank=obs_rank,observation_singular_values=obs_s.tolist(),
                      observation_rank_threshold=float(obs_tol),iterations=1,converged=True)
    if arm=='free':g,details=_fit_ls(A,y)
    elif arm=='group':g,details=_group(A,y,groups,float(sigma_terminal))
    else:
        original=L
        _,singular,_,rank,tol=_svd(original)
        diagnostic.update(basis_rank=rank,basis_singular_values=singular.tolist(),basis_rank_threshold=float(tol),
                          incidence=(original!=0).tolist(),group_sizes=np.count_nonzero(original,axis=0).tolist())
        if arm=='sham':
            L,sham=sham_basis(original,ids);diagnostic['sham']=sham
            if sham['rank_link']!=sham['rank_sham']:
                raise FloatingPointError('numerically uncertain sham/link rank parity')
        latent,details=_fit_ls(A@L,y);g=L@latent
        diagnostic['latent_slots']=L.shape[1]
    if not np.isfinite(g).all():raise FloatingPointError('nonfinite restricted coefficients')
    diagnostic.update(details,zero_model=False,residual_squared=float(np.linalg.norm(y-A@g)**2))
    return {'atom_ids':ids.tolist(),'coefficients':g,'diagnostics':diagnostic}
