"""Uniform-external Gaussian moment matching for bounded data blocks.

Exact conditional second moments, approximate Gaussian likelihood. Observation
and pilot inputs are DAFT-domain vectors; computations use the frozen CPP time
operators. This one-pass detector is not the native iterative receiver.
"""
from pathlib import Path
import sys
import time
import resource
import itertools

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from experiments.afdm_structured_inference_20261003.collapsed import CollapsedModel,PHYSICAL,SOURCES,dense_operators
from experiments.afdm_structured_inference_20261003.message import bit_extrinsic
from experiments.afdm_structured_inference_20261003.pair_message import PairLikelihood,pair_pass,probability_error
from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk,exact_posterior
from experiments.afdm_structured_inference_20261003.common import run,dump,ARTIFACT


def chol_solve(chol,rhs):
    return np.linalg.solve(chol.conj().T,np.linalg.solve(chol,rhs))


class GaussianPairLikelihood(PairLikelihood):
    def __init__(self,model,y,pilot,external_variance=.5):
        super().__init__(model,y,pilot)
        c=model.channel
        if np.any(model.mean!=0) or not np.allclose(model.factor@model.factor.conj().T,np.eye(c.p)/c.p,atol=1e-14,rtol=1e-14):
            raise ValueError('moment-matched kernel requires zero-mean iid CN(0,I/P) gains')
        if not np.isscalar(external_variance) or np.iscomplexobj(external_variance) or not np.isfinite(external_variance) or external_variance<0:
            raise ValueError('external scalar variance must be finite and nonnegative')
        self.variance=float(external_variance)

    def block(self,indices):
        indices=np.asarray(indices)
        c=self.model.channel;n=c.n
        if (indices.ndim!=1 or len(indices) not in (1,2) or not np.issubdtype(indices.dtype,np.integer)
                or len(np.unique(indices))!=len(indices) or np.any(indices<0) or np.any(indices>=n)):
            raise ValueError('one or two distinct legal integer indices required')
        directions=[]
        for index in indices:
            unit=np.zeros(n,complex);unit[index]=1
            directions.append(self.model.ops.responses_time(PHYSICAL.daft(unit,c.c1,c.c2,True))@self.model.factor)
        d=np.sqrt(self.variance)*np.concatenate(directions,axis=1)
        scale=self.model.noise+self.variance
        # D D^H <= external_variance I, so R >= noise/scale I.
        # No signed determinant, eigenvalue clipping, or covariance jitter.
        r=np.eye(d.shape[1])-d.conj().T@d/scale
        chol_r=np.linalg.cholesky(r)
        def inverse_base(z):
            return z/scale+d@chol_solve(chol_r,d.conj().T@z)/(scale*scale)
        stacked=np.stack([self.t0,*directions])
        columns=stacked.transpose(1,0,2).reshape(n,-1)
        inverse_columns=inverse_base(columns).reshape(n,len(stacked),c.p).transpose(1,0,2)
        gram=np.einsum('anp,bnq->abpq',stacked.conj(),inverse_columns,optimize=True)
        inverse_y=inverse_base(self.yt)
        matched=np.einsum('anp,n->ap',stacked.conj(),inverse_y,optimize=True)
        logdet_base=n*np.log(scale)+2*np.log(chol_r.diagonal().real).sum()
        constant=-n*np.log(np.pi)-logdet_base-float(np.vdot(self.yt,inverse_y).real)
        return dict(indices=indices.copy(),gram=gram,matched=matched,constant=float(constant),
                    downdate_min_eigenvalue_lower_bound=self.model.noise/scale,
                    downdate_rank_bound=d.shape[1])

    def likelihoods(self,block,words):
        words=np.asarray(words,complex)
        if words.ndim!=2 or words.shape[1]!=len(block['indices']) or not np.isfinite(words).all():
            raise ValueError('finite local words must match block dimension')
        out=np.empty(len(words))
        for index,word in enumerate(words):
            coeff=np.r_[1.,word]
            gram=np.einsum('a,b,abpq->pq',coeff.conj(),coeff,block['gram'],optimize=True)
            matched=coeff.conj()@block['matched']
            chol=np.linalg.cholesky(np.eye(self.model.channel.p)+gram)
            whitened=np.linalg.solve(chol,matched)
            out[index]=block['constant']+float(np.vdot(whitened,whitened).real)-2*np.log(chol.diagonal().real).sum()
        if not np.isfinite(out).all():
            raise FloatingPointError('nonfinite Gaussian pair likelihood')
        return out


def gaussian_pair_pass(model,y,pilot,incoming,*,block_size=2,external_variance=.5):
    n=model.channel.n
    incoming=np.asarray(incoming,float)
    if incoming.shape!=(2*n,) or not np.isfinite(incoming).all() or np.any(incoming!=0):
        raise ValueError('only exactly uniform incoming bit priors are supported')
    if isinstance(block_size,bool) or not isinstance(block_size,int) or block_size not in (1,2):
        raise ValueError('block_size must be one or two')
    kernel=GaussianPairLikelihood(model,y,pilot,external_variance)
    app=np.empty(2*n);ext=np.empty(2*n);blocks=0;calls=0
    for start in range(0,n,block_size):
        indices=np.arange(start,min(n,start+block_size))
        words,bits=enumerate_qpsk(len(indices))
        loglike=kernel.likelihoods(kernel.block(indices),words)
        ids=np.r_[indices,indices+n]
        app[ids],ext[ids]=bit_extrinsic(loglike,bits,incoming[ids])
        blocks+=1;calls+=len(words)
    return dict(app=app,extrinsic=ext,blocks=blocks,likelihood_evaluations=calls,
                fft_count=n+2,probability_object='CN moment-matched outside uniform independent QPSK',
                observation_domain='DAFT',schedule='single pass, no feedback')


def dense_covariance(model,operators,pilot,indices,word,variance=.5):
    n=model.channel.n;p=model.channel.p
    x=np.array(pilot,dtype=complex,copy=True);x[indices]+=word
    b=np.einsum('pij,j->ip',operators,x)
    outside=np.setdiff1d(np.arange(n),indices)
    rest=sum(op[:,outside]@op[:,outside].conj().T for op in operators)*(variance/p)
    covariance=model.noise*np.eye(n)+rest+b@b.conj().T/p
    return covariance


def enumerated_second_moment(model,operators,pilot,indices,word):
    """Exact expectation of y y^H over outside QPSK and analytic zero-mean gains."""
    n=model.channel.n;p=model.channel.p
    outside=np.setdiff1d(np.arange(n),indices)
    if len(outside):
        outside_words,_=enumerate_qpsk(len(outside))
    else:
        outside_words=np.empty((1,0),complex)
    total=np.zeros((n,n),complex)
    for outside_word in outside_words:
        x=np.array(pilot,dtype=complex,copy=True);x[indices]+=word;x[outside]+=outside_word
        b=np.einsum('pij,j->ip',operators,x)
        total+=model.noise*np.eye(n)+b@b.conj().T/p
    return total/len(outside_words)


def dense_log_likelihood(y,covariance):
    sign,logdet=np.linalg.slogdet(covariance)
    if abs(sign-1)>1e-10:
        raise FloatingPointError('dense covariance determinant is not positive')
    return float(-len(y)*np.log(np.pi)-logdet-np.vdot(y,np.linalg.solve(covariance,y)).real)


CONFIG=dict(seed=[20261003,104129,80,62],independent_draws_per_size=3,n=[2,4],small_p=2,
            noise=.2,pilot_energy=.5,data_energy=.5,gain_prior='CN(0,I/P)',incoming='uniform only',
            block_sizes=[1,2],large=dict(n=1024,p=8,repeats=3,safety_multiplier=3),
            tolerance=dict(likelihood=1e-9,second_moment=1e-10,n2_exact_llr=1e-10),
            source_registration='message-r2_registration.json',final_message_mechanism_revision=True,
            receiver_calls=0,decoder_calls=0)


def make_model(n,p):
    channel=PHYSICAL.Channel(n,.37/n,.13/n**2,np.arange(p)%n,
                            [.23,-.38] if p==2 else np.linspace(-.4,.7,p),np.ones(p))
    return CollapsedModel(channel,np.zeros(p),np.eye(p)/p,CONFIG['noise'])


def calculate(output):
    started=time.monotonic();cpu_started=time.process_time()
    rng=np.random.default_rng(CONFIG['seed']);records=[]
    for draw,n in itertools.product(range(CONFIG['independent_draws_per_size']),CONFIG['n']):
        model=make_model(n,2);ops=dense_operators(model.channel)
        pilot=np.sqrt(.5)*np.exp(.3j*np.arange(n));incoming=np.zeros(2*n)
        words,bits=enumerate_qpsk(n)
        gains=(rng.normal(size=2)+1j*rng.normal(size=2))/2
        data=words[rng.integers(len(words))]
        y=np.einsum('p,pij,j->i',gains,ops,pilot+data)+np.sqrt(.2/2)*(rng.normal(size=n)+1j*rng.normal(size=n))
        # Both candidate and exact reference receive only observed inputs and
        # declared priors. Generated gains/data are not reference arguments.
        exact=exact_posterior(y,ops,pilot,words,[0,0],np.eye(2)/2,.2,bits=bits)
        r1=pair_pass(model,y,pilot,incoming)
        pair=gaussian_pair_pass(model,y,pilot,incoming)
        single=gaussian_pair_pass(model,y,pilot,incoming,block_size=1)
        kernel=GaussianPairLikelihood(model,y,pilot)
        ll_errors=[];moment_errors=[];local_raw={}
        for block_number,start in enumerate(range(0,n,2)):
            indices=np.arange(start,min(n,start+2));local_words,_=enumerate_qpsk(len(indices))
            ll=kernel.likelihoods(kernel.block(indices),local_words)
            dense_ll=[];covariances=[];enumerated=[]
            for word in local_words:
                cov=dense_covariance(model,ops,pilot,indices,word)
                exact_moment=enumerated_second_moment(model,ops,pilot,indices,word)
                dense_ll.append(dense_log_likelihood(y,cov));covariances.append(cov);enumerated.append(exact_moment)
                moment_errors.append(float(np.linalg.norm(cov-exact_moment)))
            ll_errors.extend(abs(ll-np.array(dense_ll)))
            local_raw.update({f'block_{block_number}_indices':indices,
                              f'block_{block_number}_fast_likelihood':ll,
                              f'block_{block_number}_dense_likelihood':dense_ll,
                              f'block_{block_number}_dense_covariance':covariances,
                              f'block_{block_number}_enumerated_second_moment':enumerated})
        index=len(records)
        np.savez(output/f'case_{index:02d}.npz',y=y,pilot=pilot,operators=ops,incoming=incoming,
                 noise=.2,gain_cov=np.eye(2)/2,words=words,bits=bits,exact_llr=exact.llr,
                 r1_app=r1['app'],r2_pair_app=pair['app'],r2_pair_extrinsic=pair['extrinsic'],
                 r2_single_app=single['app'],**local_raw)
        records.append(dict(case=index,draw=draw,n=n,r1=probability_error(exact.llr,r1['app']),
                            r2_pair=probability_error(exact.llr,pair['app']),r2_single=probability_error(exact.llr,single['app']),
                            fast_dense_likelihood_error=float(max(ll_errors)),second_moment_error=float(max(moment_errors)),
                            app_extrinsic_equal=bool(np.array_equal(pair['app'],pair['extrinsic']))))
    dump(output/'mathematical_raw.json',records)
    if max(r['fast_dense_likelihood_error'] for r in records)>CONFIG['tolerance']['likelihood'] or max(r['second_moment_error'] for r in records)>CONFIG['tolerance']['second_moment']:
        raise AssertionError('Gaussian pair likelihood/second-moment contract failed')
    if max(r['r2_pair']['llr_rmse'] for r in records if r['n']==2)>CONFIG['tolerance']['n2_exact_llr']:
        raise AssertionError('N2 full block does not recover exact likelihood')
    n,p,repeats=1024,8,3
    y=rng.normal(size=n)+1j*rng.normal(size=n);pilot=np.sqrt(.5)*np.exp(.3j*np.arange(n));incoming=np.zeros(2*n)
    wall=time.perf_counter();cpu=time.process_time()
    model=make_model(n,p);kernel=GaussianPairLikelihood(model,y,pilot)
    setup_wall=time.perf_counter()-wall;setup_cpu=time.process_time()-cpu
    wall=time.perf_counter();cpu=time.process_time()
    local_words,local_bits=enumerate_qpsk(2)
    first_ll=kernel.likelihoods(kernel.block([0,1]),local_words)
    bit_extrinsic(first_ll,local_bits,np.zeros(4))
    pair_wall=time.perf_counter()-wall;pair_cpu=time.process_time()-cpu
    estimated_cpu=repeats*(setup_cpu+n/2*pair_cpu);estimated_wall=repeats*(setup_wall+n/2*pair_wall)
    admitted=(3*estimated_cpu+time.process_time()-cpu_started+20<180
              and 3*estimated_wall+time.monotonic()-started+20<240)
    quote=dict(setup_cpu_seconds=setup_cpu,setup_wall_seconds=setup_wall,
               one_pair_cpu_seconds=pair_cpu,one_pair_wall_seconds=pair_wall,
               estimated_three_pass_cpu_seconds=estimated_cpu,estimated_three_pass_wall_seconds=estimated_wall,
               safety_multiplier=3,admitted=admitted,
               includes='complete model/phase/prior/cache setup, all blocks/solves/transforms, APP/ext assembly, actual NPZ write',
               excludes='imports/input generation, observed geometry/receiver initialization, native iterations, LDPC; preliminary estimate omits final NPZ write',
               scope='single-thread shared-machine arithmetic quote')
    dump(output/'preliminary_quote.json',quote)
    timings=[]
    if admitted:
        for repeat in range(repeats):
            wall=time.perf_counter();cpu=time.process_time()
            complete_model=make_model(n,p)
            result=gaussian_pair_pass(complete_model,y,pilot,incoming)
            np.savez(output/f'quote_{repeat:02d}.npz',y=y,pilot=pilot,incoming=incoming,app=result['app'],extrinsic=result['extrinsic'])
            timings.append(dict(repeat=repeat,wall_seconds=time.perf_counter()-wall,cpu_seconds=time.process_time()-cpu,
                                blocks=result['blocks'],likelihood_evaluations=result['likelihood_evaluations'],fft_count=result['fft_count']))
    dump(output/'quote_results.json',dict(status='complete' if admitted else 'not_completed_quote_exceeds_cap',
                                        preliminary=quote,repeats=timings,
                                        process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                        rss_scope='macOS whole-process cumulative high-water mark, not isolated method peak'))
    return dict(cases=records,
                per_n={str(n):{method:{key:float(np.mean([r[method][key] for r in records if r['n']==n]))
                                      for key in records[0][method]} for method in ['r1','r2_pair','r2_single']} for n in CONFIG['n']},
                max_fast_dense_likelihood_error=max(r['fast_dense_likelihood_error'] for r in records),
                max_second_moment_error=max(r['second_moment_error'] for r in records),
                quote_status='complete' if admitted else 'not_completed_quote_exceeds_cap',quote_repeats=timings,
                probability_object='approximate Gaussian likelihood with exact conditional second moment under uniform external QPSK/zero-mean iid Gaussian gain prior',
                production_utility='not_tested',native_iterative_replacement='not_supported_by_this_interface')


if __name__=='__main__':
    run('message_v3',CONFIG,[*SOURCES,Path(__file__).with_name('message.py'),Path(__file__).with_name('pair_message.py'),
                            __file__,ARTIFACT/'message-r2_registration.json'],calculate)
