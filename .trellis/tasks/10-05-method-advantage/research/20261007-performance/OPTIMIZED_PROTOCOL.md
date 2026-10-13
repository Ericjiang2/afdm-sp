# Independent validation of the observation-free optimized phase code

Development only. The three prior performance pilots remain FAIL. The separate D/A-only design qualified with mu .3253236536113068 -> .18375555862063078, selecting checkpoint199 by the previously frozen geometry criterion. It used0 observations, no restarts,200 deterministic updates. New performance is not inferred from geometry.

## Immutable inputs and cohort

Keep N64/T2/SNR5dB,CP16/L80/s5,uniform delay0..15 andCFO0..63,radial gain uniform[.75,1.25],circularphase,known nominalnoise, iidQPSK and complete-call SCREEN128/FULL exactly as SCREEN128_PROTOCOL.md. Only the known column code changes. Three waveform arms: old tuned quadratic (129candidate design), old fixed random, fixed optimized principal fourth-root code. New acquisition core reuses the admitted SCREEN128 implementation, no new estimator/gain grid or hidden truth input.

Oldreference codes.npz SHA2569d3a2d5532780b3fc884cc7d97fb7001107f9a94b64d0e9513f9eb2f2ffa0e03.
Optimized code.npz SHA25688e1b59be3dca8d7ff997b8e01528eaa41d6a7ef8b1a5da6d8d1bee803cdaee8.
Its D/results SHA2563b6d9be61f9a6d01e604f30e0c27cd2614ed7ebc93145b92a9b6906062c8bd05, D/attempt SHA25628ae960189cfcc035f5467f979e5a35cd2cd695c261e927410b852078b9fbe50, independent A/results SHA256cf50e2f969cf5b2eb0f0e08e56f8119d8ed5cf2f1dd00cb806ffdf83b7b0d22f. All four are immutable optimized_reference inputs; validate hash, D complete, design_qualified and A audit_pass before sampling.

One fixed seed2026100705,1024 fresh independent paired groups; draw l,nu,rho,phi,states(2,64),realnoise,imagnoise in old order. Share exogenous variables between all3 codes. Rotate six complete calls by group mod6, no warmup. Save all originalY/latent arrays and fullscores/choices/times. No interim endpoint selection, no pooling old data, no seed retry. This is a fourth outcome-informed development configuration, not a single global pre-registered5% confirmatory study.

3072 waveform datasets,6144 new64-vectors,393216complex observations,6144 complete acquisition calls,3538944 likelihood candidates,169869312gain evaluations. New design/geometry/RNG-for-design0. Prior design cost reported separately; no free reused per-observation transforms or candidate likelihood caches.

## Unchanged substantive gates for the proposed code

All required: complete contracts/raw audit andFULL>=SCREEN128; optimized code complete FULL/SCREEN128 cumulative time ratio>=3; optimized bad-discordance one-sided95%CP upper<=.02 (n1024 exactlyx<=12), report reverse separately; tunedquadratic SCREEN128 minusoptimized SCREEN128 error difference>=.10 and exploratory pairednormal95% interval lower>0; optimized SCREEN128 error<=256/1024. PairedSE=sqrt(samplevariance(error difference)/1024).

Also report the oldrandom comparison and its paired interval, all three codes' FULL errors and allthree code/method costs. Do not attribute better new-cohort results specifically to optimization unless the within-cohort optimized-versus-oldrandom evidence supports it. The previous random273/1024 is not a paired comparator. Failure of any primary gate remainsFAIL; no retrospective threshold change or implicit repeat.

## Budget and audit

Source package afdm_acquisition_optimized_20261007, outputroot outputs_acquisition_optimized_20261007. P1500s/A300s,total1800s; RSS2GiB/output512MiB; oneCPUthread/CUDAhidden/no concurrent timing. Committed/source-admitted isolated snapshot on deinlab/AFDM, all writes under/data/guoyikun, immutable stages. Earlier D/A design total1.382412s and202608geometry is historical, not new design work.

Independent A rebuilds all3072 Y and SCREEN fourth-score arrays, verifies all6144choices/counts/costs/paired intervals/CP, selectedcode hashes; explicit mixture check groups0/256/512/768 ×3codes×2candidates=24spots. It does0 new observations/estimator calls/geometry design. Unchanged finite48gain-grid profile is not continuousML or Bayes MAP; no multipath/continuousCFO/BER/production or first-in-literature claim.
