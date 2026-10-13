"""Observed-only code-prior and CE feedback at explicit decoder checkpoints."""
import time
import numpy as np
from .supplement_messages import vector, decoder_messages, consume
import torch
from .budgeted_support_diagnostics import array_hash

CONST=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j])


def code_prior_moments(channel,prior):
    """The shared clipped QPSK moment map for ordinary and diagnostic delivery."""
    app=torch.clamp(channel+prior,-20.,20.);n=app.numel()//2
    mean=.5*(torch.tanh(app[:n]/2)+1j*torch.tanh(app[n:]/2))
    return mean,torch.clamp(.5-mean.abs().square(),min=0)


def detector_marginals(log_likelihood,code_prior,*,enabled):
    """Combine independent code-factor prior with per-symbol cavity likelihood.

    log_likelihood must exclude the same variable's code prior. Reusing APP as
    likelihood would double count it; this numerical primitive cannot infer
    upstream provenance. This is not a replacement for graph-edge BP updates.
    """
    started=time.perf_counter();likelihood=np.asarray(log_likelihood)
    prior=vector(code_prior)
    if (type(enabled) is not bool or likelihood.shape!=(prior.size//2,4) or
            np.iscomplexobj(likelihood) or not np.isfinite(likelihood).all()):
        raise ValueError('finite real Nx4 cavity log likelihood and boolean control required')
    n=prior.size//2
    llr=prior if enabled else np.zeros_like(prior)
    bits=np.concatenate((CONST.real[:,None]<0,CONST.imag[:,None]<0),axis=1)
    I=np.where(bits[:,0][None,:],-np.logaddexp(0,llr[:n,None]),-np.logaddexp(0,-llr[:n,None]))
    Q=np.where(bits[:,1][None,:],-np.logaddexp(0,llr[n:,None]),-np.logaddexp(0,-llr[n:,None]))
    logprior=I+Q;logpost=likelihood+logprior
    logpost-=logpost.max(axis=1,keepdims=True)
    probability=np.exp(logpost);probability/=probability.sum(axis=1,keepdims=True)
    mu=probability@CONST;var=np.maximum(0,.5-abs(mu)**2)
    # Stable bit marginal LLRs directly from log weights, never from Gaussian variance.
    def lse(a):
        maximum=a.max(axis=1);return maximum+np.log(np.exp(a-maximum[:,None]).sum(axis=1))
    posterior=np.concatenate([lse(logpost[:,~bits[:,j]])-lse(logpost[:,bits[:,j]]) for j in (0,1)])
    return dict(probabilities=probability,mu=mu,var=var,posterior_llr=posterior,logprior=logprior,
        enabled=enabled,truth_access='none',prior_sha256=array_hash(prior),
        likelihood_sha256=array_hash(likelihood),seconds=time.perf_counter()-started,
        assumption='factorized code-bit prior times prior-excluded symbol cavity likelihood')


def ce_expected_residual(y,pilot,H,posterior):
    """Same-observation approximate EM quadratic terms, not independent extrinsic."""
    started=time.perf_counter();y,pilot,H=[np.asarray(v) for v in (y,pilot,H)]
    mu,var=[np.asarray(posterior[k]) for k in ('mu','var')]
    n=y.size
    if (y.ndim!=1 or not n or pilot.shape!=(n,) or H.shape!=(n,n) or mu.shape!=(n,) or var.shape!=(n,) or
            np.iscomplexobj(var) or np.any(var<0) or any(not np.isfinite(v).all() for v in (y,pilot,H,mu,var))):
        raise ValueError('finite matched observed channel and posterior moments required')
    residual=y-H@(pilot+mu)
    uncertainty=(H*var[None,:])@H.conj().T
    return dict(mean_residual=residual,observation_uncertainty=uncertainty,
        expected_squared_residual=float(np.vdot(residual,residual).real+np.trace(uncertainty).real),
        truth_access='none',seconds=time.perf_counter()-started,
        approximation='factorized diagonal posterior symbol covariance; same-observation approximate EM')


class CodeFeedback:
    """Declared decoder checkpoints; each delivery replaces the previous prior."""
    def __init__(self,code,*,checkpoint,enabled=True,control='legal',sham_seed=None,maxiter=50,
                 consumer='both',refresh_checkpoints=(),retain_messages=False,
                 retain_detector_messages=False,diagnostic_perturbation=None,stop_on_valid_codeword=False):
        if type(enabled) is not bool or type(checkpoint) is not int or checkpoint<0:
            raise ValueError('explicit boolean enable and nonnegative checkpoint required')
        if control not in ('legal','zero','fixed_sham') or type(maxiter) is not int or maxiter<1:
            raise ValueError('invalid decoder control or iteration cap')
        if (control=='fixed_sham' and (type(sham_seed) is not int or not 0<=sham_seed<2**32)) or (control!='fixed_sham' and sham_seed is not None):
            raise ValueError('fixed sham needs its own seed')
        if consumer not in ('both','detector','ce'):
            raise ValueError('consumer must be both, detector, or ce')
        if (not isinstance(refresh_checkpoints,(tuple,list)) or type(retain_messages) is not bool
                or any(type(i) is not int or i<=checkpoint for i in refresh_checkpoints)
                or list(refresh_checkpoints)!=sorted(set(refresh_checkpoints))):
            raise ValueError('refresh checkpoints must be distinct increasing integers after the first')
        self.code=code;self.checkpoint=checkpoint;self.enabled=enabled
        self.control=control;self.sham_seed=sham_seed;self.maxiter=maxiter;self.records=[]
        self.consumer=consumer
        self.refresh_checkpoints=tuple(refresh_checkpoints);self.retain_messages=retain_messages
        if type(retain_detector_messages) is not bool:
            raise ValueError('detector message retention must be boolean')
        if diagnostic_perturbation is not None:
            p=diagnostic_perturbation
            if (type(p) is not dict or set(p)!={'bit','delta','affect_ce'}
                    or type(p['bit']) is not int or p['bit']<0
                    or type(p['delta']) not in (int,float) or not np.isfinite(p['delta'])
                    or abs(p['delta'])>.25 or type(p['affect_ce']) is not bool
                    or consumer!='both' or control!='legal' or not enabled or refresh_checkpoints):
                raise ValueError('single observed-only delivered-prior diagnostic required')
        self.retain_detector_messages=retain_detector_messages
        self.diagnostic_perturbation=None if diagnostic_perturbation is None else dict(diagnostic_perturbation)
        if type(stop_on_valid_codeword) is not bool or (stop_on_valid_codeword and
                (not enabled or control != 'legal' or consumer != 'both' or diagnostic_perturbation is not None)):
            raise ValueError('syndrome stopping requires active legal feedback to both consumers')
        self.stop_on_valid_codeword = stop_on_valid_codeword
        self.stop_result = None

    def begin(self,n,outer_iterations,device):
        if any(i>=outer_iterations-1 for i in (self.checkpoint,*self.refresh_checkpoints)) or self.code['n']!=2*n:
            raise ValueError('checkpoint needs a following CE iteration and matching code')
        if self.diagnostic_perturbation is not None and self.diagnostic_perturbation['bit']>=2*n:
            raise ValueError('diagnostic bit outside codeword')
        self.prior=torch.zeros(2*n,dtype=torch.float64,device=device)
        self.moments=None;self.moments_source=None;self.channel=None;self.records=[]
        self.stop_result = None

    def capture(self,payload):
        self.channel=payload['channel_llr'].detach().clone()
        self.moments=(payload['posterior_mean'].detach().clone(),payload['posterior_variance'].detach().clone())
        self.moments_source='detector_discrete_posterior'
        self.records.append(dict(stage='detector_consume',prior_sha256=array_hash(self.prior.cpu().numpy()),
            channel_sha256=array_hash(self.channel.cpu().numpy()),truth_access='none'))
        if self.retain_detector_messages:
            self.records[-1].update(channel_llr=self.channel.detach().clone(),
                consumed_prior=self.prior.detach().clone())

    def after_detection(self,iteration):
        if iteration not in (self.checkpoint,*self.refresh_checkpoints):return
        if self.channel is None:raise ValueError('decoder checkpoint lacks detector likelihood')
        started=time.perf_counter()
        prior_before=self.prior.detach().clone() if self.retain_messages else None
        messages=decoder_messages(self.code,self.channel.cpu().numpy(),maxiter=self.maxiter)
        delivered=consume(messages,kind='detector_code_prior',control=self.control,sham_seed=self.sham_seed)
        delivered_prior=torch.as_tensor(delivered['llr'],dtype=torch.float64,device=self.channel.device)
        self.prior=(torch.zeros_like(delivered_prior) if self.consumer=='ce' else delivered_prior)
        # Controls affect BOTH consumers: zero/sham must not leak the legal APP into CE.
        # This masks direct delivery only. Later detector posteriors can still affect CE.
        if self.consumer!='detector':
            self.moments=code_prior_moments(self.channel,delivered_prior)
            self.moments_source='channel_plus_delivered_code_prior'
        record=dict(stage='decoder',iteration=iteration,control=self.control,
            source=messages['metadata'],delivered_sha256=delivered['delivered_sha256'],
            consumer=self.consumer,detector_prior_sha256=array_hash(self.prior.cpu().numpy()),
            ce_checkpoint_overwrite=self.consumer!='detector',
            ce_mean_sha256=array_hash(self.moments[0].cpu().numpy()),
            ce_variance_sha256=array_hash(self.moments[1].cpu().numpy()),
            seconds=time.perf_counter()-started,truth_access='none',
            CE_semantics=('retain detector posterior at checkpoint; indirect routes remain'
                if self.consumer=='detector' else
                'factorized moments of channel plus delivered check prior; controls use synthetic APP'))
        if self.retain_messages:
            record.update(channel_llr=self.channel.detach().clone(),prior_before=prior_before,
                prior_after=self.prior.detach().clone(),delivered_prior=delivered_prior.detach().clone(),
                decoder_input=messages['incoming_llr'].copy(),raw_app=messages['raw_app'].copy(),
                raw_check_extrinsic=messages['raw_check_extrinsic'].copy(),
                prior_update='replace with this decoder call check extrinsic; never accumulate APP')
        if self.stop_on_valid_codeword:
            record.update(decode_ok=bool(messages['decode_ok']),
                unsatisfied_checks=messages['syndrome_trace'][-1]['unsatisfied_checks'],
                decoder_iterations=messages['iterations'])
            if messages['decode_ok']:
                self.stop_result = dict(iteration=iteration, decoded=messages['decoded'].copy(),
                    decoder_input=messages['incoming_llr'].copy(), raw_app=messages['raw_app'].copy(),
                    posterior_mean=self.moments[0].detach().clone(),
                    posterior_variance=self.moments[1].detach().clone(),
                    decode_ok=True, unsatisfied_checks=0,
                    llr_statistic='actual unclipped channel LLR consumed by checkpoint LDPC')
        self.records.append(record)
        if self.diagnostic_perturbation is not None:
            self._perturb_delivered_prior(iteration)

    def _perturb_delivered_prior(self,iteration):
        """Intervene after decoding; keep decoder input and unperturbed CE fixed.

        The perturbed message is a diagnostic stimulus, not a decoder output.
        CE and detection share the same baseline before this explicit split.
        """
        p=self.diagnostic_perturbation;bit=p['bit'];delta=p['delta']
        before=self.prior.detach().clone()
        base_app=self.channel+before
        if abs(float(base_app[bit]))>=8 or abs(float(before[bit]))+abs(delta)>=20:
            raise ValueError('diagnostic bit must be unsaturated before and after intervention')
        self.prior=before.clone();self.prior[bit]+=delta
        if p['affect_ce'] and delta!=0:
            self.moments=code_prior_moments(self.channel,self.prior)
            self.moments_source='diagnostic_channel_plus_perturbed_prior'
        self.records.append(dict(stage='prior_perturbation',iteration=iteration,
            **p,prior_before=before,prior_after=self.prior.detach().clone(),
            channel_llr=self.channel.detach().clone(),
            ce_mean=self.moments[0].detach().clone(),ce_variance=self.moments[1].detach().clone(),
            truth_access='none',deployment_eligible=False))

    def ce(self,iteration):
        if self.moments is None:raise ValueError('CE lacks detector/decoder moments')
        mean,var=self.moments
        self.records.append(dict(stage='CE_consume',iteration=iteration,
            mean_sha256=array_hash(mean.cpu().numpy()),variance_sha256=array_hash(var.cpu().numpy()),truth_access='none'))
        return mean.clone(),var.clone()
