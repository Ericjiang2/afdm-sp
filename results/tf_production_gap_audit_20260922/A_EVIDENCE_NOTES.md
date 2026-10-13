# Production evidence audit A

No receiver calls were added by A. All3072 TF observations/6144 TF checkpoints were recounted; the original9696 attempts and19392 checkpoint timing records remain bound by source artifact hashes. Original raw data stay at deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_pd1q_part_b_20260921/run. `A/receipt.json` and existing `remote_inventory.json` bind the evidence; unavailable fields are in `A/unavailable_fields.json`.

## Findings before interventions
6.5dB:43 TF failures, all nonzero syndrome; round2 rescues284, harms0. Across1024 frames:470 missing distinct delay,238 true same-delay multiplicity,228 represented same-delay underfit,95 final-refit boundary hits within.002. Among43 failures:23 missing delay,17 missing energy>.01,25 represented same-delay underfit,3 final-refit boundary hits. Among981 successes corresponding counts447,153,203,92. Missing weak paths and boundary hits alone do not identify recoverability.

Historical acquisition duration and initial support were not retained; each refit total includes all candidate evaluations but their individual durations are absent. Ready offsets are saved; exact UTC at receiver-entry origin is absent. Stage sum and unsplit remainder remain separate, never sum medians. Native TF precision-floor flags are zero throughout; this does not assert every clipping/floor in acquisition/LDPC was inactive.

## Exact source and laws
`source_archive_manifest.json` binds a source archive assembled against actual PartB `source_hashes`27/27 and `baseline_source_hashes`131/131. Source2d130b4db9076e609be11d84035f1de5d6ee7b80, baseline31d5ec0dd6d582b59e74096b945a326896e24ba3. Actual native/receiver/physical/messages/LDPC files are included; older SOURCE_PROVENANCE receiver hash is stale and is not authority.

Actual N1024, P8, rho=.5, c1=.00244140625, c2=1.9751241797117955e-7, CPP102. Zadoff-Chu pilot root7: sqrt(rho)*exp(-j*pi*7*n²/N). Original data sqrt(1-rho)*qpsk_map(coded), all-I then all-Q; identity interleaver. Complex noise sigma²=10^(-SNR/10), CN(0,1) samples=(normal+j*normal)/sqrt2. Receiver unit scale sqrt(2*(1-rho))=1.

Source anchors (inside archived baseline/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled): afdm_env.py:131 pilot; :180-205 chirps; :285-360 exponential delay/PDP, Rayleigh amplitude/random phase, normalized tap amplitudes and nonuniform Doppler; :505-632 physical integer-delay/continuous-Doppler conversion and matrix/gain scaling. supplement_g1.py:18-42,:72-125 defines complete physical operator and CPP consistency; no second gain normalization there. budgeted_support_eval.py:114-129 and PartB campaign/run.py:64-96 define actual sample generation and unit conversion.

LDPC e1_ldpc.py:43-157 builds H/G and free/pivot coordinates, :164-191 encodes/extracts/maps. Actual frozen cache SHA cbb1557dbbd9ac27bdaf27099ccca2d831943bd1a27d14e46faedf4e9fb9c052; raw G SHA bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af. Dimensions2048x1024. Three duplicate G-row pairs [66,932],[878,1566],[2046,2047] mean code-symbol covariance has6 directed off-diagonal corrections. SP scoring uses exact code moments, not unconditional PdI approximation.

Actual environment: liunxgpu/x86_64, Linux5.15.0-191, Python3.10.20, NumPy1.26.4, SciPy1.10.1, Torch2.5.1+cu121. CUDA hidden, effective Torch intra/inter-op1 and all BLAS/OpenMP1. Acquisition casts complex64; physical/TF NumPy arithmetic complex128/float64. PartB manifest records platform but not CPU model; fresh machine metadata does not reconstruct historical unsaved details.

## Native negative controls, exploratory only
Source definitions/results remain under experiments/sp_afdm_native_joint_20260921; they predate final counted StageA/B, are reused4/8-frame screens, not production FER estimates.

|Variant|Observed saved result|Measured cost scope|
|---|---|---|
|Vector variance base20/coherent20|both0/4 errors|1.702610/2.398132s; excludes acquisition|
|Vector variance base40/coherent40|both0/4 errors|3.015125/4.306987s; excludes acquisition|
|Gain covariance block soft/mean|both1/8 errors;53/56 info errors|3.647119/3.643399s; includes acquisition|
|Dynamic tangent joint2/joint4|1/4 versus3/4 errors|1.414792/2.302008s; excludes acquisition|
|Frozen tangent joint2/joint4|both1/4 errors|1.397612/2.282600s; excludes acquisition|

Definitions: src/fast_bilinear.py:54-101, block_bilinear.py:26-49, joint_tangent_exploration.py:35-50, joint_tangent.py:48-50. Results: results/{fastamp_screen,block_screen,tangent_screen,tangent_fixed_screen}.json. These controls do not cover every joint code/channel correction.

## Retired V4
Archived spafdm-gpt-20260920/search_screen.csv (in source ZIP),64-draw cold-start: true-word coverage OSD16=27/64,OSD64=32/64,OSD128=35/64,branch64=43/64,phase64=29/64,relaxed64=35/64,beam64=33/64. Corresponding errors37,32,30,23,36,30,31. This is candidate acquisition coverage, separate from fixed-list evaluation.

Fixed256-word-list192-draw full/certified both48 failures; equal MAP decisions and work fractions. One actual N1024 attachment: frontend3.480154276s,proposal9.259998281s,full scorer.185995941s,certified scorer.167863736s; totals12.926148498/12.908016293s. True word absent from64-word list; scorer saving only.14% total. Confirmation was PREPARED_NOT_EXECUTED. Source anchors .trellis/tasks/09-13-trans-next/research/spafdm-gpt-20260920/{v4-proposed-method.md:35-43,:274-302,architecture-verdict.md:40-44,transactions-package-README.md:20-25}. No current production TF claim follows.
