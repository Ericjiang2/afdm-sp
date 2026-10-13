"""Disjoint two-symbol factor messages with a declared deterministic cavity.

External symbols stay at zero soft mean. A local 16-letter alphabet is not a
codeword bank, and this one pass is not a production receiver.
"""
from pathlib import Path
import sys
import time
import resource

import numpy as np
from scipy.special import logsumexp, expit, xlogy

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from experiments.afdm_structured_inference_20261003.collapsed import CollapsedModel, PHYSICAL, SOURCES, dense_operators
from experiments.afdm_structured_inference_20261003.message import bit_extrinsic
from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk, exact_posterior
from experiments.afdm_structured_inference_20261003.common import run, dump, ARTIFACT


class PairLikelihood:
    """Shared local Gram arithmetic, restricted to an independent zero-mean gain prior."""
    def __init__(self,model,y,pilot):
        self.model=model
        self.y=np.asarray(y,complex)
        self.pilot=np.asarray(pilot,complex)
        c=model.channel
        if self.y.shape!=(c.n,) or self.pilot.shape!=(c.n,) or not all(np.isfinite(a).all() for a in (self.y,self.pilot)):
            raise ValueError('finite observation/pilot must match channel')
        if np.any(model.mean!=0):
            raise ValueError('shared Gram kernel explicitly requires zero-mean gains')
        self.yt=PHYSICAL.daft(self.y,c.c1,c.c2,True)
        self.t0=model.ops.responses_time(PHYSICAL.daft(self.pilot,c.c1,c.c2,True))@model.factor
        self.ynorm=float(np.vdot(self.yt,self.yt).real)

    def block(self,indices):
        raw=np.asarray(indices)
        n=self.model.channel.n
        if (raw.ndim!=1 or len(raw) not in (1,2) or not np.issubdtype(raw.dtype,np.integer)
                or len(np.unique(raw))!=len(raw) or np.any(raw<0) or np.any(raw>=n)):
            raise ValueError('one or two distinct legal integer symbol indices required')
        c=self.model.channel
        columns=[self.t0]
        for index in raw:
            basis=np.zeros(n,complex);basis[index]=1
            columns.append(self.model.ops.responses_time(PHYSICAL.daft(basis,c.c1,c.c2,True))@self.model.factor)
        stacked=np.stack(columns)
        # G[a,b] = T_a^H T_b; matched[a] = T_a^H y. Candidate
        # coefficients multiply the *second* block without conjugation.
        gram=np.einsum('anp,bnq->abpq',stacked.conj(),stacked,optimize=True)
        matched=np.einsum('anp,n->ap',stacked.conj(),self.yt,optimize=True)
        return dict(indices=raw.copy(),gram=gram,matched=matched)

    def likelihoods(self,block,words):
        words=np.asarray(words,complex)
        if words.ndim!=2 or words.shape[1]!=len(block['indices']) or not np.isfinite(words).all():
            raise ValueError('candidate words must match block length')
        noise=self.model.noise
        rank=self.model.factor.shape[1]
        out=np.empty(len(words))
        for i,word in enumerate(words):
            coeff=np.r_[1.,word]
            gram=np.einsum('a,b,abpq->pq',coeff.conj(),coeff,block['gram'],optimize=True)
            matched=coeff.conj()@block['matched']
            precision=np.eye(rank)+gram/noise
            chol=np.linalg.cholesky(precision)
            whitened=np.linalg.solve(chol,matched/noise)
            out[i]=(-self.ynorm/noise+float(np.vdot(whitened,whitened).real)
                    -2*np.log(chol.diagonal().real).sum()-self.model.channel.n*np.log(np.pi*noise))
        if not np.isfinite(out).all():
            raise FloatingPointError('nonfinite block likelihood')
        return out


def pair_pass(model,y,pilot,incoming):
    """One disjoint pair pass; every external data coordinate remains zero.

    No previous block output is fed into a later block. The pair's own incoming
    bit factor is deleted from its outgoing message by exact finite summation.
    """
    n=model.channel.n
    incoming=np.asarray(incoming,float)
    if incoming.shape!=(2*n,) or not np.isfinite(incoming).all():
        raise ValueError('finite all-I then all-Q incoming bit LLRs required')
    kernel=PairLikelihood(model,y,pilot)
    app=np.empty(2*n);ext=np.empty(2*n)
    counts=[]
    for start in range(0,n,2):
        indices=np.arange(start,min(n,start+2))
        words,bits=enumerate_qpsk(len(indices))
        block=kernel.block(indices)
        likelihood=kernel.likelihoods(block,words)
        bit_indices=np.r_[indices,indices+n]
        app[bit_indices],ext[bit_indices]=bit_extrinsic(likelihood,bits,incoming[bit_indices])
        counts.append(len(words))
    return dict(app=app,extrinsic=ext,blocks=len(counts),likelihood_evaluations=sum(counts),
                fft_count=2+n, external_reference='data zero everywhere outside current block',
                schedule='disjoint adjacent pairs, simultaneous fixed reference, one pass')


CONFIG=dict(seed=[20261003,104129,80,61],independent_draws=3,n=[2,4],p=2,
            noise=.2,pilot_energy=.5,data_energy=.5,gain_prior='CN(0,I/P)',
            geometries='delay [0,1], Doppler [.23,-.38]',
            external_reference='zero-soft-mean (deterministic cavity, not legal QPSK support)',
            block_size=2,chirps='c1=.37/N,c2=.13/N^2 (nontrivial CPP stress, not production setting)',
            quote=dict(n=1024,p=8,repeats=3,minimum_safety_multiplier=3,
                       residual_cpu_reserve_seconds=20,absolute_quote_cap_seconds=180),
            likelihood_tolerance=1e-9,n2_llr_tolerance=1e-10,own_edge_tolerance=1e-10,
            source_registration='message-r1_registration.json',receiver_calls=0,decoder_calls=0)


def probability_error(reference,actual):
    p=expit(reference);q=expit(actual)
    kl=xlogy(p,p)+xlogy(1-p,1-p)+p*np.logaddexp(0,-actual)+(1-p)*np.logaddexp(0,actual)
    return dict(llr_rmse=float(np.sqrt(np.mean((reference-actual)**2))),
                probability_mse=float(np.mean((p-q)**2)),bernoulli_kl=float(np.mean(kl)))


def make_model(n,p):
    delays=[0,1] if p==2 else np.arange(p)
    dopplers=[.23,-.38] if p==2 else np.linspace(-.4,.7,p)
    channel=PHYSICAL.Channel(n,.37/n,.13/n**2,delays,dopplers,np.ones(p))
    return CollapsedModel(channel,np.zeros(p),np.eye(p)/p,CONFIG['noise'])


def calculate(output):
    started=time.monotonic();cpu_started=time.process_time()
    rng=np.random.default_rng(CONFIG['seed'])
    records=[]
    for draw in range(CONFIG['independent_draws']):
        for n in CONFIG['n']:
            model=make_model(n,2)
            operators=dense_operators(model.channel)
            words,bits=enumerate_qpsk(n)
            incoming=.6*rng.normal(size=2*n)
            logprior=.5*(1-2*bits)@incoming
            prior=np.exp(logprior-logsumexp(logprior))
            pilot=np.sqrt(CONFIG['pilot_energy'])*np.exp(.3j*np.arange(n))
            gain=(rng.normal(size=2)+1j*rng.normal(size=2))/2
            data=words[rng.choice(len(words),p=prior)]
            y=np.einsum('p,pij,j->i',gain,operators,pilot+data)+np.sqrt(CONFIG['noise']/2)*(rng.normal(size=n)+1j*rng.normal(size=n))
            # Truth enters only generation; both reference and candidate receive
            # y, pilot, geometry and the same Gaussian/incoming prior.
            exact=exact_posterior(y,operators,pilot,words,np.zeros(2),np.eye(2)/2,CONFIG['noise'],bits=bits,prior_probabilities=prior)
            pair=pair_pass(model,y,pilot,incoming)
            kernel=PairLikelihood(model,y,pilot)
            full_errors=[];own_errors=[];single=np.empty(2*n)
            for start in range(0,n,2):
                indices=np.arange(start,min(n,start+2))
                local_words,local_bits=enumerate_qpsk(len(indices))
                block=kernel.block(indices)
                fast=kernel.likelihoods(block,local_words)
                full=[]
                for word in local_words:
                    x=pilot.copy();x[indices]+=word
                    full.append(model.evaluate(y,x)['log_likelihood'])
                full_errors.extend(abs(fast-np.array(full)))
                ids=np.r_[indices,indices+n]
                _,ext=bit_extrinsic(fast,local_bits,incoming[ids])
                for j in range(len(ids)):
                    modified=incoming[ids].copy();modified[j]+=1.7
                    _,changed=bit_extrinsic(fast,local_bits,modified)
                    own_errors.append(abs(ext[j]-changed[j]))
            for symbol in range(n):
                local_words,local_bits=enumerate_qpsk(1)
                likelihood=kernel.likelihoods(kernel.block([symbol]),local_words)
                ids=np.array([symbol,symbol+n])
                single[ids],_=bit_extrinsic(likelihood,local_bits,incoming[ids])
            index=len(records)
            np.savez(output/f'case_{index:02d}.npz',y=y,pilot=pilot,operators=operators,
                     gain_mean=np.zeros(2),gain_cov=np.eye(2)/2,noise=CONFIG['noise'],
                     words=words,bits=bits,incoming=incoming,prior=prior,exact_llr=exact.llr,
                     pair_app=pair['app'],pair_extrinsic=pair['extrinsic'],single_app=single,
                     fast_full_errors=full_errors,own_edge_errors=own_errors)
            records.append(dict(case=index,draw=draw,n=n,full_oracle_words=len(words),
                                pair=probability_error(exact.llr,pair['app']),single=probability_error(exact.llr,single),
                                fast_full_likelihood_error=float(max(full_errors)),own_edge_error=float(max(own_errors)),
                                blocks=pair['blocks'],local_likelihood_evaluations=pair['likelihood_evaluations']))
    dump(output/'mathematical_raw.json',records)
    if max(r['fast_full_likelihood_error'] for r in records)>CONFIG['likelihood_tolerance'] or max(r['own_edge_error'] for r in records)>CONFIG['own_edge_tolerance']:
        raise AssertionError('pair exact local factor contract failed')
    if max(r['pair']['llr_rmse'] for r in records if r['n']==2)>CONFIG['n2_llr_tolerance']:
        raise AssertionError('whole N=2 pair does not match exact marginal')
    n,p,repeats=1024,8,CONFIG['quote']['repeats']
    pilot=np.sqrt(CONFIG['pilot_energy'])*np.exp(.3j*np.arange(n))
    y=rng.normal(size=n)+1j*rng.normal(size=n)
    incoming=.6*rng.normal(size=2*n)
    # Quote observation is exogenous arithmetic input, not a generated
    # production frame and not communication-performance evidence.
    quote_start=time.perf_counter();quote_cpu=time.process_time()
    model=make_model(n,p)
    kernel=PairLikelihood(model,y,pilot)
    setup_wall=time.perf_counter()-quote_start;setup_cpu=time.process_time()-quote_cpu
    quote_start=time.perf_counter();quote_cpu=time.process_time()
    local_words,local_bits=enumerate_qpsk(2)
    local_ll=kernel.likelihoods(kernel.block([0,1]),local_words)
    bit_extrinsic(local_ll,local_bits,incoming[[0,1,n,n+1]])
    pair_wall=time.perf_counter()-quote_start;pair_cpu=time.process_time()-quote_cpu
    estimated_cpu=repeats*(setup_cpu+(n//2)*pair_cpu)
    estimated_wall=repeats*(setup_wall+(n//2)*pair_wall)
    safety=CONFIG['quote']['minimum_safety_multiplier']
    spent_cpu=time.process_time()-cpu_started;spent_wall=time.monotonic()-started
    admitted=(safety*estimated_cpu+spent_cpu+20<180 and safety*estimated_wall+spent_wall+20<240)
    preliminary=dict(setup_cpu_seconds=setup_cpu,setup_wall_seconds=setup_wall,
                     one_pair_cpu_seconds=pair_cpu,one_pair_wall_seconds=pair_wall,
                     estimated_three_pass_cpu_seconds=estimated_cpu,estimated_three_pass_wall_seconds=estimated_wall,
                     safety_multiplier=safety,admitted=admitted,already_spent_cpu_seconds=spent_cpu,
                     complete_pass_includes='model/setup, zero reference, each pair bases/Gram/16 solves, bit APP/extrinsic, output assembly and NPZ write',
                     excludes='data generation/imports, receiver/decoder; preliminary one-pair estimate excludes final NPZ write',
                     environment='one effective thread; shared-machine arithmetic quote')
    dump(output/'preliminary_quote.json',preliminary)
    full_quote_ll=[]
    for word in local_words:
        x=pilot.copy();x[:2]+=word
        full_quote_ll.append(model.evaluate(y,x)['log_likelihood'])
    quote_error=float(np.max(abs(local_ll-full_quote_ll)))
    np.savez(output/'quote_reference.npz',y=y,pilot=pilot,local_words=local_words,
             fast_likelihood=local_ll,full_evaluate_likelihood=full_quote_ll)
    if quote_error>CONFIG['likelihood_tolerance']:
        raise AssertionError('N1024 shared Gram fails full evaluate reference')
    timings=[]
    if admitted:
        for repeat in range(repeats):
            trial=time.perf_counter();trial_cpu=time.process_time()
            complete_model=make_model(n,p)
            result=pair_pass(complete_model,y,pilot,incoming)
            # Persist every result, including actual NPZ writes in the quote.
            np.savez(output/f'quote_{repeat:02d}.npz',y=y,pilot=pilot,incoming=incoming,
                     app=result['app'],extrinsic=result['extrinsic'])
            elapsed=time.perf_counter()-trial;cpu=time.process_time()-trial_cpu
            timings.append(dict(repeat=repeat,wall_seconds=elapsed,cpu_seconds=cpu,
                                blocks=result['blocks'],likelihood_evaluations=result['likelihood_evaluations'],
                                fft_count=result['fft_count']))
    dump(output/'quote_results.json',dict(status='complete' if admitted else 'not_completed_quote_exceeds_cap',
                                        preliminary=preliminary,repeats=timings,
                                        fast_full_likelihood_error=quote_error,
                                        process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                        rss_scope='macOS whole-process cumulative high-water mark, not incremental method peak'))
    return dict(status='complete_local_diagnostic',cases=records,
                per_n={str(n):{method:{metric:float(np.mean([r[method][metric] for r in records if r['n']==n]))
                                      for metric in records[0][method]} for method in ['single','pair']} for n in CONFIG['n']},
                max_fast_full_likelihood_error=max(r['fast_full_likelihood_error'] for r in records),
                max_own_edge_error=max(r['own_edge_error'] for r in records),
                n1024_fast_full_likelihood_error=quote_error,
                quote_status='complete' if admitted else 'not_completed_quote_exceeds_cap',quote_repeats=timings,
                full_receiver_admission='not_established; outside-block nuisance uncertainty and receiver schedule/cavity closure remain',
                performance_claim='not_tested')


if __name__=='__main__':
    run('message_v2',CONFIG,[*SOURCES,Path(__file__).with_name('message.py'),__file__,
                            ARTIFACT/'message-r1_registration.json'],calculate)
