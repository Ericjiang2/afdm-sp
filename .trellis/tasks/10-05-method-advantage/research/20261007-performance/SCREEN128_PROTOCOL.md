# Fixed SCREEN128 repair and one independent larger cohort

Status: preregistered development validation; source admission still required. Both previous pilots retain their FAIL verdicts. User's continuing exploration/SSH authorization covers this bounded followup; this is not a production CONF stream.

## Trigger and scientific question

In the independently sampled two-frame pilot, tuned quadratic SCREEN32 made90/256 errors versus random60/256 (11.71875pp improvement, exploratory95% CI[5.65497,17.78253]pp). Same-code random FULL made57/256: three correct FULL decisions were lost by SCREEN32, so the frozen noninferiority gate failed despite28.3757x speed. This explicitly identifies a screening loss that the four-frame pilot did not exhibit.

Fix only the candidate budget: use128 of1024 hypotheses, four times the old shortlist, keeping an8x hypothesis-count saving versusFULL. This is a conservative predetermined increase, not the smallest K selected from saved miss ranks; no saved-score scan of K is used to choose it. The method retains exact same mixture and48-point gain grid, no new waveform, radial weighting or truth initialization.

## Frozen cohort and counts

Same model and codes as SHORTBURST_PROTOCOL: N64,T2,SNR5dB,CP16,L80,s5,iid specifiedQPSK,nominal noise independent hiddengain,uniform delay/CFO and circular uniform-amplitude gain [.75,1.25]. Copy prior D's identical code reference, SHA2569d3a2d5532780b3fc884cc7d97fb7001107f9a94b64d0e9513f9eb2f2ffa0e03. No new design work.

One fresh fixedseed2026100704 stream,1024 independent paired groups. Use only tuned-quadratic and random codes; current and standaloneFOURTH already have retained evidence and are not necessary to validate this repair. Methods SCREEN128 andFULL; all waveforms/methods share the same external group variables and observation knowledge. Draw order l,nu,rho,phi,states(2,64),realnoise,imagnoise unchanged. Rotate four arm/method calls by globalgroup mod4. No warmup,seed search or optional stopping; keep all1024 even if early results look poor.

Counts:2048 waveform datasets,4096 new64-vectors,262144 complex observations,4096 top-level complete acquisition calls. Likelihood hypotheses=1024*2*(1024+128)=2359296; gain-grid evaluations113246208. New geometry/code draws0, productionreceiver/decoder0. Save all raw and scores; preserve entered/completed accounting and partial prefixes upon failure.

The larger batch reduces uncertainty after the pilot; it is one separately frozen cohort, not pooled retries or repeated testing until passage. The old3/256 loss and old accuracy effects do not enter the new acceptance calculation.

## Gates

All must pass:
- Deterministic core contracts, all FULL>=SCREEN128 objectives within1e−8+1e−10|screen|, same-candidate scores consistent, and complete independent raw audit.
- Random-code cumulative completeFULL time / completeSCREEN128 time>=3. Per-call validation/transforms/templates/output included, common generator/disk excluded for both; full process/I/O separate.
- Bad discordance SCREEN128 wrong/FULL correct: exact one-sided95% Clopper–Pearson upper U=Beta.ppf(.95,x+1,1024−x)<=.02. Exact acceptance set x<=12 (x12 U=.0189178670894; x13 U=.0201085405233). Report opposite discordance. Risk threshold/confidence unchanged; count threshold changes solely because n changed.
- Equal observation/cost comparison: tunedquadratic SCREEN128 error minusrandom SCREEN128 error>=.10, exploratory pairednormal95% CI lower>0; SE=sqrt(samplevariance(d)/1024).
- Random SCREEN128 errorfraction<=.25 (<=256 errors).

Report FULL accuracy on both codes as well. This evaluates a classical screening implementation of the scoped phase-code theory, not a first-in-literature FFT invention or universal receiver superiority. If any gate fails, retain the result and reassess the mechanism; no implicit re-run or favorable seed selection.

## Budget and provenance

New root outputs_acquisition_screen128_20261007, P1200s/A300s,total1500s,4096 observation reservation,0geometry,one CPUthread,CUDAhidden,RSS2GiB,output512MiB. CPU cost estimate is below cap based on completed two-frame pilot, not a completion guarantee. deinlab/AFDM and all remote writes under/data/guoyikun; committed isolatedsource and source admission before sampling, g_*tmux and no concurrent timing job.

Independent A reconstructs everyY with denseDFT, every fourth score with direct sums, all hypothesis/gain choices/counts/gates, and explicitmixture spots for groups0,256,512,768, two codes,two candidates=16 spots; no newobservations or estimatorcalls. Historical design reference is validated without redoing its objective search. Source/runtime/attempt/raw hashes retained. Finite-grid maximum likelihood remains distinct from continuousML or prior-integratedBayesMAP.
