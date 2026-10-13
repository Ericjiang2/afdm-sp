# Research: frozen SP-AFDM offline raw-diagnostics source map

- Query: Locate reusable offline-only interfaces in `experiments/sp_afdm_frozen_20260920` for (1) full true/estimated channel reconstruction in receiver units, (2) support omission/collision and model-error diagnostics, (3) bit extraction/BER denominators and saved-decision NPZ schemas for I1/proposed/native arms, and (4) information absent from stored driver results.
- Scope: internal
- Date: 2026-09-21
- Source version: original imported package / Git commit `70dd0077`. Line numbers and missing-field findings refer to that original schema; corrected evidence code evolves separately.

## Findings

### Files found

- `experiments/sp_afdm_frozen_20260920/src/run_local.py`: frozen driver; creates unit-normalized receiver inputs, saves truth/input NPZs, flattens arm arrays and decision checkpoints.
- `experiments/sp_afdm_frozen_20260920/src/receiver.py`: observed-only front end, proposed/native terminal paths, saved final path parameters, and native round state transitions.
- `experiments/sp_afdm_frozen_20260920/src/physical.py`: matrix-free `Channel` operator and dense-equivalent fractional-path formulas used by the new receiver.
- `experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_g1.py`: exact full CPP physical channel matrix, generator-side observation closure, and physical-model provenance.
- `.../budgeted_support_diagnostics.py`: truth-side projection, physical-cluster basis, and array hashing primitives.
- `.../representation_ledger.py`: physical-slot matching, merged dictionary truth ledger, stage-loss accounting, and fixed-support representation error.
- `.../v3_statistics.py`: exact offline residual decomposition around an estimated channel and a receiver working mean.
- `.../direction_factorial.py`: exact cancellation/data/thermal residual and energy-cross-term ledger.
- `.../supplement_a01_diagnostics.py`: fixed-design thermal/model-error diagnostics, but its prepared/fitted object contract is not emitted by the frozen driver.
- `.../e1_ldpc.py` and `.../run_classical_baselines_python.py`: code dimensions, systematic info extraction, QPSK bit order/sign, LLR convention, and raw-bit denominator.
- `experiments/sp_afdm_frozen_20260920/docs/DESIGN.md`: signal and information contracts, unit transform, receiver stages and approximation boundaries.
- `experiments/sp_afdm_frozen_20260920/docs/LOCAL_PROTOCOL.md`: required returned arrays and canary policy.
- `experiments/sp_afdm_frozen_20260920/environment.json`: recorded Python/NumPy/SciPy/PyTorch CPU versions.

### 1. Full true and estimated channels in the same receiver units

The exact truth-side dense matrix constructor is `supplement_g1.physical_channel_matrix` at `upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_g1.py:18-42`. It validates integer delays and supported CPP prefix, evaluates the full Dirichlet kernel and chirp phase, and explicitly documents “no gain normalization” at lines 18-23. The physical observation wrapper calls it with `system.N_total`, `system.c1`, `system.c2`, saved `l_i`, `k_real`, `g_i`, and `prefix_length` at lines 72-85. The direct CPP observation is checked against `h @ (pilot + data)` at lines 86-89, so this is the authoritative matrix convention rather than an inferred reconstruction.

The frozen driver saves `l_i`, `k_real`, `g_i` and `unit_scale` in `truth/cXX_fYYYYY.npz` at `src/run_local.py:61-64`; it saves receiver input `y`, `pilot`, and normalized `sigma2` in the separate input NPZ at lines 61-64. The exact normalization is `unit_scale = sqrt(2*(1-rho))`, followed by `y/unit_scale`, `pilot/unit_scale`, and `sigma2/unit_scale**2` at lines 61-62. `docs/DESIGN.md:65-70` states the same contract: divide `y` and `p` by `a`, divide variance by `a**2`, and retain the same channel. Therefore the receiver-unit truth matrix is:

```text
H_true_rx = physical_channel_matrix(N, c1, c2, l_i, k_real, g_i,
                                    prefix_length=l_max_cap)
```

There is no division of `H_true_rx` or `g_i` by `unit_scale`; only `y`, `pilot`, `data` and thermal variance are transformed into the receiver interface. When reconstructing a normalized observation closure from saved truth, use `data_rx = truth['data']/unit_scale`, `noise_rx = truth['noise']` with `sigma2_rx = truth['sigma2_raw']/unit_scale**2` if raw variance is separately available, or compare directly to the saved `input/y.npy`.

For the frozen N=1024 system, `run_frozen_i1_smoke.build` fixes `N_total=1024`, `l_max_cap=102`, `k_max_cap=2`, and records `rho`, `c1`, `c2` in `header.system` at `upstream/spafdm_receiver_handoff/run_frozen_i1_smoke.py:103-121`. `run_local` copies those values into `manifest.json` at `src/run_local.py:42-44`; use the manifest/header rather than inventing chirp constants.

The proposed and non-I1 terminal paths return a `physical.Channel` `c` and save its final path arrays at `src/receiver.py:75-77` (`path_delays`, `path_dopplers`, `path_gains`). The driver flattens these into `result_path_delays`, `result_path_dopplers`, and `result_path_gains` at `src/run_local.py:71-75`. Reconstruct an estimated dense matrix in the same receiver units with the same `physical_channel_matrix(..., prefix_length=l_max_cap)` call using those three arrays. Equivalently, the exact operator used by the receiver is `physical.Channel` at `src/physical.py:92-123`: `regressors` line 103, `apply` lines 109-114, and `adjoint` lines 115-120. The upstream dense constructor is preferable for an offline matrix because it is already the independently audited full CPP form.

Native coded arms persist one terminal result per coded round in `run_native`: round arrays are prefixed `round{t}_` at `src/receiver.py:125-141`, then flattened by the driver at `src/run_local.py:71-75`. Reconstruct `Hhat_t` from each `result_round{t}_path_*` triplet. For GAMP, `sbl_full_dopplers`/`sbl_full_gains` are auxiliary full-grid posterior state; the actual terminal `Channel` is still represented by the round `path_*` arrays returned by `estimate` (`src/offgrid.py:32-64`).

I1 (`method == 'I1'`) exits before physical refit and does not save final path arrays: `src/receiver.py:51-53` returns only `final_llr`. Its dense preterminal `H_est` is saved as `front_H_canary` only when `frame < 2`, at `src/run_local.py:73-75`. Thus I1 full-channel NMSE is available for the first two frames of each cell from the canary, but cannot be reconstructed for later I1 frames from the current NPZ schema. The saved `front_delays`, `front_dopplers`, and `front_gains` are the I1 observed support state (`src/receiver.py:45`, flattened by `run_local.py:74`), not a saved final I1 matrix; rebuilding a front matrix from them is an observed-support representation and should be checked against the canary before use.

Suggested read-only channel call chains:

1. Truth: load `truth/*.npz` plus `manifest.json` -> read `l_i/k_real/g_i/unit_scale` -> call `supplement_g1.physical_channel_matrix` with manifest `N/c1/c2` and `l_max_cap` -> keep matrix unchanged in receiver units.
2. Proposed: load `result_path_*` from the arm NPZ -> call the same constructor with final path parameters -> compare against `front_H_canary` only when the canary is present (the canary is front H, so this is a stage-consistency check only if the path set is the corresponding front state).
3. Native: select each `result_round{t}_path_*` triplet -> call the same constructor per round -> pair with `decision_t` and the round's saved `round{t}_final_*` arrays. Do not use the auxiliary full-grid arrays as if they were the selected terminal channel without applying the `active_cap` selection in `offgrid.estimate`.

### 2. Reusable support omission/collision and model-error diagnostics

`representation_ledger.match_physical_slots` at `upstream/.../representation_ledger.py:9-38` is directly reusable from frozen truth and estimated path arrays. Give it `np.column_stack((truth_l_i, truth_k_real))` and an estimated `np.column_stack((path_delays, path_dopplers))`. It excludes exact duplicate truth slots from the identifiable denominator (lines 13-24), performs one-to-one matching within tolerance `(0.5, 0.5)` (lines 26-35), and reports `recall`, `identifiable_denominator`, collisions, ambiguity, and contested estimates (lines 35-38). This is the cleanest existing offline physical-slot omission/collision diagnostic because it does not need to invoke a receiver.

`physical_cluster_weights` at `upstream/.../budgeted_support_diagnostics.py:82-103` is also directly reusable with `system` and saved `l_i/k_real`; it retains duplicate/zero physical slots and merges them through `W @ g` (lines 83-87). `fit_physical_cluster` at lines 106-128 performs observed-pilot LS for a truth-position reference without using truth gains/data. It is a diagnostic/oracle adapter and must remain labeled as such; it is not a deployable replay of the frozen arm.

`representation_ledger.merged_truth_ledger` at `representation_ledger.py:41-67` gives exact merged integer dictionary collision/omission accounting, including `K_true`, `K_true_in_receiver_doppler_domain`, and `physical_matching`. However it requires full generator parameter fields `taps`, `l_exp`, `k_exp`, and `chan_coef_exp` at lines 44-54. Frozen `run_local` truth NPZ saves only `coded`, `info`, `data`, `noise`, `l_i`, `k_real`, `g_i`, and `unit_scale` (`src/run_local.py:62-64`), so this exact merged-ledger function cannot be called from stored driver results alone.

`stage_losses` at `representation_ledger.py:70-80` separates `truth_not_in_pool`, `in_pool_not_selected`, `initially_true_then_pruned`, `selected_then_pruned`, and `final_missing`. It requires structured `pool`, `union`, and `final_prune` events carrying `candidate_ids`, `selected_ids`, and `pruned_ids` (lines 73-79). The frozen NPZ stores array leaves only via `run_local.flatten` (`src/run_local.py:23-28`); the arm ledger stores `events` but does not persist those proposal-event dictionaries. Therefore stage-by-stage omission attribution is unavailable offline from the current driver archives.

For fixed integer support, `representation_ledger.representation_error` at `representation_ledger.py:103-155` is a reusable truth-side model/representation diagnostic. It rebuilds merged truth, projects `H_true` onto the supplied support, and reports `E_repr`, projection residual, optional actual-channel error and dense-reference closure. It has the same missing `params` dependency through `merged_truth_ledger` at lines 121-129, and it expects integer support columns; fractional `result_path_dopplers` cannot be passed as integer IDs. `direction_run.channel_audit` at `direction_run.py:59-82` adds projected-vs-outside-span closure, but calls `initial_error` and therefore also requires the full unpersisted generator params and integer support.

The most directly reusable model-error decomposition for the frozen archives is `v3_statistics.residual_decomposition` at `upstream/.../v3_statistics.py:5-24`. After reconstructing `H_true_rx` and `Hhat`, pass saved input `y`, `pilot`, normalized `data_rx`, and the saved working mean (`front_mu` for I1/front or `result_ce_mu` for proposed/native) to obtain exact channel, data, and noise vector terms, cross terms, residual mean square, and closure. It explicitly warns that residual mean square is not a thermal-variance estimate (line 24).

`direction_factorial.residual_ledger` at `direction_factorial.py:14-36` is another exact offline model-error ledger. It requires `snapshot={Htrue,Hhat/y,pilot,data,noise,sigma2_thermal}` and reports pilot-channel error, data-channel error, thermal noise, cross terms, residual energy, and both closures. It is reusable after converting saved `data` and variance into receiver units; it does not require a receiver call. `supplement_h01._cell_record` at `supplement_h01.py:165-193` shows the corresponding channel NMSE denominator as `||Htrue||_F^2` and labels the factorial cells diagnostic-only.

`bandlimited_estimation.external_error_accounting` at `upstream/.../bandlimited_estimation.py:48-101` decomposes fixed-support representation, omitted-support selection, shrinkage, pilot alias, data, noise and numerical components. It requires a `geometry`, selected columns, a fit record, observation, and truth `H/pilot/data/noise/sigma2`; those fit/geometry records are not emitted by `src/run_local.py`, so it is a source pattern rather than a drop-in call for current archives.

### 3. Bits, BER/FER denominators, and saved-decision NPZ schema

The frozen code is systematic LDPC. `build_code` returns `n`, `k`, `free_cols`, and edge structures at `upstream/.../e1_ldpc.py:104-157`; `encode` is `G @ info mod 2` at lines 164-170 and `extract_info` is exactly `coded[free_cols]` at lines 173-175. For the frozen primary metadata, `cell_02_metadata.json` records `code_n=2048`, `code_k=1024`, and bit order `all I then all Q`.

QPSK uses `qpsk_map` at `e1_ldpc.py:178-191`: bits are `[all I bits, then all Q bits]`, bit 1 maps to a negative component. The matching raw hard-bit extractor is `_bits_of_symbol` at `upstream/.../run_classical_baselines_python.py:100-105`: `real < 0` for the first N bits and `imag < 0` for the second N. The frozen LLR convention is `log P(bit=0)/P(bit=1)`, negative means bit 1 (`e1_ldpc.py:20-25`), and `demap_llr` concatenates I/Q LLRs in that order at lines 194-230.

The authoritative offline denominator/error implementation is `supplement_profile.score_errors` at `upstream/.../supplement_profile.py:221-236`: information errors are `count_nonzero(info_hat != info)`; raw detector errors compare the sign-extracted `x_hard` bits to `coded`; decoded codeword errors compare `decoded` to `coded`; denominators are `coded.size` for raw bits and `info.size` for coded information bits; FER is `int(info_errors > 0)` (lines 230-236). The frozen driver's ledger repeats the FER rule by counting `result['info_hat'] != raw['info']` at `src/run_local.py:77-83`.

Current frozen driver NPZ schema by arm:

- Input: `cXX_fYYYYY_input.npz` contains only `y`, `pilot`, and normalized `sigma2` (`src/run_local.py:61-64`).
- Truth: `truth/cXX_fYYYYY.npz` contains `coded`, `info`, `data`, `noise`, `l_i`, `k_real`, `g_i`, `unit_scale` (`src/run_local.py:62-64`).
- All successful arms: top-level `decoded` and `llr`, plus array leaves under `result_*`; all front leaves are under `front_*`, and checkpoint decisions are `decision_0`, `decision_1`, ... (`src/run_local.py:71-79`). `front_decoder_records_*`, `front_ce_inputs_*`, `front_mu`, `front_v`, `front_prior`, `front_channel_llr`, `front_delays`, `front_dopplers`, and `front_gains` are present when emitted by `front` (`src/receiver.py:34-46`).
- I1: `result_final_llr` only from the terminal arm (`src/receiver.py:51-53`), plus front state and `front_H_canary` for the first two frames (`src/run_local.py:73-75`). No final `x_hard`, `info_hat`, path parameters, final detector moments, or final APP/check arrays are saved.
- Proposed: `result_ce_mu`, `result_ce_variance`, `result_ce_prior`, `result_ce_channel_llr`, objective/Gamma history, `result_path_*`, selected shifts/energies/coefficients, weak row variance/effective observation, and final input/APP/check/detector moments (`src/receiver.py:61-97`; names are flattened by `run_local.py:71-75`).
- Native: each coded round's `r['arrays']` is saved under `result_round{t}_*`; `run_native` updates path/state between rounds at `src/receiver.py:125-141`. The `decision_timeline` saves decoded decisions per round, but its per-round `llr` field is not separately written by `run_local.py:76-79`; only the top-level final `llr` is saved.
- Failure: numerical failure writes a marker NPZ containing only `failure=[1]` and the ledger retains the traceback (`src/run_local.py:80-83`).

Saved `decoded` plus truth `coded/info` is enough to exactly recount information-bit errors, FER and decoded-codeword errors offline with `extract_info`; no receiver import is needed beyond the code builder. `tests/verify_saved_decisions.py:1-17` demonstrates the intended recount pattern for earlier saved NPZs: load decoded/truth, index `free_cols`, compare the count to the ledger, and require finite saved LLR/moment arrays.

Raw BER is not fully recoverable from the frozen driver NPZ schema. `score_errors` requires `x_hard`, but `run_local.py` saves only `decoded` and `llr` plus flattened `result.arrays`; `x_hard` is never inserted. Proposed/native arrays include `final_detector_mu`, so a sign-based raw-bit reconstruction may be possible for those detector outputs after validating detector semantics, but I1 has no final detector `mu`/`x_hard`. The sign of saved final `llr` is a decoded-input hard bit and must not be silently relabeled as raw detector BER. Thus exact raw BER denominators are defined by the protocol/source, but exact raw BER values for current driver NPZs are absent unless the raw symbol hard decisions were separately saved.

### 4. Information absent from original stored driver results

The following missing fields block specific diagnostics without rerunning or regenerating the receiver:

1. **Final I1 channel for most frames.** Only `front_H_canary` exists for frames 0 and 1 (`src/run_local.py:73-75`); I1 final `H`/path parameters are not returned (`src/receiver.py:51-53`).
2. **Exact raw detector hard bits.** No arm writes `x_hard`; I1 also lacks final detector posterior `mu`. This blocks exact raw coded BER recount from the ordinary driver NPZs even though `coded` truth is present.
3. **Full merged truth dictionary parameters.** `merged_truth_ledger`, `initial_error`, `representation_error`, and `direction_run.channel_audit` require `taps`, `l_exp`, `k_exp`, and `chan_coef_exp` (`representation_ledger.py:44-54`, `v3_metrics.py:8-35`). The driver saves only physical `l_i`, `k_real`, `g_i` and `unit_scale` (`run_local.py:62-64`), so exact integer dictionary collision/omission attribution is unavailable from stored truth alone.
4. **Structured proposal/pool/prune events.** `stage_losses` needs `candidate_ids`, `selected_ids`, and `pruned_ids` event dictionaries (`representation_ledger.py:70-80`). `flatten` keeps numeric array leaves only (`run_local.py:23-28`), and ordinary frozen `events` do not contain those full event records.
5. **Per-round native decoded LLRs.** Native rounds save decisions and round arrays, but `decision_timeline`'s round LLR is not written (`receiver.py:134-142`; `run_local.py:76-79`). Per-round calibrated/confidence LLR diagnostics cannot be reproduced exactly.
6. **A complete per-frame model-error snapshot.** `v3_statistics.residual_decomposition` needs normalized data and a selected working mean; normalized data must be reconstructed from raw truth using `unit_scale`, and the exact final working mean is absent for I1 terminal. `direction_factorial.residual_ledger` additionally needs a raw/normalized thermal variance and channel snapshot; raw variance is not stored in truth NPZ, although normalized input `sigma2` is available.
7. **A-01 fixed-design fit metadata.** `external_error_accounting` and `supplement_a01_diagnostics.fit_diagnostics` need geometry, selected support design, fit coefficients/rank and truth coefficient maps. Current proposed NPZ has selected diagonal coefficients and CE history but not the required `geometry`/fit objects, so those routines are not direct drop-ins.

### Suggested read-only call chains

```text
truth NPZ + manifest -> physical_channel_matrix -> H_true_rx
arm NPZ result_path_* -> physical_channel_matrix -> Hhat_rx
H_true_rx/Hhat_rx + match_physical_slots -> identifiable physical-slot recall/collision report
H_true_rx/Hhat_rx + input y/pilot + truth data/unit_scale + front_mu/result_ce_mu
    -> v3_statistics.residual_decomposition
H_true_rx/Hhat_rx + normalized snapshot -> direction_factorial.residual_ledger
decoded + truth coded/info + build_code/extract_info -> exact info errors, FER, decoded-codeword errors
```

Keep any output from `match_physical_slots`, residual ledgers, or channel NMSE explicitly offline/truth-bearing. Do not feed reconstructed truth matrices, physical slots, or true gains back into a receiver arm.

## External references

- No external web or paper lookup was needed for this bounded source map.
- Internal version record: `experiments/sp_afdm_frozen_20260920/environment.json` reports Python 3.13.5, NumPy 2.3.5, SciPy 1.17.0, PyTorch 2.10.0+cpu, CPU-only, one thread.

## Related specs

- `experiments/sp_afdm_frozen_20260920/docs/DESIGN.md`, especially “Signal and information contracts” and the receiver-stage contract.
- `experiments/sp_afdm_frozen_20260920/docs/LOCAL_PROTOCOL.md`, especially “Required files to return for analysis” and the dense-canary rule.
- `experiments/sp_afdm_frozen_20260920/protocol/protocol.json` and `protocol/configurations.json` for the registered N=1024/LDPC and arm families.

## Caveats / Not Found

- No confirmation campaign outputs or full native-arm NPZs are present under `results`; only the two-arm smoke archives were inspected for concrete schema names. Native round naming is established from `run_native` source.
- Current source imports NumPy/Torch only in the recorded experiment environment; this lookup did not execute receiver code or experiments.
- The upstream `physical_channel_matrix` is exact for the physical CPP operator and has no gain normalization. It is not a proof that a fractional fitted path set equals the dense preterminal `H_est`; compare against available canaries where applicable.
- `unit_scale` is required to convert saved raw truth data/noise variance into receiver observation units, but the channel matrix itself remains unchanged under the documented uniform input/output scaling.
- Exact per-stage support omissions, exact merged integer-dictionary truth counts, and exact I1 final-channel errors require fields the current driver does not save; do not infer them from `front_*` arrays or from final LLR signs.

## Corrected v3 interface map (supersedes the 70dd0077/old-runner field map)

- Query: re-read the corrected `receiver.py`, the `driver_smoke_v3` manifest/cell metadata and NPZ artifacts, then verify the new offline-report call sites.
- Scope: internal, read-only; no receiver execution, numerical experiment, SSH, or lifecycle/bootstrap operation.
- Date: 2026-09-21

The concrete source is the corrected run recorded by `results/sp_afdm_frozen/corrected_pipeline_20260921/driver_smoke_v3/manifest.json`; its `source` points to the separate `/data/.../experiments/sp_afdm_frozen_corrected_20260921` package. All earlier descriptions tied to commit `70dd0077` or the old flattened `result_*`/`front_*` archive schema are stale. The current artifact is an `evidence.py` v2 envelope and must be read as `payload, identity = load_artifact(path[, expected_identity])`, whose exact implementation is `experiments/sp_afdm_frozen_20260920/src/evidence.py:297-320`; it returns nested dictionaries and copies every referenced array.

### Manifest keys and receiver units

The v3 manifest's actual system keys are `header.system.n_total=1024`, `header.system.c1=0.00244140625`, `header.system.c2=1.9751241797117955e-07`, `header.system.rho=0.5`, `header.system.l_max_cap=102`, and `header.system.k_max_cap=2` (`driver_smoke_v3/manifest.json:202-208`). The registered primary protocol calls the prefix “full declared CPP” (`experiments/sp_afdm_frozen_20260920/protocol/protocol.json:3-14`), but there is no literal `prefix` key in the manifest header. The executable prefix argument is derived as `prefix_length=system.l_max_cap` in `src/run_local.py:151-156`, so the v3 offline call uses `prefix_length=int(manifest["header"]["system"]["l_max_cap"])`, namely 102. The one cell is `manifest.cells[0] = {"id": 2, "snr_db": 7}`; arm configuration keys are `P_M24_I20`, `I1_BP12_r0`, and `N_ep_2_r1` (`manifest.json:136-162`).

The saved v3 truth payload keys are exactly `coded`, `data`, `g_i`, `info`, `k_real`, `l_i`, `noise`, and `unit_scale`; input keys are exactly `pilot`, `sigma2`, and `y`. Their observed shapes are respectively codeword `(2048,)`, information `(1024,)`, symbols/observation `(1024,)`, and eight physical paths for `g_i/k_real/l_i`. The corrected runner's normalization source is `unit_scale=sqrt(2*(1-rho))`, with `y` and `pilot` divided by `unit_scale` and `sigma2` divided by `unit_scale**2` (`src/run_local.py:151-169`); divide saved truth `data` by `unit_scale` when passing it to a receiver-unit residual ledger. Do not rescale `H_true`: call `physical_channel_matrix(n,c1,c2,l_i,k_real,g_i,prefix_length=102)` directly.

### Corrected arm payloads

`src/run_local.py:_arm_payload` (`:173-200`) writes the common nested keys `decision_timeline`, `decoded`, `front`, `info_hat`, `llr`, `result`, and `result_contract`; for non-native states it additionally writes `front_H_coo`, and `run_local.py:349-350` adds dense `front_H_canary` for `frame<2`. The actual v3 `load_artifact` observations are:

- **I1 (`I1_BP12_r0`)**: `result` keys are `final_llr`, `final_input`, `final_app`, `final_check`, `final_detector_hard`, `final_detector_mu`, and `final_detector_variance`. Top-level `llr`, `decoded`, and `info_hat` are present. `front_H_coo` and `front_H_canary` are present; the COO has `rows`, `columns`, `data`, `shape`, and `semantics`, and is the exact actual damped/masked I1 `H_est`. There is no terminal path triplet or separate `final_H`; the terminal decoder uses the front `H` (`src/receiver.py:50-61`). `front` contains the initial `mu/v/prior/channel_llr`, support arrays, `ce_inputs`, and decoder records (`receiver.py:28-48`).
- **Proposed (`P_M24_I20`)**: `result` keys are `ce_channel_llr`, `ce_gamma`, `ce_mu`, `ce_objective_history`, `ce_prior`, `ce_variance`, `effective_y`, `final_app`, `final_check`, `final_detector_app`, `final_detector_mu`, `final_detector_variance`, `final_input`, `path_delays`, `path_dopplers`, `path_gains`, `selected_coefficients`, `selected_shifts`, and `weak_row_variance`. Top-level `llr`, `decoded`, and `info_hat`, plus front H canary/COO, are present. There is no saved `final_H` dense matrix; reconstruct the terminal physical estimate from this result's `path_*` triplet with `physical_channel_matrix` (`receiver.py:62-106`).
- **Native (`N_ep_2_r1`)**: `result` keys are round-prefixed: for the observed one round, `round0_ce_channel_llr`, `round0_ce_gamma`, `round0_ce_mu`, `round0_ce_objective_history`, `round0_ce_prior`, `round0_ce_variance`, `round0_final_app`, `round0_final_check`, `round0_final_detector_app`, `round0_final_detector_mu`, `round0_final_detector_variance`, `round0_final_input`, `round0_path_delays`, `round0_path_dopplers`, and `round0_path_gains`. The source prefixes every `r['arrays']` leaf as `round{t}_{key}` (`receiver.py:130-166`). Top-level `decoded`, `info_hat`, and `llr` are the final completed round; `decision_timeline` records `round`, `elapsed`, `decoded`, and the native snapshot `llr` in the payload. `front` has `native_initial_state` and no H; there is no `front_H_*` or separate final H. Reconstruct `Hhat_t` from each `round{t}_path_*` triplet.

For all three arms, `result_contract.decoder_records` is the saved terminal/round decoder record list, and the decoder metadata states LLR semantics `log P(bit0)/P(bit1)` with all-I then all-Q order. The exact systematic recount remains `extract_info(code, decoded)=decoded[code['free_cols']]` (`upstream/.../e1_ldpc.py:164-175`); v3 `verify_driver_smoke.py:65-70` counts `info_errors` against `truth['info']` and full codeword errors against `truth['coded']`. Thus denominators are `code_k=1024` for information BER and `code_n=2048` for full decoded-codeword BER; FER is the information-error indicator in `run_local.py:209-216`. The saved v3 arm payload does not contain a raw `x_hard` field for proposed/native, and I1 has no final detector posterior beyond its saved I1-specific fields, so exact raw detector BER is still not a generic artifact field.

### Exact reusable offline function interfaces

- `supplement_g1.physical_channel_matrix(n, c1, c2, delays, dopplers, gains, *, prefix_length)` (`upstream/.../supplement_g1.py:18-42`) returns a dense complex NumPy array of shape `(n,n)`, with no gain normalization. It is the exact truth constructor and can rebuild proposed/native `Hhat` from their saved path triplets. The offline call chain is `manifest.header.system` + `truth.{l_i,k_real,g_i}` -> `physical_channel_matrix(..., prefix_length=header.system.l_max_cap)`; arm `result.path_*` or `result.round{t}_path_*` -> the same constructor.
- `representation_ledger.match_physical_slots(truth_slots, estimated_slots=None)` (`upstream/.../representation_ledger.py:9-38`) returns, with no estimates, `{recall: None, reason: "receiver_has_no_physical_slot_estimator", colliding_truth_slots, tolerance}`; with estimates it returns `recall`, `identifiable_denominator`, `matches`, `colliding_truth_slots`, `ambiguous_truth_slots`, `contested_estimate_slots`, `tolerance`, and `scope`. Truth slots are `np.column_stack((truth['l_i'], truth['k_real']))`; estimated slots are the analogous path arrays. Exact duplicate truth slots are excluded from the denominator and one-to-one matching uses tolerance `(0.5,0.5)`.
- `v3_statistics.residual_decomposition(y, H, Hhat, pilot, data, mean)` (`upstream/.../v3_statistics.py:5-24`) returns `component_mean_squares` (channel/data/noise), `cross_terms`, `residual_mean_square`, `relative_vector_closure`, `energy_closure`, and `semantics`. It computes `noise=y-H@(pilot+data)`, `(H-Hhat)@(pilot+mean)`, `H@(data-mean)`, and `y-Hhat@(pilot+mean)` exactly; `residual_mean_square` is explicitly not a thermal-variance estimate. Use saved input `y/pilot`, truth `data/unit_scale`, truth-built `H`, estimated `Hhat`, and `ce_mu` (or I1 `front.mu`).

### `development_report.py` compatibility check

`results/sp_afdm_frozen/development_report.py` uses the corrected manifest keys and helper signatures consistently: `header.system.N_total/c1/c2/l_max_cap` (`:113-116`), `truth.l_i/k_real/g_i/unit_scale` (`:139-145`), `result` with `final_*` or round-prefixed keys through `final_arrays` (`:41-47`, `:156-209`), and the three exact functions (`:101-105`, `:145`, `:201`, `:209`). Its `final_arrays` round stripping matches the observed `round0_` payload. No field-name error was found in those call sites.

Two precondition failures remain material. First, line 107 calls `validate_run`; the current checked-in `evidence.py` validator requires `input/truth` payload `seed` fields at `:399-403`, but the v3 artifacts loaded read-only here have no `seed` key, so this v3 package must use `load_artifact` only as requested. Second, line 109 compares the manifest source hash map to the source argument; the v3 manifest records the separate corrected package (`driver_smoke_v3_recount.json:3-4`) and its 130-file hash map, while the workspace `experiments/sp_afdm_frozen_20260920` map is 131 files with differing `src/analyze.py`, `src/evidence.py`, `src/receiver.py`, `src/run_local.py`, `src/seal.py`, and test hashes. If the report is pointed at the old/current workspace tree, it will fail this identity gate before producing metrics. These are package/validator identity issues, not wrong payload key or helper-argument references.

### Corrected-v3 caveats / absent fields

- No literal manifest `prefix` key exists; report code must derive `prefix_length` from `header.system.l_max_cap` (102) and keep the protocol label “full declared CPP” separate.
- No arm payload stores a key named `final_H`. I1's `front_H_canary` is the front/terminal I1 H state; proposed/native terminal H is reconstructible only from path arrays (`path_*` or `round{t}_path_*`).
- Current artifacts contain one native round (`N_ep_2_r1` configuration `coded_rounds=1`); the source establishes the general `round{t}_` naming, but no multi-round v3 NPZ was present.
- No code was changed and no receiver/validator was run in this lookup; payload key observations came from bundled-NumPy `load_artifact` calls only.

## Minimal staged-campaign lookup (existing 59-arm catalog)

- Query: identify existing lowest-error/strong cost candidates, map E-JSG-like controls, and check rho/fresh-frame interfaces for a minimal fresh campaign.
- Scope: internal, read-only single-frame CSV/catalog lookup.
- Date: 2026-09-21

The only numerical table consulted was `results/sp_afdm_frozen/cost_screen_20260921/analysis_v1/frame_metrics.csv` (one observation: cell 2, frame 0, 7 dB). Its columns are the reusable report schema: `cell,frame,snr_db,arm,family,status,seconds,info_bits,coded_bits,info_errors,code_errors,info_ber,decoded_code_ber,frame_error,channel_nmse,numerical_fallback,front_seconds,refit_seconds,detector_seconds,decoder_seconds,instrumentation_seconds,failed_round_seconds,decoder_calls_front,decoder_calls_terminal_and_rounds,completed_checkpoints,decoder_input_ber,posterior_mean_slicer_ber,front_channel_nmse,channel_scope,saved_raw_detector_ber`. These are descriptive single-frame values, not FER evidence.

Observed candidate rows (info errors / code errors / complete seconds) are:

- I1 lowest-error simple arm: `I1_BP8_r1` = `64 / 135 / 1.0650 s`; the baseline parent arm `I1_BP12_r0` = `78 / 155 / 1.0950 s`. `I1_BP8_r0` is fastest at `1.0095 s` but has `86 / 170`.
- Native EP: fastest `N_ep_2_r1` = `140 / 287 / 0.2763 s`; first zero-error/stronger candidate `N_ep_2_r2` = `0 / 0 / 0.4629 s`; heavier strong check `N_ep_8_r2` = `0 / 0 / 1.0600 s`.
- Native GAMP: fastest `N_gamp_g1_i15_r1` = `76 / 160 / 0.4254 s`; first zero-error candidate `N_gamp_g1_i30_r2` = `0 / 0 / 0.8479 s`; strongest registered grid/round candidate `N_gamp_g4_i40_r3` = `0 / 0 / 2.8063 s`.
- Native bilinear: fastest `N_bilinear_2_r1` = `158 / 315 / 2.2632 s`; zero-error strong candidate `N_bilinear_8_r2` = `0 / 0 / 13.9561 s` (the one-round `N_bilinear_8_r1` is `0 / 0 / 7.0124 s`).
- Proposed/control context: `P_M16_I8` = `0 / 0 / 1.1112 s`, `P_M24_I20` = `0 / 0 / 1.2035 s`, `ABL_mean` = `0 / 0 / 1.1921 s`, `ABL_scalar` = `0 / 0 / 1.1668 s`, `C_M24_I8` = `83 / 152 / 1.1114 s`, and `S_SBL3` = `114 / 213 / 2.6070 s`.

The catalog definitions are exact in `experiments/sp_afdm_frozen_20260920/protocol/configurations.json`: I1 arms `:38-81`, native EP `:83-177`, native GAMP `:179-231`, proposed `:2-36`, integer controls `:269-304`, and ablations `:362-399`. The initial lookup candidate set below is schema-valid but was superseded before execution by `../staged-plan.md` (which retains both PBiGaBP budgets and S_SBL1, omits fresh C control): `I1_BP12_r0`, `I1_BP8_r1`, `C_M24_I8`, `P_M24_I20`, `P_M16_I8`, `ABL_mean`, `ABL_scalar`, `N_ep_2_r2`, `N_ep_8_r2`, `N_gamp_g1_i30_r2`, `N_gamp_g4_i40_r3`, `S_SBL3`, `N_bilinear_8_r2`.

### E-JSG-like control mapping

`docs/DESIGN.md:239-243` names the existing E-JSG/weak-edge comparison as sparse BP on the actual I1 channel with full mean and weak moments. In this catalog, the actual-I1-H/new-terminal six-arm family is `C_M24_I8`, `C_M24_I12`, `C_M24_I20`, `C_M40_I8`, `C_M40_I12`, `C_M40_I20` (`family=integer_control`, `method=integer_control`). The implementation projects the actual front `H` to integer coefficients and records `stage=no_physical_refit` (`src/receiver.py:72-75`); use `C_M24_I8` as the smallest existing control. The direct weak-edge removal ablation is `ABL_no_weak_variance` (`weak_variance=false`, catalog `:375-378`); `ABL_raw_truncation` removes mean preservation (`preserve_mean=false`, `:380-383`). No new E-JSG module is needed or registered.

### rho and fresh-frame interface

Primary scope is rho=0.5; `protocol/protocol.json:3-14` registers transfer rho=0.2 and 0.7 as separate descriptive cells, while `docs/LOCAL_PROTOCOL.md:96-102` excludes them from primary multiplicity and requires an explicit transfer lock. The current frozen `front` function hard-rejects non-.5 (`src/receiver.py:28-33`, `cfg.rho != .5`), so the existing primary receiver interface cannot simply accept a non-.5 cell without the separately registered transfer path/rescaling contract.

Fresh frame generation already exists: `src/run_local.py:146-156` builds a `SeedSequence`-based `rng_factory`, calls `make_frame(system, code, 0, frame, cell['snr_db'], split=2, rng_factory=...)`, then applies `physical_observation`; the import is `budgeted_support_eval.make_frame` at `run_local.py:32-35`. Reuse this generator and the existing `protocol` seed contract for the proposed 2-cell × 10-frame campaign; no new generator/module is required.

### Caveats

- The candidate errors above are one shared observation at 7 dB; they only rank what to stage and do not support population FER claims.
- The CSV's `saved_raw_detector_ber` is blank for native/proposed where raw hard symbols were not stored; use `info_ber`/`decoded_code_ber` for this stage.
