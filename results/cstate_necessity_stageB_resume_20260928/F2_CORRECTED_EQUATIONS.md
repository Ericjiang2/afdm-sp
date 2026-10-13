# Corrected F2 SISO equations

For observed `y∈C^N`, known pilot `p`, and current charged hard feedback `d`, define `x=p+d`, `φ_j=U(ℓ_j,ν_j)x` with the project's CPP/DAFT `Channel.regressors`, and `Φ=[φ_j]`. Integer `ℓ_j∈{0,…,102}` remains integer; `ν_j∈[−3,3]` is continuous. The likelihood is `y=Φh+w`, `w∼CN(0,β⁻¹I_N)`, and independent `h_j∼CN(0,δ_j)` with `δ_j>0`. Only the `N_r=1` case is implemented.

The small full-GESBL reference is `Σ=(βΦᴴΦ+diag(δ)⁻¹)⁻¹`, `μ=βΣΦᴴy`. Algorithm 3 instead propagates diagonal variances. With `A=|Φ|²` and incoming `(μ,V,s)`, one GAMP step is

```
V_P=A V;  P=Φμ−V_P⊙s_old
s=(1−θ_s)s_old+θ_s (y−P)/(β⁻¹+V_P)
V_S=1/(β⁻¹+V_P);  V_U=1/(Aᵀ V_S)
U=μ+V_U⊙(Φᴴs)
μ_new=(1−θ_h)μ+θ_h [δ⊙U/(δ+V_U)]
V_new=δ⊙V_U/(δ+V_U).
```

All operations on variances are real and positive. The damping is on `s` and `μ`, as declared; the diagonal variance recursion is **not** the diagonal of the full covariance in general. The EM hypervariance is the stable SISO form `δ_new=2E/(sqrt(1+4bE)+1)`, `E=|μ|²+V` (subject to the frozen positive floor). The corrected precision update is `β_new=(N+d−1)/(e+||y−Φμ||²+Σ_j V_j||φ_j||²)` for Alg.3; full-reference mode substitutes `tr(ΦΣΦᴴ)`.

Let `B_j=∂[U(ℓ_j,ν_j)x]/∂ν_j`. The expected linearized residual for **real** offsets κ is `const−2αᵀκ+κᵀQκ`, where `M=Σ+μμᴴ`, `Q=Re[(BᴴB)∘Mᵀ]`, and `α_j=Re[μ_j* b_jᴴ(y−Φμ)−(BᴴΦΣ)_{jj}]`. Alg.3 uses diagonal Σ, as explicitly printed. Optimize only δ-ranked top `R̄=155`, with each κ in `[−.5,.5]∩[−3−ν_j,3−ν_j]`, then set `ν_j←ν_j+κ_j`. The real QP coordinate change `z_j=sqrt(Q_jj)κ_j` is algebraically identical in physical κ and box; report both coordinate KKT residuals and solver termination. After the final grid update, charge a fresh posterior on the actual final grid before output.

For hard feedback, form `H_eff` from the selected 155 path gains and use `x̂_d=(HᴴH+2σ²I)⁻¹Hᴴ(y−Hp)` for the project's power-.5 QPSK, then hard-map each component to ±.5 (zero maps positive). Subsequent estimation uses `p+x̂_d,hard`. This is an **autonomous project policy** with up to four data passes; it is not the exact original paper experiment. Cap hits are reported. F2E passes the final 155-path Channel through the unchanged two TF20/LDPC50 rounds; triggered F2T starts from already charged native APP hard data and native check prior, and receives one TF20/LDPC50 continuation. No decoder result or truth enters the estimator's pilot pass.

The numerical and stopping constants are exactly [the frozen contract](F2_METHOD_CONTRACT.md) plus [the QP coordinate amendment](F2_NUMERICAL_AMENDMENT.md). Neither full posterior agreement nor a small mean discrepancy implies equal GAMP variance, equal support, FER, or convergence of a capped outer loop.
