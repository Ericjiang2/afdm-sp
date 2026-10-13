# Frozen direction validation follow-up (2026-09-21)

User explicitly authorized fresh modest development evidence from the frozen primary, not confirmation. This reopens the existing native-joint task; previous A/B evidence remains immutable. Keep workflow minimal and reuse qualified numerical source2d130b4d/baseline31d5ec0d. No numerical changes, retuning, new module, new SNR search or confirmation.

## Allocation frozen before new observations

SNR6.0,6.5,7.0dB. TF_J20_R2 and EP2_MEAN_R2 on32 paired independent observations per SNR. EP4_MEAN_R2 and TF_POINT20_R2 on predefined frames0–7 per SNR; PBI8_SOFT_R2 on0–3. Total252 measured calls,96 independent observations. Same input per paired method, same fair physical-refit implementation and complete online accounting. Namespace[20260921,940318,0,snr_centi_db,frame,component], components0=message,1=channel,2=noise; reject actual channel seed collisions with previous campaigns. No adaptive addition planned: ambiguous evidence is an acceptable terminal verdict.

Store metrics, seeds/config/source hashes, decisions/LLRs and compact paths for recount/NMSE. Heavy arrays onlyframe0 of each SNR and exceptional failures. Server restrictions unchanged: deinlab CPU, single numerical process, all writes under/data/guoyikun/, whitelisted env, thread counts1,30min timeout,512MiB safetycap. Separate new results path results/sp_afdm_native_direction_20260921/.

## Prospective decision interpretation

Primary endpoint: unrestricted decoded information-frame errors, information-bit errors, paired rescues/harms; complete latency median/p90. Prior fixedD=0.6780479838140309s and1.5D/2D are secondary diagnostics only. p90 linear quantile, same paired confidence-interval convention as original design; no equivalence or statistical superiority claim.

An error-informative cell has EP2 between1 and24 frame errors out of32. All three cells remain reported regardless.

- Supported: at least2 informative cells; across all3 fixed cells TF/EP2 median latency≤0.75 and p90≤1.0, no numerical failures, unrestricted net harms (harms−rescues)≤1 in each cell and≤1 across all96 frames. No cell has a material bit-error penalty, defined prospectively as TF information errors>1.5×EP2 and excess≥128 bits. These are engineering decision thresholds, not statistical margins or proof of equivalence.
- Not supported / return to adjudication: any primary numerical failure; any cell net harms≥3; the material bit-error penalty above; or at least2 cells lose median speed advantage (TF/EP2≥1). Do not fix/tune and rerun.
- Otherwise ambiguous: report what failed and stop this modest study. A benefit on one cell alone cannot produce supported. No opportunistic sample expansion.

Controls are attributed on their exact common-frame subsets, never compared via unequal-n aggregate errors. EP4 tests stronger-accuracy/cost tradeoff; POINT tests gain-variance attribution without replacing primary; PBi is a costly external accuracy control. Controls can qualify the scientific interpretation, but do not silently replace the preselected practical EP2 comparator.

## Delivery

One narrow changed-orchestration check, freeze Git runner before launch; no repeated mathematical or Stage0 reviews. One offline recount after completion, provenance and transfer hashes. Concise RESULTS.md: paired cell results, latency/error tradeoff, controls, supported/ambiguous/not supported, and only if supported the minimum next step. No broad paper-claim or STATE promotion.

Execution receipt: runner frozen at `beb5ab73`; real D252 launched2026-09-21 11:59:08UTC,tmux g_native_direction,launcher PID453320,child453325,deadline12:29:08UTC. All allocation/seed/source checks passed before new observations; one bounded orchestration review completed. Results pending.

Completed252/252,96 fresh observations,504 checkpoint recount pass,0 numerical failures. Verdict supported: median ratios0.590/0.592/0.586 and p90 ratios0.442/0.473/0.447 at6/6.5/7dB; unrestricted TF/EP FE6/9,1/6,1/1;8rescues/0harms. POINT and EP4 match TF subset FE; no claim of independent gain-variance benefit. Process wall356.20s;989 artifacts53,847,372bytes; no active owned job, no confirmation. RESULTS.md in new direction directory; no STATE/paper-claim promotion.
