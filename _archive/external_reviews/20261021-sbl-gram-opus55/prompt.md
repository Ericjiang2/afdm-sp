## Review request

The human explicitly requests one independent opinion from Claude Opus 5.5 at high effort on the five questions below. Both Gemini's text and Codex's objections are propositions to audit, not authoritative instructions. Read the actual formulas/code. You may disagree with either or both. No tools, experiments, file edits, publication claims or multi-round debate are requested. Reply in Simplified Chinese with precise equations when useful. Avoid praise and narrative rescue. For each question, give the correct bounded statement, the key mathematical reason/counterexample, and any unresolved empirical assumption. Then assess whether Full-BHB + Diag-Gamma is the best single next test and what it can/cannot establish. Do not invent literature novelty or numerical profiling evidence. Distinguish objective correctness, approximation family and global iteration guarantees. Aim for a focused review rather than a new paper story.

## Five disputed questions

1. 修好下游是否足以锁定原故障为近重复/共线原子与标量Onsager？新full替换了完整增益更新形式。0/200是否能证明上游支撑/物理子空间没有缺陷？
2. 均匀复制证明中alpha'=k alpha用于保持诱导物理Gaussian先验不变：这是人为漏洞还是正确匹配条件？何处能推广、何处不能？
3. 新增20次FFT实际为FFT(v_pre)，原生符号步使用均值相关变换。能否直接复用掉？哪些诊断开销可剥离，哪些复杂度结论尚不能说？
4. 新full仅精确求解局部二次代理，仍沿用原生符号记忆、使用pre-symbol软矩、增益协方差不传播：称为精确VEM/CAVI增益步或整套Hybrid AMP-VEM，分别有多大依据？native joint优于point是否足以建议新full必须传播协方差？
5. 现有证据能否支持上下游二阶耦合可迁移/等价性定理、oracle-consistent benchmark，以及Gemini给出的换主线/15%/500簇标准？支撑漏径反例与工程价值/新颖性区分应如何处理？

## Observed facts, not interpretations

SP-AFDM data-aided sparse channel estimation/detection. Same200 OLD keys from50 shared frame clusters, U/G, physical rho .3, SNR7/8dB. Both saved SBL upstream outputs are fixed: scalar-Gamma L-diag and full-Gamma L-cov. Prior/support/h0 and source hashes are qualified; no new SBL fit or new frame. Same original decoder check prior. Native fixed/point/joint failure counts are4/40/23 for L-diag,15/11/2 for L-cov. New full soft-Gram:0/200 for either upstream; new diag(M):200/200 and198/200. Full LLR logloss means .189826/.189927 vs best native full-Gamma/joint .219107. Primary paired frame bootstrap10000 draws gives each full-minus-best FER -.010[-.025,0], logloss differences -.029281[-.034220,-.024547] and -.029180[-.032705,-.025687]. Native six baselines replay exactly; independent raw recount/bootstrap passes. Zero/200 is not zero population FER or noninferiority. No novelty claim.
Mean active support P is23.91 scalar-upstream (198 cases24, one16, one14) and23.345 full-upstream (154 cases24, range14..24).
New gain family uses M=B^HB+Gamma(v_pre), b=B^HY, alpha=noise*P from h~CN(0,I/P); h0 is initialization not prior center. Full solves(M+alpha I,b); diagonal solves(diag(diag M)+alpha I,b). Both set propagated gain variance0. Symbol means/variances are from finite QPSK marginals, not asserted exact Gaussian posteriors. Gain solve uses saved PRE-symbol moments that formed B; symbol step executes first, then applies saved-snapshot fit. New full surrogate covariance noise*Q^-1 is computed only for qualification and not propagated.
Uniform2x duplication of every atom, h0 split equally, and native coordinate variance1/(2P) preserve induced working Gaussian physical prior. Full20 trajectories/covariance/LLRs invariant in fixed synthetic and real probes; native point first aggregate update non-invariant. No arbitrary partial-duplicate or near-duplicate invariance claim was tested.
Instrumented median detector times42.73/42.62ms vs best native28.82ms; detector+decoder59.11/59.23 vs45.65ms. New20 has61FFTs versus native41: extraFFT(v_pre) in projected_variance.20 gain solves plus20 diagnostic covariance solves/eigvalsh/qualification Cholesky. Upstream SBL time excluded; no optimized end-to-end timing or speed prediction. All results exploratory, informed old-cohort screening.

## Declared derivation and boundaries

# Derivation Package: full versus diagonal soft-Gram gain block

Date: 2026-10-21. Internal diagnostic proposal, not a paper method claim.

## Target
Derive two matched point-gain updates differing only in soft-Gram off-diagonals. Establish uniform-duplicate invariance of the full block and verify a bounded prototype before deciding any 200-key experiment.

## Status
COHERENT AS STATED; independent algebra review and the two predetermined numerical qualification cases passed. This qualifies the local surrogate and implementation only.

## Invariant Object
Physical channel H=sum_p h_p U_p and the induced working Gaussian prior, not coordinate norms. U_p are the frozen unitary path operators in AF coordinates. A unitary observation rotation to the native time coordinates leaves all Gram/b-vector identities unchanged.

## Assumptions
At a gain step the available working symbol distribution has mean mu and diagonal nonnegative variance v. xbar=pilot+mu, and its uncertainty is the data-symbol uncertainty. This factorized working distribution is held fixed for the local gain fit; no claim is made that it is the exact posterior. Observation noise sigma2>0 is unchanged, and h~CN(0,I/P) is the existing zero-mean working prior. Observed h0 is initialization, not the center of a new prior. Propagated gain variance remains zero in both prototype arms. Every atom is uniformly duplicated k times for the invariance control.

## Notation
B=[U_p xbar], b=B^H y, Gamma(v)_{pq}=tr(U_p^H U_q diag(v)), M=B^H B+Gamma(v), alpha=sigma2*P. In native time coordinates B is TimePathOps.responses_time(IDAFT(xbar)) and y is IDAFT(observed y); Gamma is unchanged by this left-unitary rotation. The existing physical.projected_variance helper computes Gamma and must be checked against explicit small dense operators, including mixed delays and nonuniform v.

## Derivation Strategy
Use the expected squared observation residual plus the existing Gaussian gain prior as a LOCAL quadratic surrogate. Compare its full minimizer to a diagonal normal-matrix approximation; then prove aggregation commutes with the full solve. Do not describe this as a rederivation or exact correction of the entire native P-BiG-AMP iteration.

## Derivation Map
1. Exact expectation under the DECLARED working symbol distribution: E||y-B(x)h||^2=const-2Re(h^H b)+h^H M h.
2. Add sigma2*P||h||^2 from the working prior; the full positive-definite normal matrix is Q=M+alpha I.
3. Full mean h_full=solve(Q,b); optional surrogate covariance sigma2 Q^-1 is a local Gaussian quantity, not propagated by these point-mode prototypes.
4. Diagonal control h_diag=solve(diag(diag(M))+alpha I,b), identical inputs/ridge/timing.
5. Under B'=BD, Gamma'=D^H Gamma D, b'=D^H b, P'=kP, prove D h'_full=h_full. The diagonal projection does not generally commute with this transformation.

## Main Derivation
Both operations keep the same right-hand side, prior and symbol-update schedule. M is Hermitian PSD by construction; alpha>0 makes Q invertible even for exact duplicates. Do not add an undeclared ridge, pseudoinverse or fallback. A materially invalid covariance is a qualification error, not a clipping opportunity.

Let D=I_P kron ones(1,k), D D^H=k I, T=D^H/k, D T=I. Uniform duplication gives M'=D^H M D and alpha'=k alpha. Then

Q' T=(D^H M D+k alpha I)D^H/k = D^H(M+alpha I)=D^H Q.

Since Q is positive definite, h'=T h solves Q'h'=D^H b=b'. Thus D h'=h. Also D(sigma2 Q'^-1)D^H=sigma2 Q^-1. This is an exact identity of the local Gaussian surrogate. The prior pushforward is unchanged as in representation-invariance.md.

For diagonal M entries m_p, duplicated diagonal entries repeat m_p, so

(D h'_diag)_p=k b_p/(m_p+k alpha), versus (h_diag)_p=b_p/(m_p+alpha).

Their difference is (k-1)m_p b_p/[(m_p+k alpha)(m_p+alpha)], generally nonzero. This is a direct diagnostic of the removed cross-copy information, not a claim about which version has better FER.

Prototype schedule: at iteration t, use the PRE-symbol-update mu_(t-1),v_(t-1) that formed the existing B. Compute the symbol update exactly as in the native point schedule; then apply either full or diagonal gain fit to those same saved pre-update moments, with no extra gain damping or decoder feedback. This avoids a hidden old-versus-new-symbol timing difference between arms. Preserve all symbol/residual/damping equations and zero propagated gain variance. A native-gain branch of the same prototype must replay the frozen native point before interpreting either block arm. For full mode, matched H, symbol prior and all non-gain states imply equal next symbol moments; the aggregation identity then preserves H after the gain update. Induction gives duplicate-invariant symbol trajectories in exact arithmetic.

## Remarks and Interpretation
The paired FULL-versus-DIAG comparison isolates off-diagonal soft-Gram coupling within this surrogate-update family. Either block versus native point changes the gain-update family, including removal of its pseudo-observation/Onsager gain formula; that comparison cannot isolate off-diagonals. Upstream SBL Gamma choice remains a separate axis and is NOT replaced or recomputed by this test. Full soft Gram M includes both mean regressors and symbol uncertainty, so this is not a Gamma-only ablation.

## Boundaries and Non-Claims
No 200-key run, new physical frame, parameter tuning, evidence-based stopping step, production receiver replacement or claimed performance improvement in this stage. Validate one synthetic fixture and the already predetermined U/rho .3/7dB/frame9100 h0/prior. Decode outcomes are single-key descriptions. The best existing full-Gamma/joint receiver remains the eventual performance reference; new solve cost must be reported if extended. Representation invariance is not sufficient for useful FER, global convergence, near-duplicate causality or a new scientific contribution.

## Open Risks
Current native symbol messages and their memories were derived for a different gain update; a valid local quadratic solve does not make the hybrid schedule a globally coherent AMP/VI algorithm. The working symbol distribution reuses observations; it is not an independent sample or oracle. A negative or uninformative minimal result must be retained without automatically extending the cohort. Independent algebra/code review and the dense Gamma/duplicate gates are required before any outcome interpretation.

## Numerical Qualification (2026-10-21)
Frozen source5d2feb6e; gram_block_gate1 EXIT0, one CPU thread,5.11s total wall. Independent mixed-delay Gamma relative error1.676e-15 and minimum eigenvalue10.3275. Native clone has bit-exact output/state/trace parity in both cases; the real original point/h20/scores reproduce immutable run2. Full20 duplicate maximum relative physical differences5.398e-16 (synthetic) and4.426e-15 (real), final LLR maximum differences1.066e-14/2.056e-13. All-step non-gain states/traces and surrogate covariance pushforward pass fixed tolerances. Diagonal first-update relative physical differences.976126/.990782; independent saved-matrix diagonal difference residuals<=1.12e-16. Detailed receipts and the bounded readout are in experiments/sbl_freeze_replay_20261020/GRAM_BLOCK_SUMMARY.md. This is no new population-performance or real near-duplicate causal verdict.

Direct all-step LLR observation was missing from gate1 and was completed, without changing its sources or results, by the frozen return-preserving wrapper62f70a16 on the identical cases in gate2. All20 extrinsic/APP LLR differences are<=1.066e-14 synthetic/2.141e-13 real; every saved numerical algorithm field matches gate1 exactly (timings excluded). This completes numerical qualification, not an independent sample replication. Combined process wall10.11s.


## Actual new implementation

"""Local Gaussian soft-Gram point-gain prototypes; no covariance propagation."""
from __future__ import annotations
import time
import numpy as np

RTOL, ATOL = 1e-10, 1e-12


def solve_gain(B, Y, Gamma, noise, mode):
    """Matched full/diagonal normal systems with only the declared noise*P ridge."""
    started = time.perf_counter()
    B, Y, Gamma = np.asarray(B, complex), np.asarray(Y, complex), np.asarray(Gamma, complex)
    if (B.ndim != 2 or B.shape[1] < 1 or Y.shape != (B.shape[0],)
            or Gamma.shape != (B.shape[1], B.shape[1]) or mode not in ('full', 'diag')
            or not np.isfinite(noise) or noise <= 0
            or not all(np.isfinite(a).all() for a in (B, Y, Gamma))):
        raise ValueError('invalid gain-block inputs')
    if not np.allclose(Gamma, Gamma.conj().T, rtol=RTOL, atol=ATOL):
        raise ValueError('non-Hermitian Gamma')
    eigenvalues = np.linalg.eigvalsh(Gamma)
    if eigenvalues[0] < -(ATOL+RTOL*np.max(np.abs(eigenvalues))):
        raise ValueError('non-PSD Gamma')
    M, b = B.conj().T @ B+Gamma, B.conj().T @ Y
    alpha = float(noise)*B.shape[1]
    Q = (M if mode == 'full' else np.diag(np.diag(M)))+alpha*np.eye(B.shape[1])
    np.linalg.cholesky(Q)  # Qualification only; no ridge adjustment or fallback.
    h = np.linalg.solve(Q, b)
    covariance = noise*np.linalg.solve(Q, np.eye(B.shape[1]))
    normal_scale = np.linalg.norm(Q)*np.linalg.norm(h)+np.linalg.norm(b)
    normal_residual = float(np.linalg.norm(Q @ h-b))
    normal_relative = normal_residual/normal_scale if normal_scale > 0 else normal_residual
    covariance_relative = float(np.linalg.norm(Q @ covariance-noise*np.eye(B.shape[1])) /
        (np.linalg.norm(Q)*np.linalg.norm(covariance)+noise*np.sqrt(B.shape[1])))
    if (not np.isfinite(h).all() or not np.isfinite(covariance).all()
            or normal_relative > RTOL or covariance_relative > RTOL):
        raise FloatingPointError('gain-block solve residual/nonfinite result')
    detail = dict(M=M, b=b, Q=Q, covariance=covariance, alpha=alpha,
        gamma_min_eigenvalue=float(eigenvalues[0]), normal_relative_residual=float(normal_relative),
        covariance_relative_residual=covariance_relative, seconds=time.perf_counter()-started)
    return h, detail


def scalar_point(y, pilot, c, noise, *, native, physical, pd=.5, prior=None,
                 iterations=20, damping=.3, gain_block='native', record_states=False):
    """Frozen point-loop schedule; replace only its applied gain-update family.

    `native` and `physical` are explicitly qualified frozen modules. The native
    branch has the canonical output schema and must replay it before other arms.
    Full/diag use the same B and v_pre, then apply the fit after the symbol update.
    Their local covariance is retained for qualification only, never propagated.
    """
    y=np.asarray(y,complex);pilot=np.asarray(pilot,complex);n=c.n;P=c.p
    if y.shape!=(n,) or pilot.shape!=(n,) or noise<=0 or not np.isfinite(noise):raise ValueError('observation/noise')
    if iterations<1 or not 0<damping<=1 or gain_block not in ('native','full','diag'):raise ValueError('configuration')
    if not np.isfinite(y).all() or not np.isfinite(pilot).all():raise ValueError('nonfinite observations')
    if prior is None:prior=np.zeros(2*n)
    prior=np.asarray(prior,float)
    if prior.shape!=(2*n,) or not np.isfinite(prior).all() or pd<=0:raise ValueError('invalid code prior/data power')
    a,_=native.alphabet(pd);mu,v,_=native.moments(prior,pd);x=pilot+mu
    o=native.TimePathOps(c);Y=physical.daft(y,c.c1,c.c2,True)
    h=c.gains.copy();vh=0.;tau=1/P
    xb=x.copy();hb=h.copy();Bb=None;s=np.zeros(n,complex);sv=0.;bar0=None;vp0=None;trace=[];states=[];blocks=[]
    for it in range(iterations):
        xt=physical.daft(x,c.c1,c.c2,True);B=o.responses_time(xt);vx=float(v.mean());ex=float(np.vdot(x,x).real)
        v_pre=v.copy()
        channel_norm=o.power(h)
        bar=vx*channel_norm+P*vh*ex/n;vp=bar+P*vh*vx
        if bar0 is not None:bar=damping*bar+(1-damping)*bar0;vp=damping*vp+(1-damping)*vp0
        bar0=bar;vp0=vp
        z=B@h
        ph=z-s*bar
        s=damping*(Y-ph)/(noise+vp)+(1-damping)*s;sv=damping/(noise+vp)+(1-damping)*sv
        st=s
        xb=damping*x+(1-damping)*xb;hb=damping*h+(1-damping)*hb
        Bb=B.copy() if Bb is None else damping*B+(1-damping)*Bb
        data_precision=sv*o.power(hb);gain_precision=sv*np.vdot(xb,xb).real
        vr=1/max(data_precision,1e-12);vq=1/max(gain_precision,1e-12)
        adj=physical.daft(o.adjoint_time(hb,st),c.c1,c.c2)
        rx=x+vr*(adj-xb*(sv*P*vh))
        rh=h+vq*(Bb.conj().T@st-hb*sv*n*vx)
        ext,app,mu,v=native.marginal(-abs((rx-pilot)[:,None]-a)**2/vr,prior,pd);x=pilot+mu
        vh=0.
        if gain_block == 'native':
            h=tau*rh/(tau+vq)
        else:
            block_started=time.perf_counter()
            Gamma=physical.projected_variance(v_pre,c.delays,c.dopplers,c.c1)
            if not np.allclose(np.diag(Gamma),v_pre.sum(),rtol=RTOL,atol=ATOL):
                raise AssertionError('soft covariance diagonal differs from v_pre sum')
            h,detail=solve_gain(B,Y,Gamma,noise,gain_block)
            blocks.append({k:value for k,value in detail.items() if k not in ('M','b','Q')})
            blocks[-1].update(iteration=it,v_pre_sum=float(v_pre.sum()),v_post_sum=float(v.sum()),
                              solve_seconds=detail['seconds'],seconds=time.perf_counter()-block_started,gamma_fft_count=1)
        if not all(np.isfinite(q).all() for q in (h,mu,v,s)):raise FloatingPointError('nonfinite scalar joint update')
        trace.append(dict(iteration=it,data_variance=float(v.mean()),gain_variance=float(vh),
                          channel_norm_factor=float(channel_norm),pseudo_variance_bar=float(bar),
                          pseudo_variance_total=float(vp),data_pseudo_variance=float(vr),
                          gain_pseudo_variance=float(vq),output_precision=float(sv),
                          data_precision_floor=bool(data_precision<=1e-12),
                          gain_precision_floor=bool(gain_precision<=1e-12),
                          fft_count=2 if gain_block=='native' else 3))
        if record_states:states.append(dict(h=h.copy(),mu=mu.copy(),v=v.copy(),s=s.copy(),vr=vr,vq=vq,vh=vh,sv=sv,bar=bar,vp=vp))
    out=dict(extrinsic=ext,app=app,mu=mu,variance=v,gains=h,gain_variance=np.full(P,vh),trace=trace,iterations=iterations,
             fft_count=2*iterations+1 if gain_block=='native' else 3*iterations+1)
    if record_states:out['states']=states
    if gain_block!='native':
        out.update(gain_blocks=blocks,native_symbol_fft_count=2*iterations+1,gamma_fft_count=iterations,
                   gain_solve_calls=iterations,covariance_solve_calls=iterations)
    return out


## Frozen native operator and scalar_joint

"""Two-FFT realization of scalar-variance parametric bilinear AMP for SP-AFDM.
No dense channel/tensor, no independent time-domain QPSK prior, no tail deletion.
The inferential approximation is scalar P-BiG-AMP (Parker/Schniter); the exact
change is a unitary observation rotation and the path-operation contractions.
"""
import numpy as np
from scipy.optimize import minimize_scalar
from physical import Channel,daft,dkernel
from messages import alphabet,marginal,moments

class TimePathOps:
    def __init__(self,c):
        self.c=c;self.n=c.n;self.P=c.p;n=c.n;k=np.arange(n)
        if n<1 or self.P<1 or np.any(c.delays<0) or np.any(c.delays>=n):raise ValueError('invalid path dimensions/delays')
        if not np.isfinite(c.dopplers).all() or not np.isfinite(c.gains).all():raise ValueError('nonfinite paths')
        self.idx=(k[:,None]-c.delays)%n
        wrap=k[:,None]-c.delays
        cp=np.where(wrap<0,np.exp(2j*np.pi*c.c1*(n*n+2*n*wrap)),1.)
        self.phase=cp*np.exp(2j*np.pi*k[:,None]*c.dopplers/n)
        self.R=(c.delays[:,None]==c.delays[None,:])*dkernel(c.dopplers[None,:]-c.dopplers[:,None],n)
    def responses_time(self,xt):return self.phase*xt[self.idx]
    def adjoint_time(self,h,z):
        q=self.phase.conj()*z[:,None]*h.conj()
        return sum(np.roll(q[:,i],-int(l)) for i,l in enumerate(self.c.delays))
    def power(self,h):
        value=float(np.vdot(h,self.R@h).real)
        if value < -1e-10*max(float(np.vdot(h,h).real),1.):raise FloatingPointError('non-PSD physical norm')
        return max(value,0.)

def scalar_joint(y,pilot,c,noise,pd=.5,prior=None,iterations=20,damping=.3,gain_mode='joint',record_states=False,observation_domain='time'):
    """Observed-only detector. Gain prior CN(0,I/P), reused once per batch.
    c.gains is initialization, never an independent observation-derived prior.
    Fixed-gain and zero-variance gain-mean-update controls are explicitly named.
    In each iteration only one IDAFT (new x) and one DAFT (adjoint) are needed;
    B(xbar) is updated by linearity, not with an extra transform.
    """
    y=np.asarray(y,complex);pilot=np.asarray(pilot,complex);n=c.n;P=c.p
    if y.shape!=(n,) or pilot.shape!=(n,) or noise<=0 or not np.isfinite(noise):raise ValueError('observation/noise')
    if iterations<1 or not 0<damping<=1 or gain_mode not in ('joint','point','fixed') or observation_domain not in ('time','af'):raise ValueError('configuration')
    if not np.isfinite(y).all() or not np.isfinite(pilot).all():raise ValueError('nonfinite observations')
    if prior is None:prior=np.zeros(2*n)
    prior=np.asarray(prior,float)
    if prior.shape!=(2*n,) or not np.isfinite(prior).all() or pd<=0:raise ValueError('invalid code prior/data power')
    a,_=alphabet(pd);mu,v,_=moments(prior,pd);x=pilot+mu
    o=TimePathOps(c);Y=daft(y,c.c1,c.c2,True) if observation_domain=='time' else y.copy()
    h=c.gains.copy();vh=1/P if gain_mode=='joint' else 0.;tau=1/P
    xb=x.copy();hb=h.copy();Bb=None;s=np.zeros(n,complex);sv=0.;bar0=None;vp0=None;trace=[];states=[]
    for it in range(iterations):
        xt=daft(x,c.c1,c.c2,True);B=o.responses_time(xt);vx=float(v.mean());ex=float(np.vdot(x,x).real)
        channel_norm=o.power(h)
        bar=vx*channel_norm+P*vh*ex/n;vp=bar+P*vh*vx
        if bar0 is not None:bar=damping*bar+(1-damping)*bar0;vp=damping*vp+(1-damping)*vp0
        bar0=bar;vp0=vp
        z=B@h
        if observation_domain=='af':z=daft(z,c.c1,c.c2)
        ph=z-s*bar
        s=damping*(Y-ph)/(noise+vp)+(1-damping)*s;sv=damping/(noise+vp)+(1-damping)*sv
        st=s if observation_domain=='time' else daft(s,c.c1,c.c2,True)
        xb=damping*x+(1-damping)*xb;hb=damping*h+(1-damping)*hb
        Bb=B.copy() if Bb is None else damping*B+(1-damping)*Bb
        data_precision=sv*o.power(hb);gain_precision=sv*np.vdot(xb,xb).real
        vr=1/max(data_precision,1e-12);vq=1/max(gain_precision,1e-12)
        adj=daft(o.adjoint_time(hb,st),c.c1,c.c2)
        rx=x+vr*(adj-xb*(sv*P*vh))
        rh=h+vq*(Bb.conj().T@st-hb*sv*n*vx)
        ext,app,mu,v=marginal(-abs((rx-pilot)[:,None]-a)**2/vr,prior,pd);x=pilot+mu
        vh=tau*vq/(tau+vq) if gain_mode=='joint' else 0.
        if gain_mode!='fixed':h=tau*rh/(tau+vq)
        if not all(np.isfinite(q).all() for q in (h,mu,v,s)):raise FloatingPointError('nonfinite scalar joint update')
        trace.append(dict(iteration=it,data_variance=float(v.mean()),gain_variance=float(vh),
                          channel_norm_factor=float(channel_norm),pseudo_variance_bar=float(bar),
                          pseudo_variance_total=float(vp),data_pseudo_variance=float(vr),
                          gain_pseudo_variance=float(vq),output_precision=float(sv),
                          data_precision_floor=bool(data_precision<=1e-12),
                          gain_precision_floor=bool(gain_precision<=1e-12),
                          fft_count=2 if observation_domain=='time' else 4))
        if record_states:states.append(dict(h=h.copy(),mu=mu.copy(),v=v.copy(),s=s.copy(),vr=vr,vq=vq,vh=vh,sv=sv,bar=bar,vp=vp))
    out=dict(extrinsic=ext,app=app,mu=mu,variance=v,gains=h,gain_variance=np.full(P,vh),trace=trace,iterations=iterations,fft_count=2*iterations+1 if observation_domain=='time' else 4*iterations)
    if record_states:out['states']=states
    return out


## Actual projected covariance function

"""Reference full-fractional frozen-diagonal-q variable projection.
Classical variable projection; the fast projected moment identity is tested separately.
No truth is accepted by the estimator. Integer delays are supplied by observed support.
"""
import numpy as np
from scipy.optimize import minimize_scalar

def dkernel(t, n):
    t=(np.asarray(t,dtype=float)+n/2)%n-n/2
    return np.exp(1j*np.pi*(n-1)*t/n)*np.sinc(t)/np.sinc(t/n)

def projected_variance(v, delays, dopplers, c1):
    """Exact tr(U_i^H U_j diag(v)); positive chirps/positive Doppler."""
    v=np.asarray(v,float);l=np.asarray(delays,int);nu=np.asarray(dopplers,float);n=len(v)
    delta=l[None,:]-l[:,None]
    z=nu[None,:]-nu[:,None]+2*n*c1*delta
    gamma=np.exp(2j*np.pi*c1*(l[:,None]**2-l[None,:]**2))*dkernel(z,n)*np.fft.fft(v)[delta%n]
    return (gamma+gamma.conj().T)*.5


## Actual finite QPSK moments/marginals

"""All bit vectors use the upstream ALL-I THEN ALL-Q order. L>0 means bit zero.
Output APP and extrinsic are distinct; decoder priors are replacements.
"""
import numpy as np
from scipy.special import logsumexp

def alphabet(pd):
    a=np.sqrt(pd/2);return a*np.array([1+1j,1-1j,-1+1j,-1-1j]),np.array([[0,0],[0,1],[1,0],[1,1]])
def logprior(L,pd):
    L=np.asarray(L,float);n=len(L)//2
    if L.ndim!=1 or len(L)%2 or not np.isfinite(L).all():raise ValueError('Invalid grouped LLR vector')
    _,bits=alphabet(pd);li=np.column_stack((L[:n],L[n:]));a=.5*li@(1-2*bits).T
    return a-logsumexp(a,axis=1,keepdims=True)
def moments(L,pd):
    p=np.exp(logprior(L,pd));a,_=alphabet(pd);mu=p@a
    return mu,np.maximum(pd-abs(mu)**2,0),p@(a*a)-mu*mu

def marginal(likelihood,prior,pd):
    post=np.asarray(likelihood,float)+logprior(prior,pd);a,b=alphabet(pd)
    app=np.concatenate([logsumexp(post[:,b[:,j]==0],axis=1)-logsumexp(post[:,b[:,j]==1],axis=1) for j in (0,1)])
    p=np.exp(post-logsumexp(post,axis=1,keepdims=True));mu=p@a
    return app-prior,app,mu,np.maximum(pd-abs(mu)**2,0)


## Gemini original, untrusted opinion to evaluate

这组 $2 \times 5$ 的配对实验与推导文档非常有价值。它不仅以极高的工程严谨性（位精确复现与独立 Bootstrap 核验）回应了上一轮的核心悬念，而且事实上**已经为“为什么会发生排序翻转”提供了决定性的机理证据**，同时也暴露了当前对照设计与论文叙事中几个必须警惕的数学漏洞。

以下脱离此前的解释框架，直接基于两份附件的代数结构与统计数据给出独立判断。

---

## 一、 这组数据真正说明了什么？（三个核心数学判断）

### 1. 排序翻转的真正根源已被锁定：`Native point`（40 vs 11）与 `New full`（0 vs 0）的对比就是铁证

在本次实验中，最具科学判别力的不是 `New full` 对 `New diagonal`（0 vs 200），也不是 `New full` 对 `Native joint`（0 vs 2），而是**同处于“零传播增益方差（Propagated gain variance = 0）”且共享完全相同符号更新调度的 `Native point` 与 `New full soft Gram` 之间的对比**：

* 在 `Native point` 下，标量 $\Gamma$ 上游与完整 $\Gamma$ 上游的失败数为 **40/200（20.0%）对 11/200（5.5%）**，呈现剧烈的性能翻转（相比 `Native fixed` 的 4/200 对 15/200）。


* 当唯一改动是将下游标量 P-BiG-AMP 的伪观测/Onsager 增益更新替换为精确求解 $P \times P$ 正规方程 $Q h = (B^H B + \Gamma(v) + \alpha I)h = B^H y$（即 `New full soft Gram`）后，两种上游输出下的失败数同时降至 **0/200 对 0/200**；更重要的是，两者的外信息比特对数损失（`0.189826` vs `0.189927`）与数据符号 MSE（`0.110024` vs `0.110842`）几乎完全重合，标量 $\Gamma$ 上游的最终信道 NMSE 甚至还略优于完整 $\Gamma$ 上游（`0.024835` vs `0.026482`）！


* **这组对比在数学上确立了一个核心事实：**
上游标量 $\Gamma$ SBL 选出的支撑集 $\hat{S}_{\text{scalar}}$ **在物理子空间意义上根本没有缺陷**（甚至多出的近重复自由度在精确矩阵求逆下提供了略微更低的信道逼近误差 `0.024835`）。此前观测到的下游崩溃（40/200 与 23/200），**完全是因为原生 P-BiG-AMP 的一阶标量增益更新（及其对角 Onsager 修正）破坏了算子表征不变性，无法处理 $\hat{S}_{\text{scalar}}$ 中的共线/近重复原子列**；一旦下游改为满足子空间聚合不变性（$D h'_{\text{full}} = h_{\text{full}}$）的二阶矩阵求解，上游选标量 $\Gamma$ 还是完整 $\Gamma$ 的性能差异与翻转现象便彻底消失。



### 2. 即使在无近重复的完整 $\Gamma$ 上游上，原生标量 AMP 的增益步也存在显著的有限维近似损失

在 `Full-Gamma upstream` 上，近重复原子已被上游抑制，但切换下游依然呈现出清晰的阶梯演进：


$$\text{Native fixed (15/200)} \longrightarrow \text{Native point (11/200)} \longrightarrow \text{Native joint (2/200)} \longrightarrow \text{New full (0/200)}$$


特别注意：`New full` 与 `Native point` 同样**不向符号端传播增益方差（传播方差为 0）**，却不仅消除了 `Native point` 的全部 11 次失败，而且比传播了增益方差的 `Native joint`（2/200）还要降低约 **13.4% 的 LLR 对数损失**（`0.189927` vs `0.219107`）并改善了信道 NMSE（`0.026482` vs `0.028158`）。
这说明：即便没有同时延近重复原子，在有限帧长与叠加导频结构下，不同路径基矩阵 $U_p \bar{x}$ 之间仍存在非零的有限样本互相关 $(B^H B)_{pq} \neq 0$ 以及非均匀软符号方差诱导的耦合 $\Gamma(v)_{pq} \neq 0$。原生 P-BiG-AMP 依赖大系统独立同分布假设的标量增益更新，在精度上显著劣于直接求解 $P \times P$ 局部高斯代理问题。

### 3. 算法本质定位：这是嵌套在 AMP 符号环内的“精确变分 EM（VEM / CAVI）M-步”，而非全新的推断框架

如附件所坦承的那样，不能将该局部二次代理求解包装成全新的全局 AMP/VI 推导。从统计信号处理视角看，给定符号端工作分布 $x \sim \mathcal{CN}(\bar{x}, \text{diag}(v))$，最小化期望对数似然加高斯先验：


$$\mathbb{E}_{x}\left[\Vert{}y - B(x)h\Vert{}_2^2\right] + \alpha \Vert{}h\Vert{}_2^2 = \text{const} - 2\text{Re}(h^H b) + h^H \big(B^H B + \Gamma(v) + \alpha I\big) h$$


得到的闭式解 $h_{\text{full}} = (B^H B + \Gamma(v) + \alpha I)^{-1} B^H y$，在数学上正是**含乘性字典不确定性（Errors-in-Variables）的坐标上升变分推断（CAVI）或变分 EM（Variational EM）的精确增益更新步**。因为符号维度 $N$ 很大而稀疏支撑维度 $P = \vert{}\hat{S}\vert{}$ 很小，在 $N$ 维符号端跑标量 AMP、在 $P$ 维信道端做精确 $P \times P$ 闭式线性求解，属于经典的混合消息传递—变分推断（Hybrid AMP-VEM）合理应用。

---

## 二、 哪些解释或算法环节存在漏洞？（五个关键漏洞）

### 漏洞 1：`New diagonal soft Gram`（C1 对照）是一个“稻草人对照”，完全不能用来证明 $\Gamma(v)$ 非对角项或近重复原子的作用

在 `full-gram-gain-block.md` 中，对角控制组定义为：


$$h_{\text{diag}} = \big(\text{diag}(\text{diag}(M)) + \alpha I\big)^{-1} b, \quad M = B^H B + \Gamma(v), \quad b = B^H y$$


它在 दोनों上游下跑出了 **200/200（100% 失败）** 和 **198/200（99% 失败）** 的极端结果。附件中已经敏锐地意识到“该对角分支极其脆弱，仅击败它不足以支撑后续工作，且 $M$ 同时混杂了均值回归器与符号不确定性耦合”。从代数上看，它崩溃的根本原因在于：

* **它在右端使用了全观测匹配滤波 $b = B^H y$（包含所有 $P$ 条路径的叠加信号），却在左端把确定性多径互相关矩阵 $(B^H B)_{pq}$ ($p \neq q$) 连同 $\Gamma(v)_{pq}$ 一起砍掉了**！


* 在 `Native point` 中，虽然也是标量更新，但它是对**扣除了其他路径干扰后的当前残差**做更新；而 $h_{\text{diag}} = (\text{diag}(M)+\alpha I)^{-1} B^H y$ 既不在左端做矩阵解耦，也不在右端扣除多径残差，直接退化成了**零多径干扰抵消的单用户匹配滤波器（Single-User Matched Filter）**！
* 这就是为什么即便在**完全没有近重复原子的 `Full-Gamma upstream` 上**，`New diagonal` 也会在第一步就产生 `0.99` 的相对物理信道偏差并导致 **198/200 失败**。因此，C1（`New full` 胜过 `New diagonal`）只证明了“多径信道不能用无干扰抵消的单径匹配滤波器来解”，**完全没有隔离出 $\Gamma(v)$ 的非对角项，也没有证明任何关于近重复原子的机理**。



### 漏洞 2：推导包中的“精确复制不变性（$D h'_{\text{full}} = h_{\text{full}}$）”依赖人为同步放大先验 $\alpha' = k\alpha$，在真实非均匀近重复下并不严格成立

在 `full-gram-gain-block.md` 的核心推导中，为了证明每个原子均匀复制 $k$ 次后物理信道不变（$D h'_{\text{full}} = h_{\text{full}}$），关键一步利用了 $P' = kP \implies \alpha' = \sigma^2 P' = k\alpha$：


$$Q' T = (D^H M D + k\alpha I) \frac{D^H}{k} = D^H (M + \alpha I) = D^H Q \implies D h'_{\text{full}} = h_{\text{full}}$$

* **数学漏洞：** 这一精确恒等式成立的充要条件是**每一个原子都被均匀复制相同的 $k$ 次，且全局先验精度恰好按总原子数 $P'=kP$ 放大了 $k$ 倍**。


* 但在真实的 `Scalar-Gamma upstream` 输出中，近重复是**非均匀局部发生的**（例如某条强径分裂成了 $k_1 = 3$ 个近重复原子，另一条弱径只有 $k_2 = 1$ 个原子）。此时不同簇的复制重数 $k_p$ 不同，标量先验 $\alpha' I$ 无法同时在所有簇上提公因子消掉 $k_p$！ Furthermore，对于两个相近但不完全相等的原子 $U_1 \approx U_2$，在反相差分方向 $v_- = \frac{1}{\sqrt{2}}[1, -1]^T$ 上，$v_-^H M v_- = \mathcal{O}(\epsilon \Vert{}M\Vert{}) \neq 0$。
* **真实原因：** 在实际数据上 `New full` 之所以对近重复近乎免疫，**不是因为 $\alpha' = k\alpha$ 的严格代数对易，而是因为在高信噪比/工作点下同相方向数据项占优（$\lambda_+(M) \gg \alpha$），且 $M = B^H B + \Gamma(v)$ 在同相方向具有天然的算子级分裂不变性，而 $\alpha I$ 在零空间/差分方向充当了Tikhonov 阻尼**。如果把“均匀复制 $k$ 倍不变性”作为论文定理的主体，审稿人很容易指出非均匀复制（$k_1 \neq k_2$）的反例。

### 漏洞 3：混合迭代的全局一致性缺陷（Onsager 记忆错配与零方差传播截断）

`full-gram-gain-block.md` 在 Open Risks 中已经点出了这一风险：

1. **符号端记忆项失配：** 原生符号更新步中的残差记忆与阻尼是为渐近标量 AMP 的增益步配套设计的，直接塞入闭式矩阵解 $h_{\text{full}}$ 构成了缺乏单一全局自由能下降保证的启发式混合迭代（Hybrid Schedule）。


2. **丢弃后验协方差 $\sigma^2 Q^{-1}$：** `New full` 已经算出了 $Q$ 的分解，却为了对齐 `Native point` 而强制将传播给符号端的增益方差设为 0。然而原生对比清楚显示：开启增益方差传播（`Native joint` 相比 `Native point`）能将失败数从 40/11 降至 23/2。忽略 $\text{diag}(\Sigma_h)$ 意味着符号检测器在早期迭代中低估了信道不确定性。



### 漏洞 4：耗时统计（+48% 检测 / +29% 总耗时）混入了大量非算法必需的工程与诊断开销

当前 `New full` 检测耗时中位数为 `42.73ms/42.62ms`（对比 `Native joint` 的 `28.82ms` 增加约 48%），但这并非算法本身的真实代价：

* 附件明确记录：`Native 20` 仅调用 **41 次 FFT**，而 `New 20` 调用了 **61 次 FFT、20 次增益求解和 20 次仅用于诊断的协方差求解（外加资格检验的特征值分解 eigensolves）**！


* 既然算法处于点估计模式（传播方差为 0），那 **20 次协方差求逆与特征值分解完全是诊断冗余**；且每轮多出的 1 次 FFT（共 20 次）源于重复计算时域/AF 域变换。剥离这些非必要开销后，仅在 $P \ll N$ 的小矩阵上做 20 次 Cholesky 求解，真实耗时增幅将远低于 29%。



### 漏洞 5：整篇论文的主线面临“左右互搏”的叙事危机

如果你们把 `New full soft Gram` 作为最终推荐的下游检测器，请看表中的数据：

* `Scalar-Gamma upstream + New full`：失败 **0/200**，LLR 损失 **0.189826**，信道 NMSE **0.024835**，耗时 **59.11ms**。


* `Full-Gamma upstream + New full`：失败 **0/200**，LLR 损失 **0.189927**，信道 NMSE **0.026482**，耗时 **59.23ms**。
**漏洞在于：** 如果下游采用 `New full`，**上游使用完整 $\Gamma$ SBL 相对于标量 $\Gamma$ SBL 的性能优势在当前样本上彻底归零（甚至 NMSE 略差）**！这会直接动摇你们前期花费大量精力构建的“上游完整 $\Gamma$ 改善支撑选择与最终性能”的立论根基。



---

## 三、 研究价值究竟在哪里？（如何重构为高价值贡献）

把 `New full soft Gram` 单独包装成“一种新的检测器算法”价值有限（容易被评为经典的变分 EM / 块最小二乘更新，且与 `Native joint` 的 2/200 在统计上尚未拉开显著的 FER 差距，95% CI 为 `[-0.025, 0.000]`）。

但如果你将 **`Native fixed`、`Native point`、`Native joint` 与 `New full soft Gram` 四者的对比** 整合起来，它揭示了一个比“单个算法改进”深刻得多的**两阶段双线性推断（Two-Stage Bilinear Recovery）结构性定理**：

> **核心重构命题（二阶不确定性耦合的“上下游可迁移性 / 等价性原理”）：**
> 在含字典不确定性 $\Gamma(v)$ 的稀疏信道估计与数据检测级联系统中，由近重复/共线原子引发的病态性可以通过两条对偶途径解决：
> 1. **上游表征净化（Upstream Representation Purification）：** 在高维候选字典上付费计算完整 $\Gamma$ SBL，剔除共线近重复原子，输出良态支撑 $\hat{S}_{\text{full}}$，从而允许下游使用低复杂度的一阶标量消息传递（`Native joint`，2/200 且仅需 41 次 FFT / 28.8ms）；
> 
> 
> 2. **下游算子不变更新（Downstream Operator-Invariant Update）：** 允许上游使用廉价的标量 $\Gamma$ SBL（保留共线近重复原子），而在下游低维激活支撑 $P \times P$ 上付费求解包含完整软 Gram 矩阵 $M = B^H B + \Gamma(v)$ 的二阶正规方程（`New full`，将标量 $\Gamma$ 上游的失败数从 40/200 逆转为 0/200）。
> 
> 
> 
> 

**这一视角的价值在于：**

* 它把 `New full soft Gram` 从一个“抢夺上游功劳的竞争模块”，变成了**证明整篇论文核心机理的“神谕基准（Oracle-Consistent Benchmark）”与“高可靠模式选项”**！
* 它完美解释了为什么 `Scalar-Gamma` 在 `Native point/joint` 下崩溃、在 `New full` 下却完全恢复，使整篇论文成为对“不确定双线性稀疏恢复中表征冗余与推断阶数相互作用”的透彻研究，而不再是一篇脆弱的工程调参报告。

---

## 四、 下一步最值得做什么？（最小判别实验与判决标准）

在跑任何新帧（New Frames）之前，最值得在现有 200 个 key 上立刻完成以下 **2 个零成本补充实验**（耗时仅需十余秒 CPU 时间），然后再决定是否扩充样本：

### 第一步（最关键的机理判别）：补做“仅对角化 $\Gamma(v)$、保留完整 $B^H B$”的消融分支（`Full-BHB + Diag-Gamma`）

当前实验缺失了最关键的一个中间控制组。请保持 `New full` 的全部代码不变，仅将矩阵 $M$ 改为：


$$M_{\text{diag-}\Gamma} = B^H B + \text{diag}\big(\text{diag}(\Gamma(v))\big), \quad Q_{\text{diag-}\Gamma} = M_{\text{diag-}\Gamma} + \alpha I$$

* **为什么要做这一步：**
因为 `New diagonal` 同时删掉了 $(B^H B)_{pq}$ 和 $\Gamma(v)_{pq}$，你无法回答审稿人：“`New full` 的 0/200 究竟是因为下游需要非对角的 $\Gamma(v)_{pq}$，还是仅仅因为需要经典的最小二乘矩阵 $(B^H B)_{pq}$？”


* 如果 $M_{\text{diag-}\Gamma}$ 在 `Scalar-Gamma upstream` 上显著退化（例如失败数 > 0 或 LLR 损失明显劣于 `New full` 的 `0.189826`），这就**首次在严格控制 $(B^H B)_{pq}$ 不变的前提下，直接证明了下游保留非对角符号不确定性耦合 $\Gamma(v)_{pq}$ 对抑制共线原子失稳是不可或缺的**！
* 反之，如果 $M_{\text{diag-}\Gamma}$ 在两种上游下也达到 `0/200` 且 LLR 损失与 `New full` 几乎无差别，则说明**下游起决定性作用的只是精确求解确定性多径互相关矩阵 $B^H B$，而非下游的 $\Gamma(v)$ 非对角项**。



### 第二步（清理工程假象）：剥离诊断开销并统计两种上游的支撑基数 $P = \vert{}\hat{S}\vert{}$

在 `New full` 中关掉不参与算法的 20 次协方差求逆与特征值验证，并复用符号步已有的时域/AF 域变换以消除多出的 20 次 FFT，重新测量纯算法耗时，同时对比 `Scalar-Gamma upstream` 与 `Full-Gamma upstream` 的平均原子数 $\bar{P}$。

---

## 五、 什么证据会改变我的判断？（明确的证伪与决策红线）

对于“是否应当用 `New full soft Gram` 取代现有最佳原生接收机（`Full-Gamma SBL + Native joint`）”这一核心决策，我设定以下明确的证据反转标准：

1. **何时放弃将 `New full` 作为主推生产接收机（退回 `Full-Gamma + Native joint` 作为主角，将 `New full` 降级为机理分析工具）：**
* 如果在完成上述第一步（$M_{\text{diag-}\Gamma}$ 消融）后发现：**去掉下游 $\Gamma(v)$ 的非对角项对 `New full` 毫无影响**（说明 `New full` 只是常规的 $B^H B$ 岭回归更新）；
* **或者**在新的独立帧样本（建议专门在低 SNR / 临界工况下采样 500 个独立帧簇以避开 $0\text{--}2$ 次失败的低事件率天花板）上，`New full` 相比 `Full-Gamma + Native joint` 的 FER 改善在统计上仍不显著，且剥离诊断开销后的纯计算耗时仍高出 `Native joint` **15% 以上**。


* 一旦出现上述结果，我的判断是：**不要把 `New full` 包装成新方法去抢占主线**，而是坚定保留计算更轻量的 **`Full-Gamma SBL + Native joint` 作为推荐接收机**，并将本次的 `New full` 实验作为论文中最精彩的**机理诊断章节（Diagnostic Proof of the Reversal Mechanism）**——用它来证明为什么标量 AMP 必须搭配上游完整 $\Gamma$ SBL 才能逼近二阶矩阵求解的极限性能。




2. **何时全力将主线切换为“下游/混合二阶软 Gram 更新（`New full`）”：**
* 如果 $M_{\text{diag-}\Gamma}$ 消融证明：**在 `Scalar-Gamma` 上游（或两者）下，丢弃下游 $\Gamma(v)$ 的非对角项确实会导致显著的 FER 或 LLR 损失退化**；
* **并且**在剥离诊断冗余后，发现由于上游可以改用廉价的 `Scalar-Gamma SBL`（省去高维候选空间上的完整 $\Gamma$ 计算），**`Scalar-Gamma SBL + New full` 的端到端（SBL + 检测 + 译码）总耗时反而低于或持平于 `Full-Gamma SBL + Native joint**`，同时在新独立帧上稳健保持 LLR 损失与 FER 优势。


* 若这一证据出现，它将彻底改变整个课题的工程结论：真正最优的架构不是在庞大的上游候选集上算完整 $\Gamma$，而是**用标量 $\Gamma$ 快速筛选支撑，再在下游极小的激活集 $P \times P$ 上执行保持算子不变性的完整软 Gram 闭式更新**。
