"""Eight new observed-only soft references; historical BP/EP10 remain unchanged."""
from __future__ import annotations
import copy
import math
import time
import numpy as np
import torch
from .budgeted_support_diagnostics import array_hash
from .e1_ldpc import decode_llr,demap_llr,extract_info
from .mp_detect_bp_torch import mp_detect_bp_torch

CONST=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j])
QUALIFICATION=dict(relative_llr=1e-3,relative_mean=1e-4,fixed_point=1e-5,linear_residual=1e-8)


def catalogue():
    return [dict(id=f'{family}-{iterations}-d{damping:g}',family=family,iterations=iterations,
                 damping=damping,llr_clip=20.,fixed_point_tolerance=1e-5,
                 doubled_iterations=2*iterations)
            for family,dampings in [('stable-EP',(.25,.5)),('QPSK-MF',(.5,1.))]
            for iterations in (20,40) for damping in dampings]


def additional_catalogue():
    return [dict(id=f'BP{iterations}',family='BP',iterations=iterations,
                 damping=.5,threshold=1e-4,llr_clip=20.,fixed_point_tolerance=1e-5,
                 doubled_iterations=2*iterations)
            for iterations in (80,160)]


def recipe(identifier):
    rows=[r for r in catalogue()+additional_catalogue() if r['id']==identifier]
    if len(rows)!=1:raise ValueError('unknown preregistered detector')
    return rows[0]


def inputs(y,H,sigma,constellation,device):
    y,H,c=[np.asarray(a) for a in (y,H,constellation)]
    if (y.ndim!=1 or not 1<=len(y)<=1024 or H.shape!=(len(y),len(y)) or c.shape!=(4,) or
            any(not np.iscomplexobj(a) or not np.isfinite(a).all() for a in (y,H,c)) or
            not np.allclose(c,CONST,rtol=1e-12,atol=1e-12)):
        raise ValueError('finite complex y/H and scaled QPSK in fixed order required')
    s=np.asarray(sigma)
    if s.ndim!=0 or np.iscomplexobj(s) or not np.isfinite(s) or s<=0:
        raise ValueError('sigma is positive total complex variance')
    dev=torch.device(device)
    if dev.type not in ('cpu','cuda') or (dev.type=='cuda' and not torch.cuda.is_available()):
        raise ValueError('requested detector device unavailable; no fallback')
    if dev.type=='cuda' and dev.index is None:
        dev=torch.device('cuda',torch.cuda.current_device())
    return y,H,c,float(s),dev


def _ep(y,H,sigma,r,iterations):
    n=len(y);a=.5
    h=torch.cat((torch.cat((H.real,-H.imag),1),torch.cat((H.imag,H.real),1)),0)
    yr=torch.cat((y.real,y.imag));gram=h.T@h/(sigma/2);natural=h.T@yr/(sigma/2)
    lam=torch.full((2*n,),4.,dtype=torch.float64,device=y.device);gamma=torch.zeros_like(lam)
    trace=[]
    for iteration in range(iterations):
        precision=gram+torch.diag(lam);rhs=natural+gamma
        factor=torch.linalg.cholesky(precision)
        gaussian=torch.cholesky_solve(rhs[:,None],factor).squeeze(1)
        diagonal=torch.cholesky_inverse(factor).diagonal()
        if not torch.isfinite(diagonal).all() or bool((diagonal<=0).any()):
            raise FloatingPointError('invalid EP marginal variance')
        cavity_precision=1/diagonal-lam;cavity_eta=gaussian/diagonal-gamma
        if bool((cavity_precision < -1e-8).any()):
            raise FloatingPointError('negative EP cavity precision beyond declared tolerance')
        raw=2*a*cavity_eta
        mean=a*torch.tanh(raw/2);variance=a*a-mean.square()
        floor=1e-10*a*a;working=variance.clamp_min(floor)
        proposed_lam=1/working-cavity_precision;proposed_gamma=mean/working-cavity_eta
        if not all(bool(torch.isfinite(v).all()) for v in (raw,proposed_lam,proposed_gamma)):
            raise FloatingPointError('nonfinite EP site proposal')
        accepted=(proposed_lam>0)&(proposed_lam<=1e12)
        damping=r['damping']
        next_lam=torch.where(accepted,(1-damping)*lam+damping*proposed_lam,lam)
        next_gamma=torch.where(accepted,(1-damping)*gamma+damping*proposed_gamma,gamma)
        residual=max(float(torch.linalg.vector_norm(next_lam-lam)/torch.clamp_min(torch.linalg.vector_norm(lam),1.)),
                     float(torch.linalg.vector_norm(next_gamma-gamma)/torch.clamp_min(torch.linalg.vector_norm(gamma),1.)))
        linear=float(torch.linalg.vector_norm(precision@gaussian-rhs)/torch.clamp_min(torch.linalg.vector_norm(rhs),1.))
        if linear>1e-8:raise FloatingPointError('EP linear solve residual exceeded1e-8')
        trace.append(dict(iteration=iteration+1,fixed_point_residual=residual,linear_relative_residual=linear,
            rejected_sites=int((~accepted).sum()),variance_floor_sites=int((variance<floor).sum()),
            cavity_precision_min=float(cavity_precision.min())))
        lam,gamma=next_lam,next_gamma
    converged=trace[-1]['fixed_point_residual']<=1e-5 and trace[-1]['rejected_sites']==0
    return mean[:n]+1j*mean[n:],variance[:n]+variance[n:],raw,dict(
        trace=trace,converged=converged,fixed_point_residual=trace[-1]['fixed_point_residual'],
        linear_relative_residual=max(t['linear_relative_residual'] for t in trace),
        moments='finite-BPSK tilted marginals from Gaussian EP cavity; not exact joint posterior',
        stabilization='site moment variance floor2.5e-11; invalid/nonpositive/>1e12 precision proposals retain both old sites',
        precision_shape=list(gram.shape))


def _mf(y,H,sigma,r,iterations):
    """Factorized finite-QPSK variational coordinate descent, no Gaussian EP sites."""
    a=.5;epsilon=1e-12;damping=r['damping'];norms=H.abs().square().sum(0)
    initial=H.conj().T@y
    # Matched single-symbol marginals initialize q; exact for orthogonal columns.
    mu=a*torch.tanh(2*a*initial.real/sigma)+1j*a*torch.tanh(2*a*initial.imag/sigma)
    limit=a*(1-2*epsilon)
    mu=mu.real.clamp(-limit,limit)+1j*mu.imag.clamp(-limit,limit)
    residual=y-H@mu
    def objective():
        variances=2*a*a-mu.abs().square()
        pr=(mu.real/a+1)/2;pi=(mu.imag/a+1)/2
        entropy_term=sum((p*torch.log(p)+(1-p)*torch.log1p(-p)).sum() for p in (pr,pi))
        return float((residual.abs().square().sum()+torch.dot(norms,variances))/sigma+entropy_term)
    previous=objective();trace=[]
    for iteration in range(iterations):
        before=mu.clone();clips=0
        for j in range(len(y)):
            column=H[:,j];excluded=residual+column*mu[j]
            matched=torch.vdot(column,excluded)
            real=a*torch.tanh(2*a*matched.real/sigma);imag=a*torch.tanh(2*a*matched.imag/sigma)
            clips+=int(abs(float(real))>limit)+int(abs(float(imag))>limit)
            target=real.clamp(-limit,limit)+1j*imag.clamp(-limit,limit)
            updated=(1-damping)*mu[j]+damping*target
            residual=excluded-column*updated;mu[j]=updated
        current=objective()
        if not math.isfinite(current) or current>previous+1e-8*max(1.,abs(previous)):
            raise FloatingPointError('MF variational free energy increased or became nonfinite')
        change=float(torch.linalg.vector_norm(mu-before)/torch.clamp_min(torch.linalg.vector_norm(before),1.))
        trace.append(dict(iteration=iteration+1,free_energy=current,free_energy_change=current-previous,
                          fixed_point_residual=change,probability_clip_uses=clips))
        previous=current
    pr=(mu.real/a+1)/2;pi=(mu.imag/a+1)/2
    raw=torch.cat((torch.log(pr)-torch.log1p(-pr),torch.log(pi)-torch.log1p(-pi)))
    variance=2*a*a-mu.abs().square()
    return mu,variance,raw,dict(trace=trace,converged=trace[-1]['fixed_point_residual']<=1e-5,
        fixed_point_residual=trace[-1]['fixed_point_residual'],linear_relative_residual=0.,
        moments='factorized discrete variational marginals; posterior correlations omitted',
        stabilization='probabilities clipped to[1e-12,1-1e-12]; damped marginal means; fixed ascending coordinate order',
        convergence_scope='coordinate fixed point only; nonconvex objective, not global posterior optimum')


def detect(y_cancelled,H,sigma_complex,constellation,identifier,*,device='cpu',doubled=False):
    if type(doubled) is not bool:raise ValueError('doubling must be explicit boolean')
    r=recipe(identifier);y,h,c,sigma,dev=inputs(y_cancelled,H,sigma_complex,constellation,device)
    if dev.type=='cuda':torch.cuda.synchronize(dev)
    started=time.perf_counter();cpu=time.process_time()
    yt=torch.tensor(y,dtype=torch.complex128,device=dev);ht=torch.tensor(h,dtype=torch.complex128,device=dev)
    iterations=r['doubled_iterations'] if doubled else r['iterations']
    with torch.no_grad():
        if r['family']=='BP':
            messages=[];graphs=[]
            hard,mu,var=mp_detect_bp_torch(yt,ht,sigma,c,iterations,r['threshold'],r['damping'],
                device=dev,return_numpy=False,return_soft=True,graph_observer=graphs.append,
                convergence_observer=messages.append)
            if len(messages)!=1 or len(graphs)!=1:
                raise RuntimeError('BP observers did not return exactly one final state and graph')
            state=messages[0]
            executed=state['executed_iterations']
            bp_message_state={key:state[key].detach().cpu().numpy()
                              for key in ('mu_previous','mu_current','var_previous','var_current')}
            def relative(previous,current):
                return float(np.linalg.norm(current-previous)/max(1.,np.linalg.norm(previous))) if executed else 0.
            mu_residual=relative(bp_message_state['mu_previous'],bp_message_state['mu_current'])
            var_residual=relative(bp_message_state['var_previous'],bp_message_state['var_current'])
            raw=torch.as_tensor(demap_llr(mu.detach().cpu().numpy(),var.detach().cpu().numpy(),.5,clip=np.inf),
                                dtype=torch.float64,device=dev)
            diagnostics=dict(converged=max(mu_residual,var_residual)<=r['fixed_point_tolerance'],
                fixed_point_residual=max(mu_residual,var_residual),linear_relative_residual=None,
                mu_message_relative_residual=mu_residual,var_message_relative_residual=var_residual,
                executed_iterations=executed,bp_graph=graphs[0],
                moments='Gaussian BP posterior moments; not exact discrete posterior moments',
                convergence_scope='last executed edge-message update only; not posterior optimality')
            diagnostics['bp_message_hashes']={key:array_hash(value) for key,value in bp_message_state.items()}
            diagnostics['bp_message_norms']={key:float(np.linalg.norm(value)) for key,value in bp_message_state.items()}
        else:
            mu,var,raw,diagnostics=(_ep if r['family']=='stable-EP' else _mf)(yt,ht,sigma,r,iterations)
    if any(not bool(torch.isfinite(v).all()) for v in (mu,var,raw)) or bool((var<0).any()):
        raise FloatingPointError('invalid detector terminal marginals')
    mu,var,raw=[v.detach().cpu().numpy() for v in (mu,var,raw)]
    hard=.5*np.where(raw[:len(y)]>=0,1.,-1.)+.5j*np.where(raw[len(y):]>=0,1.,-1.)
    if dev.type=='cuda':torch.cuda.synchronize(dev)
    diagnostics.update(recipe=copy.deepcopy(r),iterations=iterations,doubled=doubled,device=str(dev),
        seconds=time.perf_counter()-started,CPU_seconds=time.process_time()-cpu,
        sigma_complex=sigma,sigma_real=sigma/2,qpsk_symbol_power=.5,truth_access='none',fresh_state=True,
        input_hashes={'y':array_hash(y),'H':array_hash(h),'constellation':array_hash(c),'sigma':array_hash(np.asarray(sigma))},
        LLR_semantics='log P(bit0)/P(bit1); all real bits then all imaginary bits; final clip20')
    if r['family']=='BP':
        diagnostics['input_hashes']['H_bp_cast']=array_hash(ht.detach().cpu().numpy())
    result=dict(mu=mu,var=var,raw_llr=raw,llr=np.clip(raw,-20,20),x_hard=hard,diagnostics=diagnostics)
    if r['family']=='BP':result['bp_message_state']=bp_message_state
    return result


def terminal(y_cancelled,H,sigma_complex,constellation,code,identifier,*,device='cpu',doubled=False):
    if code['n']!=2*len(y_cancelled):raise ValueError('code and detector dimensions differ')
    started=time.perf_counter();cpu=time.process_time()
    result=detect(y_cancelled,H,sigma_complex,constellation,identifier,device=device,doubled=doubled)
    result['diagnostics']['decoder_identity']={
        'n':int(code['n']),'k':int(code['k']),'maxiter':50,
        'G':array_hash(code['G']),'H':array_hash(code['H']),
        'free_cols':array_hash(code['free_cols']),
        'chk':array_hash(code['chk']),'var':array_hash(code['var']),
        'row_ptr':array_hash(code['row_ptr'])}
    decoded,ok=decode_llr(code,result['llr'],maxiter=50)
    result.update(decoded=decoded,info_hat=extract_info(code,decoded),decode_ok=bool(ok),
                  terminal_seconds=time.perf_counter()-started,terminal_CPU_seconds=time.process_time()-cpu,
                  call_type='T',ldpc_maxiter=50)
    return result


def qualification_pair(base,doubled):
    a,b=base['diagnostics'],doubled['diagnostics']
    if (a['recipe']!=b['recipe'] or a['doubled'] or not b['doubled'] or
            b['iterations']!=2*a['iterations'] or a['input_hashes']!=b['input_hashes'] or
            a.get('device')!=b.get('device') or
            not isinstance(a.get('decoder_identity'),dict) or
            a['decoder_identity']!=b.get('decoder_identity')):
        raise ValueError('not a matched fixed iteration-doubling pair')
    family=a['recipe']['family']
    if family=='BP':
        def stable_graph(graph):
            if not isinstance(graph,dict):raise ValueError('missing actual BP graph')
            return {key:value for key,value in graph.items() if key!='graph_observer_seconds'}
        def verify_graph(diagnostics):
            graph=diagnostics.get('bp_graph')
            recipe_row=diagnostics['recipe']
            if (not isinstance(graph,dict) or
                    graph.get('H_hash')!=diagnostics['input_hashes'].get('H_bp_cast') or
                    graph.get('threshold')!=recipe_row.get('threshold') or
                    graph.get('operator')!='>=' or graph.get('dtype')!='torch.complex128'):
                raise ValueError('actual BP graph is not bound to the cast detector input and recipe')
        verify_graph(a);verify_graph(b)
        if stable_graph(a.get('bp_graph'))!=stable_graph(b.get('bp_graph')):
            raise ValueError('actual BP graphs differ')
        def verify_messages(result,diagnostics):
            state=result.get('bp_message_state')
            keys=('mu_previous','mu_current','var_previous','var_current')
            if not isinstance(state,dict) or set(state)!=set(keys):
                raise ValueError('missing BP message state')
            values={key:np.asarray(state[key]) for key in keys}
            if (values['mu_previous'].shape!=values['mu_current'].shape or
                    values['var_previous'].shape!=values['var_current'].shape or
                    values['mu_previous'].shape!=values['var_previous'].shape or
                    any(value.ndim!=1 or len(value)!=diagnostics['bp_graph']['edges'] or
                        not np.isfinite(value).all() for value in values.values()) or
                    any(np.iscomplexobj(values[key]) or np.any(values[key]<0)
                        for key in ('var_previous','var_current'))):
                raise ValueError('invalid BP message state')
            hashes={key:array_hash(value) for key,value in values.items()}
            norms={key:float(np.linalg.norm(value)) for key,value in values.items()}
            stored_norms=diagnostics.get('bp_message_norms')
            if hashes!=diagnostics.get('bp_message_hashes'):
                raise ValueError('BP message state identity differs')
            if (not isinstance(stored_norms,dict) or set(stored_norms)!=set(keys) or
                    any(not math.isclose(norms[key], float(stored_norms[key]), rel_tol=0, abs_tol=1e-12)
                        for key in keys)):
                raise ValueError('BP message state identity differs')
            executed=diagnostics.get('executed_iterations')
            expected=0 if diagnostics['bp_graph']['edges']==0 else diagnostics['iterations']
            if executed!=expected:
                raise ValueError('BP executed iteration count differs')
            relative=lambda previous,current: (float(np.linalg.norm(current-previous)/
                max(1.,np.linalg.norm(previous))) if executed else 0.)
            residuals=(relative(values['mu_previous'],values['mu_current']),
                       relative(values['var_previous'],values['var_current']))
            recorded=(diagnostics.get('mu_message_relative_residual'),
                      diagnostics.get('var_message_relative_residual'))
            fixed=max(residuals)
            if (any(not math.isclose(float(a), float(b), rel_tol=0, abs_tol=1e-12)
                    for a,b in zip(residuals, recorded)) or
                    not math.isclose(fixed, float(diagnostics.get('fixed_point_residual')),
                                     rel_tol=0, abs_tol=1e-12)):
                raise ValueError('BP message residual does not match saved state')
            converged=diagnostics.get('converged')
            if type(converged) is not bool or converged!=(fixed<=diagnostics['recipe']['fixed_point_tolerance']):
                raise ValueError('BP convergence flag does not match saved state and threshold')
        verify_messages(base,a);verify_messages(doubled,b)
    for diagnostics in (a,b):
        keys=('fixed_point_residual',) if family=='BP' else ('fixed_point_residual','linear_relative_residual')
        if any(not math.isfinite(diagnostics[key]) or diagnostics[key]<0 for key in keys):
            raise ValueError('invalid qualification residual')
        if family=='BP' and diagnostics.get('linear_relative_residual') is not None:
            raise ValueError('BP has no linear solve residual')
    differences={}
    for name in ('llr','mu'):
        x,y=np.asarray(base[name]),np.asarray(doubled[name])
        if x.shape!=y.shape or not np.isfinite(x).all() or not np.isfinite(y).all():
            raise ValueError('invalid paired detector outputs')
        differences[name]=float(np.linalg.norm(x-y)/max(1.,np.linalg.norm(y)))
    x,y=np.asarray(base['decoded']),np.asarray(doubled['decoded'])
    if (x.ndim!=1 or x.shape!=y.shape or any(not np.isin(v,(0,1)).all() for v in (x,y))):
        raise ValueError('decoded shape/binary contract differs')
    bits_equal=bool(np.array_equal(x,y))
    passed=bool(a['converged'] and b['converged'] and bits_equal and
        differences['llr']<=QUALIFICATION['relative_llr'] and differences['mu']<=QUALIFICATION['relative_mean'] and
        max(a['fixed_point_residual'],b['fixed_point_residual'])<=QUALIFICATION['fixed_point'] and
        (family=='BP' or max(a['linear_relative_residual'],b['linear_relative_residual'])<=QUALIFICATION['linear_residual']))
    return dict(stable=passed,differences=differences,decoded_equal=bits_equal,thresholds=dict(QUALIFICATION),
        scope='iteration stability only; exact toy correctness and development performance are separate gates')
