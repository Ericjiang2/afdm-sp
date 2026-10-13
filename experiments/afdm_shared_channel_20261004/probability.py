"""Same-observation QPSK marginal, shared-gain mixture, and Gaussian projection."""
import argparse
from pathlib import Path
import sys
import time

import numpy as np
from scipy.special import expit, logsumexp, xlogy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk, exact_posterior
from experiments.afdm_structured_inference_20261003.collapsed import PHYSICAL, dense_operators, SOURCES as PHYSICAL_SOURCES
from experiments.afdm_shared_channel_20261004.quadrature import gaussian_nodes, sphere_nodes, independent_nodes, validate_nodes
from experiments.afdm_shared_channel_20261004.common import run, dump


def real_matrix(matrix):
    return np.concatenate((np.concatenate((matrix.real,-matrix.imag),axis=-1),
                           np.concatenate((matrix.imag,matrix.real),axis=-1)),axis=-2)


def packed(value):
    return np.concatenate((value.real,value.imag),axis=-1)


def outside_cavity(n, block, incoming):
    """Independent bit cavity; excludes all target-block incoming factors."""
    incoming = np.asarray(incoming, float)
    block = np.asarray(block)
    if (incoming.shape != (2*n,) or not np.isfinite(incoming).all()
            or block.ndim != 1 or len(block) == 0 or not np.issubdtype(block.dtype,np.integer)
            or len(np.unique(block)) != len(block) or np.any(block < 0) or np.any(block >= n)):
        raise ValueError('finite incoming LLRs and unique in-range integer block required')
    outside = np.setdiff1d(np.arange(n), block)
    means_real = .5*np.tanh(incoming/2)
    variance = .25-means_real**2
    own = np.r_[block,block+n]
    means_real[own] = 0
    variance[own] = 0
    means = means_real[:n]+1j*means_real[n:]
    return outside, means, np.diag(variance)


def log_bit_prior(bits, incoming):
    return np.sum(-np.logaddexp(0,(2*bits-1)*np.asarray(incoming)),axis=1)


def exact_scores(y, operators, pilot, block, incoming, noise, *, mean=None, covariance=None,
                 nodes=None, weights=None):
    """Enumerate outside QPSK; Gaussian h analytic, sphere h numerical."""
    n = len(pilot)
    outside, _, _ = outside_cavity(n,block,incoming)
    words,bits = enumerate_qpsk(n)
    local,local_bits = enumerate_qpsk(len(block))
    if nodes is None:
        posterior = exact_posterior(y,operators,pilot,words,mean,covariance,noise)
        full_scores = posterior.log_likelihood
    else:
        full_scores = conditional_scores(y,operators,pilot,words,np.zeros(n,complex),
                                         np.zeros((2*n,2*n)),np.arange(n),noise,nodes,weights)
    ids = np.r_[outside,outside+n]
    prior = log_bit_prior(bits[:,ids],np.asarray(incoming)[ids])
    scores = np.array([logsumexp(full_scores[np.all(words[:,block]==word,axis=1)]
                        +prior[np.all(words[:,block]==word,axis=1)]) for word in local])
    return scores,local,local_bits


def conditional_scores(y, operators, pilot, local_words, outside_mean, outside_real_cov,
                       block, noise, nodes, weights, batch=2048):
    """Integrate p(y|h,d_B) after a Gaussian outside cavity.

    Real augmentation preserves unequal I/Q variances from nonuniform bit priors.
    Cholesky covariance depends on h, not the local candidate; it is shared across
    all candidate RHS within each node batch. No observation-adapted gain prior.
    """
    nodes,weights = validate_nodes(nodes,weights)
    n = len(pilot)
    if not np.isfinite(noise) or noise <= 0:
        raise ValueError('noise must be strictly positive')
    x = np.broadcast_to(np.asarray(pilot,complex)+outside_mean,(len(local_words),n)).copy()
    x[:,block] += local_words
    result = np.full(len(x),-np.inf)
    for start in range(0,len(nodes),batch):
        h = np.einsum('tp,pij->tij',nodes[start:start+batch],operators)
        residual = packed(y[None,None,:]-np.einsum('tij,kj->tki',h,x))
        r = real_matrix(h)
        covariance = noise/2*np.eye(2*n)+r@outside_real_cov@r.transpose(0,2,1)
        chol = np.linalg.cholesky(covariance)
        whitened = np.linalg.solve(chol,residual.transpose(0,2,1))
        log_density = (-n*np.log(2*np.pi)-np.log(np.diagonal(chol,axis1=1,axis2=2)).sum(axis=1)[:,None]
                       -.5*np.sum(whitened**2,axis=1))
        result = np.logaddexp(result,logsumexp(log_density+np.log(weights[start:start+batch,None]),axis=0))
    return result


def mm_scores(y, operators, pilot, local_words, outside_mean, outside_real_cov,
              block, noise, mean, covariance):
    """Exact second moment of the declared cavity, single Gaussian projection."""
    n = len(pilot)
    mean,covariance = np.asarray(mean),np.asarray(covariance)
    hbar = np.einsum('p,pij->ij',mean,operators)
    second_h = covariance+mean[:,None]*mean.conj()[None,:]
    # General independent I/Q cavity's Hermitian and pseudo covariance.
    crr,cii = outside_real_cov[:n,:n],outside_real_cov[n:,n:]
    cri = outside_real_cov[:n,n:]
    co = crr+cii+1j*(cri.T-cri)
    po = crr-cii+1j*(cri+cri.T)
    out = []
    for word in local_words:
        x = np.asarray(pilot,complex)+outside_mean
        x = x.copy(); x[block] += word
        b = np.einsum('pij,j->ip',operators,x)
        cov = noise*np.eye(n)+b@covariance@b.conj().T
        cov += np.einsum('pq,pik,kl,qjl->ij',second_h,operators,co,operators.conj())
        # Proper Gaussian or uniform-sphere gains have zero central pseudo moment.
        pseudo = hbar@po@hbar.T
        real_cov = .5*np.block([[np.real(cov+pseudo),np.imag(pseudo-cov)],
                                [np.imag(pseudo+cov),np.real(cov-pseudo)]])
        chol = np.linalg.cholesky(real_cov)
        residual = packed(y-hbar@x)
        whitened = np.linalg.solve(chol,residual)
        out.append(-n*np.log(2*np.pi)-np.log(chol.diagonal()).sum()-.5*np.dot(whitened,whitened))
    return np.array(out)


def normalized(scores, bits):
    logp = scores-logsumexp(scores)
    p = np.exp(logp)
    llr = np.array([logsumexp(logp[bits[:,j]==0])-logsumexp(logp[bits[:,j]==1]) for j in range(bits.shape[1])])
    return dict(logp=logp,probability=p,llr=llr,bit0=expit(llr))


def block_extrinsic(scores, bits, incoming):
    """Global-factor-to-bit messages: explicitly omit each own incoming factor."""
    incoming = np.asarray(incoming,float)
    if incoming.shape != (bits.shape[1],) or not np.isfinite(incoming).all():
        raise ValueError('invalid local incoming LLRs')
    messages = []
    for j in range(len(incoming)):
        others = np.arange(len(incoming)) != j
        weighted = scores+log_bit_prior(bits[:,others],incoming[others])
        messages.append(logsumexp(weighted[bits[:,j]==0])-logsumexp(weighted[bits[:,j]==1]))
    return np.array(messages)


def metrics(reference, candidate, truth_bits):
    p,q = reference['bit0'],candidate['bit0']
    llr = candidate['llr']
    log0,log1 = -np.logaddexp(0,-llr),-np.logaddexp(0,llr)
    return dict(block_kl=float(np.sum(reference['probability']*(reference['logp']-candidate['logp']))),
        bit_kl=float(np.mean(xlogy(p,p)+xlogy(1-p,1-p)-p*log0-(1-p)*log1)),
        llr_rmse=float(np.sqrt(np.mean((llr-reference['llr'])**2))),
        max_probability_error=float(np.max(abs(candidate['probability']-reference['probability']))),
        expected_brier=float(np.mean(p*(1-q)**2+(1-p)*q*q)),
        expected_logloss=float(np.mean(-p*log0-(1-p)*log1)),
        observed_brier=float(np.mean(((1-truth_bits)-q)**2)),
        observed_logloss=float(np.mean(-(1-truth_bits)*log0-truth_bits*log1)),
        bit_sign_disagreements=int(np.count_nonzero((llr>=0)!=(reference['llr']>=0))))


def fourth_moments(m, v, c, v0, normalized_prior=False):
    """M rank-one, V PSD, h isotropic proper or uniform complex sphere."""
    p = len(m)
    tm,tv = np.trace(m).real,np.trace(v).real
    tmm,tvv,tmv = np.trace(m@m).real,np.trace(v@v).real,np.trace(m@v).real
    multiplier = p/(p+1) if normalized_prior else 1.
    e_mm = multiplier*c*c*(tm*tm+tmm)
    e_mv = multiplier*c*c*(tm*tv+tmv)
    e_vv = multiplier*c*c*(tv*tv+tvv)
    mixture = e_mm+4*(v0*c*tm+e_mv)+2*(v0*v0+2*v0*c*tv+e_vv)
    gaussian = 2*(v0+c*(tm+tv))**2
    return float(mixture),float(gaussian),float(mixture-gaussian)


def fourth_checks():
    rows = []
    for p in (1,2):
        for kind in ('random_scale','fixed_target','anisotropic'):
            b = np.linspace(.3,.7,p)+1j*np.linspace(.1,.2,p)
            m = np.outer(b,b.conj()) if kind != 'random_scale' else np.zeros((p,p))
            v = np.eye(p) if kind != 'fixed_target' else np.zeros((p,p))
            if kind == 'anisotropic': v = np.diag(np.linspace(.2,1.,p))
            for normalized_prior in (False,True):
                nodes,weights = sphere_nodes(p,1.,12) if normalized_prior else gaussian_nodes(np.zeros(p),np.eye(p)/p,5)
                a = np.einsum('ti,ij,tj->t',nodes.conj(),m,nodes).real
                variance = .2+np.einsum('ti,ij,tj->t',nodes.conj(),v,nodes).real
                numerical = float(weights@(a*a+4*a*variance+2*variance*variance))
                mix,mm,difference = fourth_moments(m,v,1/p,.2,normalized_prior)
                rows.append(dict(p=p,kind=kind,prior='normalized' if normalized_prior else 'Gaussian',
                    mixture=mix,mm=mm,difference=difference,quadrature_error=abs(numerical-mix)))
    return rows


def base_cases(output):
    """Save known-gain and no-outside reductions separately from the paired grid."""
    n=2
    ops=dense_operators(PHYSICAL.Channel(n,.37/n,.13/n**2,[1],[.23],[1]))
    pilot=np.array([.3+.2j,-.1+.4j]); y=np.array([.6-.2j,.1+.7j])
    incoming=np.array([.7,-.8,-.3,.5]); records=[]
    for prior in ('known','Gaussian','normalized'):
        mean=np.array([.7+.2j]) if prior=='known' else np.zeros(1)
        cov=np.zeros((1,1)) if prior=='known' else np.eye(1)
        for block in ([0],[0,1]):
            local,bits=enumerate_qpsk(len(block))
            _,m,v=outside_cavity(n,block,incoming)
            for noise in CONFIG['noise']:
                rules=(gaussian_nodes(mean,cov,41),gaussian_nodes(mean,cov,31)) if prior!='normalized' else (sphere_nodes(1,1.,41),sphere_nodes(1,1.,31))
                data={}
                for label,(nodes,weights) in zip(('fine','coarse'),rules):
                    data['mix_'+label]=conditional_scores(y,ops,pilot,local,m,v,block,noise,nodes,weights)
                    data['qpsk_'+label],_,_=exact_scores(y,ops,pilot,block,incoming,noise,
                        **(dict(nodes=nodes,weights=weights) if prior=='normalized' else dict(mean=mean,covariance=cov)))
                data['mm']=mm_scores(y,ops,pilot,local,m,v,block,noise,mean,cov)
                values={name:normalized(score,bits) for name,score in data.items()}
                ref=values['qpsk_fine']; index=len(records)
                np.savez(output/f'base_{index:02d}.npz',y=y,operators=ops,pilot=pilot,incoming=incoming,
                    block=block,noise=noise,**{'score_'+k:v for k,v in data.items()},
                    **{k+'_'+name:value for name,obj in values.items() for k,value in obj.items()})
                records.append(dict(case=index,prior=prior,block_size=len(block),noise=noise,
                    exact_label='numerical sphere reference' if prior=='normalized' else 'analytic Gaussian elimination',
                    mix_qpsk_probability_error=float(np.max(abs(values['mix_fine']['probability']-ref['probability']))),
                    mix_mm_logscore_error=float(np.max(abs(data['mix_fine']-data['mm']))),
                    refinement_max_logscore_error=float(max(np.max(abs(data['mix_fine']-data['mix_coarse'])),np.max(abs(data['qpsk_fine']-data['qpsk_coarse']))))))
    dump(output/'base_cases.json',records)
    return records


CONFIG = dict(seed=[20261004,110000,20], n=3, p=[1,2], draws=3, noise=[.15,1.2],
    priors=['Gaussian','normalized'], cavity=['uniform','nonuniform'], block_sizes=[1,2],
    orders=[5,9,13], independent_sobol_exponent=15, refinement_probability_tolerance=.003,
    refinement_llr_tolerance=.03, independent_probability_tolerance=.006,
    independent_llr_tolerance=.06, amplitude=.5, total_gain_energy=1., receiver_calls=0,
    rule='retain all cases including numerical nonconvergence; no successful-subset scoring')
SOURCES = [__file__, Path(__file__).with_name('quadrature.py'), *PHYSICAL_SOURCES,
           ROOT/'experiments/afdm_structured_inference_20261003/potential.py']


def calculate(output):
    records = []
    bases = base_cases(output)
    fourth = fourth_checks()
    dump(output/'fourth_moments.json',fourth)
    if max(r['quadrature_error'] for r in fourth) > 1e-10:
        raise AssertionError('fourth-order analytic identity failed')
    # Fixed independent gain rules are generated before observations and saved once.
    rules = {}
    for p in CONFIG['p']:
        for prior in CONFIG['priors']:
            for order in CONFIG['orders']:
                rule = (sphere_nodes(p,1.,order) if prior == 'normalized'
                        else gaussian_nodes(np.zeros(p),np.eye(p)/p,order))
                rules[p,prior,order] = rule
            rules[p,prior,'independent'] = independent_nodes(p,1.,CONFIG['independent_sobol_exponent'],
                [*CONFIG['seed'],p,int(prior=='normalized')],normalized=prior=='normalized')
            for name in [*CONFIG['orders'],'independent']:
                np.savez(output/f'nodes_{p}_{prior}_{name}.npz',nodes=rules[p,prior,name][0],weights=rules[p,prior,name][1])
    n = CONFIG['n']
    words,bits = enumerate_qpsk(n)
    for draw in range(CONFIG['draws']):
        rng = np.random.default_rng([*CONFIG['seed'],draw])
        data_id = int(rng.integers(len(words)))
        unit_noise = (rng.normal(size=n)+1j*rng.normal(size=n))/np.sqrt(2)
        gain_base = (rng.normal(size=2)+1j*rng.normal(size=2))/np.sqrt(2)
        pilot = .55*np.exp(.4j*np.arange(n))
        for p in CONFIG['p']:
            channel = PHYSICAL.Channel(n,.37/n,.13/n**2,np.arange(p),np.array([.23,-.38])[:p],np.ones(p))
            ops = dense_operators(channel)
            for prior in CONFIG['priors']:
                h = gain_base[:p]/np.linalg.norm(gain_base[:p]) if prior == 'normalized' else gain_base[:p]/np.sqrt(p)
                for noise in CONFIG['noise']:
                    y = np.einsum('p,pij,j->i',h,ops,pilot+words[data_id])+np.sqrt(noise)*unit_noise
                    for cavity in CONFIG['cavity']:
                        incoming = np.zeros(2*n) if cavity=='uniform' else np.array([.7,-.8,.4,-.3,.5,-.6])
                        for size in CONFIG['block_sizes']:
                            block = np.arange(size)
                            outside,m,real_cov = outside_cavity(n,block,incoming)
                            local,local_bits = enumerate_qpsk(size)
                            truth_bits = bits[data_id,np.r_[block,block+n]]
                            all_scores = {}
                            start = time.perf_counter()
                            if prior == 'Gaussian':
                                exact,_,_ = exact_scores(y,ops,pilot,block,incoming,noise,mean=np.zeros(p),covariance=np.eye(p)/p)
                                all_scores['exact_analytic'] = exact
                            for name in [*CONFIG['orders'],'independent']:
                                nodes,weights = rules[p,prior,name]
                                all_scores[f'mix_{name}'] = conditional_scores(y,ops,pilot,local,m,real_cov,block,noise,nodes,weights)
                                if prior == 'normalized':
                                    all_scores[f'qpsk_{name}'],_,_ = exact_scores(y,ops,pilot,block,incoming,noise,nodes=nodes,weights=weights)
                            all_scores['mm'] = mm_scores(y,ops,pilot,local,m,real_cov,block,noise,np.zeros(p),np.eye(p)/p)
                            high,low = CONFIG['orders'][-1],CONFIG['orders'][-2]
                            normalized_scores = {name:normalized(score,local_bits) for name,score in all_scores.items()}
                            refname = 'exact_analytic' if prior=='Gaussian' else f'qpsk_{high}'
                            ref,mix,mm = (normalized_scores[name] for name in (refname,f'mix_{high}','mm'))
                            met = {name:metrics(ref,z,truth_bits) for name,z in normalized_scores.items()}
                            errors = {}
                            for obj in (['mix'] if prior=='Gaussian' else ['mix','qpsk']):
                                fine,coarse,independent = (normalized_scores[f'{obj}_{name}'] for name in (high,low,'independent'))
                                errors[obj] = dict(refinement_probability=float(np.max(abs(fine['probability']-coarse['probability']))),
                                    refinement_llr=float(np.max(abs(fine['llr']-coarse['llr']))),
                                    independent_probability=float(np.max(abs(fine['probability']-independent['probability']))),
                                    independent_llr=float(np.max(abs(fine['llr']-independent['llr']))))
                            converged = all(e['refinement_probability']<=CONFIG['refinement_probability_tolerance']
                                and e['refinement_llr']<=CONFIG['refinement_llr_tolerance']
                                and e['independent_probability']<=CONFIG['independent_probability_tolerance']
                                and e['independent_llr']<=CONFIG['independent_llr_tolerance'] for e in errors.values())
                            step1,step2 = mix['llr']-ref['llr'],mm['llr']-mix['llr']
                            local_incoming = incoming[np.r_[block,block+n]]
                            ext = block_extrinsic(all_scores[f'mix_{high}'],local_bits,local_incoming)
                            own_error = 0.
                            for j in range(2*size):
                                changed = local_incoming.copy(); changed[j] += 3.
                                own_error = max(own_error,abs(block_extrinsic(all_scores[f'mix_{high}'],local_bits,changed)[j]-ext[j]))
                            index = len(records)
                            raw = dict(y=y,operators=ops,pilot=pilot,gain_truth=h,data_truth=words[data_id],unit_noise=unit_noise,
                                incoming=incoming,block=block,local_words=local,local_bits=local_bits,truth_bits=truth_bits,
                                step1_llr=step1,step2_llr=step2,extrinsic=ext)
                            for name in all_scores:
                                raw['scores_'+name] = all_scores[name]
                                for key,value in normalized_scores[name].items(): raw[key+'_'+name] = value
                            np.savez(output/f'case_{index:03d}.npz',**raw)
                            records.append(dict(case=index,draw=draw,p=p,prior=prior,noise=noise,cavity=cavity,block_size=size,
                                observation_pair_id=f'{draw}_{p}_{prior}_{noise}',reference=refname,
                                numerical_converged=bool(converged),integration_errors=errors,metrics=met,
                                approximation_steps=dict(outside_gaussian_llr_rmse=float(np.sqrt(np.mean(step1**2))),
                                    shared_gain_projection_llr_rmse=float(np.sqrt(np.mean(step2**2))),
                                    llr_error_cross_term=float(2*np.mean(step1*step2)),
                                    opposing_error_coordinates=int(np.count_nonzero(step1*step2<0)),
                                    projection_sign_changes=int(np.count_nonzero((mm['llr']>=0)!=(mix['llr']>=0)))),
                                paired_mm_minus_mix={key:met['mm'][key]-met[f'mix_{high}'][key] for key in met['mm']},
                                own_factor_invariance_error=float(own_error),seconds=time.perf_counter()-start))
    dump(output/'raw.json',dict(cases=records))
    groups = []
    for prior in CONFIG['priors']:
        rows = [r for r in records if r['prior']==prior]
        groups.append(dict(prior=prior,cases=len(rows),nonconverged=sum(not r['numerical_converged'] for r in rows),
            mm_better_block_kl=sum(r['paired_mm_minus_mix']['block_kl']<0 for r in rows),
            mix_better_block_kl=sum(r['paired_mm_minus_mix']['block_kl']>0 for r in rows),
            cancellation_cases=sum(r['approximation_steps']['llr_error_cross_term']<0 for r in rows),
            mean_paired_mm_minus_mix={k:float(np.mean([r['paired_mm_minus_mix'][k] for r in rows])) for k in rows[0]['paired_mm_minus_mix']}))
    return dict(status='all_registered_cases_retained',cases=len(records),independent_exogenous_draws=CONFIG['draws'],
        nonconverged=sum(not r['numerical_converged'] for r in records),groups=groups,
        fourth_moments=fourth,base_cases=bases,
        interpretation='descriptive local paired errors; nonconverged comparisons remain numerical uncertainty, no performance claim')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage',default='probability_v1')
    args = parser.parse_args()
    run(args.stage,CONFIG,SOURCES,calculate)
