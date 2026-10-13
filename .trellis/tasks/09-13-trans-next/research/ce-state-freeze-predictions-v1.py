"""Freeze questions and bounded analysis rules; never simulate a receiver."""
import datetime
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
MISSION = ROOT / ".mission/20260914_12-58-51-afdm-unified-exploration"
TARGET = HERE / "ce-state-predictions-v1.json"
if TARGET.exists():
    raise FileExistsError("Prediction registration is immutable; use a new explicit revision")
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
inventory = json.loads((MISSION / "evidence/pred-raw-inventory-v2.json").read_text())
full = json.loads((ROOT / "afdm_sp_joint_unrolled/outputs_dirichlet_shrinkage_20260914/reference-full-index-v1.json").read_text())
groups = {}
for snr in (7, 8):
    groups[str(snr)] = {label: sorted(r["block"] for r in full["records"]
                                   if r["snr"] == snr and bool(r["scores"]["FER"]) == failed)
                        for label, failed in (("original_FULL_failure", True), ("original_FULL_success", False))}
    assert sorted(groups[str(snr)]["original_FULL_failure"] + groups[str(snr)]["original_FULL_success"]) == list(range(32))
n = np.arange(1024)
c1, c2 = 5/(2*1024), (np.sqrt(2)-1)/(2*1024**2)
pilots = {}
for b in (338, 855):
    time_pilot = np.sqrt(.5) * np.exp(-1j*np.pi*b*n*n/1024)
    pilots[f"b{b}"] = np.exp(2j*np.pi*c2*n*n) * np.fft.fft(np.exp(2j*np.pi*c1*n*n)*time_pilot) / np.sqrt(1024)
    np.testing.assert_allclose(np.vdot(pilots[f"b{b}"], pilots[f"b{b}"]).real, 512, rtol=1e-12)
pilot_file = HERE / "ce-state-frozen-pilots-v1.npz"
if pilot_file.exists():
    raise FileExistsError(pilot_file)
np.savez(pilot_file, **pilots)
files = [
    HERE / "ce-state-theory-v1.md", HERE / "ce-state-theory-checks-v1.json",
    HERE / "ce-state-literature-map-v1.md", HERE / "m3-final-plan-v1.md",
    HERE / "dirichlet-shrinkage-v1.md", HERE / "dirichlet-shrinkage-results-v1.json",
    HERE / "pred-old-risk-contract-v1.json",
    ROOT / "afdm_sp_joint_unrolled/outputs_ce_state_20260915/pred-old-risk-v1/summary.json",
    ROOT / "afdm_sp_joint_unrolled/outputs_ce_state_20260915/pred-old-risk-v1/local-audit-v1.json",
    MISSION / "evidence/pred-raw-inventory-v2.json", pilot_file, Path(__file__),
]
record = {
    "schema": "ce-state-predictions-v1", "frozen_at_utc": now,
    "authority": ".mission/20260914_12-58-51-afdm-unified-exploration/20260914_12-58-51-afdm-unified-exploration.csv",
    "review_independence": "weak", "registration_is_not_scientific_confirmation": True,
    "source_files_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
    "source_code_at_freeze": {str((ROOT/"afdm_sp_joint_unrolled"/p).relative_to(ROOT)):
        hashlib.sha256((ROOT/"afdm_sp_joint_unrolled"/p).read_bytes()).hexdigest()
        for p in ("classical_joint_unrolled.py", "supplement_feedback.py", "dirichlet_gain_prior.py",
                  "dirichlet_prior.py", "direction_receiver.py", "budgeted_support_diagnostics.py")},
    "implementation_binding": "DICT/oracle interface changes will be hashed in immutable per-stage contracts before calls; this prediction file will not be edited",
    "exposure": {
        "classification": "retrospective for DIR, old G1 FULL and N256; newly computed interventions on already exposed development inputs are not independent confirmation",
        "DIR": {"level": "retrospective", "read_endpoints": "engineering/full development counts, FER/CE and all strength results already read before this freeze",
                "evidence_latest_known_at": "2026-09-14T15:29:43.273932+00:00", "exact_first_human_read_time": "not recoverable; do not claim blinding",
                "strengths": [.01, .1, 1.], "online_strength": .1, "arms": ["ridge", "diagonal", "dirichlet"],
                "qualified_correlated_shrinkage": False, "ordinary_ridge_is_not_innovation": True},
        "N256": {"level": "retrospective", "blocks": 16, "N": 256, "model": "UWA integer-delay/full-fractional-Doppler explicit CPP physical G1",
                 "coding": "uncoded iid QPSK", "snrs": [10,20], "W": 2, "rho": .5,
                 "nomination": [40,44], "actual_support": "cluster-expanded stored supports, not K24",
                 "missing": ["CE-input mu", "g_previous", "A", "lambda/Q/C"], "new_receiver_calls": 0},
        "G1": {"N": 1024, "blocks": 32, "coding": "original frozen LDPC 2048 coded bits/1024 information bits",
               "snrs": [7,8], "W_original": 2, "K": 24, "rho": .5,
               "model": "untruncated physical CPP G1; G0 weights/scaling not substituted",
               "input_scope": "same stored channel, data and noise; no new independent blocks"},
        "original_summaries": [{k:s[k] for k in ("path","sha256","mtime_utc","status","record_count")}
                               for s in inventory["summaries"]],
    },
    "questions": [
        {"id":"P1", "kind":"restricted geometric prediction", "direction":"gamma=1 only where pilot-only Gram orthogonality is established",
         "target":"actual K24 active supports, grouped by W2/W3/W4 and initial vs feedback design",
         "input":"G=A^H A; E=||p+mu||^2; K; support; pilot/source identity",
         "definition":"gamma=(E/K)tr(G^-1); rank-deficient designs reported separately, not pseudoinverted into a finite gamma",
         "strata":[{"arm":"C33/W3","state":"initial pilot-only","prediction":1},
                   {"arm":"C54/W4","state":"initial pilot-only","prediction":1},
                   {"arm":"P02/W2","state":"historical initial/feedback","prediction":None,"known_sample_max":1.026229},
                   {"arm":"P03/W3,P04/W4","state":"initial","prediction":None},
                   {"arm":"all new arms","state":"feedback","prediction":None}],
         "assumptions":["physical delta=5l+k","canonical frozen pilot","full-rank equal-energy selected columns",
                        "orthogonality condition must be checked, not inferred from max coherence"],
         "numerical_tolerance":{"complex64":1e-4,"complex128":1e-9},
         "interval":"report per-SNR distribution/range and channel-cluster paired bootstrap only for predeclared contrasts; algebraic identity does not need sampling CI",
         "falsification":"valid stated premises with gamma outside dtype error bound refutes implementation/claimed application; failed premises are a recorded applicability failure",
         "five_percent_rule":"not used as a cross-W guarantee or total-NMSE attribution",
         "novelty":"known algebraic consequence; not counted as a new independent scientific prediction"},
        {"id":"P2", "kind":"undirected paired oracle intervention", "direction":None, "predicted_reduction_range":None,
         "target":"O2 final original FULL CE support and previous at t=9, every block at 7/8dB",
         "input":"saved A/mu/previous/lambda/weights; true gS from Frobenius projection; true data/noise for oracle accounting",
         "primary":"coefficient squared error after-minus-before; ratio 1-sum(error_after)/sum(error_before)",
         "secondary":"normalized coefficient error and exact four-vector/six-cross-term decomposition",
         "groups":groups, "group_definition":"original FULL information-block FER; fixed now; subgroups are descriptive",
         "assumptions":["fixed S and previous","rebuild A using true already-scaled d","mean CE ignores data variance",
                        "if prior enabled recompute its A-energy scaling","actual GLS uses sigma2*C^-1"],
         "interval":{"unit":"32 independent channel clusters retaining both SNRs","draws":20000,"seed":202609150302,
                     "primary_family_size":4,"method":"percentile Bonferroni simultaneous 95% for 2 SNR x absolute/ratio",
                     "subgroup_intervals":"95% descriptive, subgroup labels fixed before intervention"},
         "undefined":"zero denominator makes ratio undefined, including any bootstrap draw; report count and no silent omission",
         "falsification":"not a directional hypothesis; record positive/negative/inconclusive continuous effect without post-hoc direction",
         "causal_boundary":"A/B/c and tail/noise projections change jointly; 50%/20% never label a dominant cause"},
        {"id":"P3", "kind":"retrospective risk ranking question", "direction":None, "ranking":None,
         "target":"original DIR 3 penalties x 3 strengths offline and fixed .1 online",
         "input":"original initial observed gains define delay-group centers; epsilon=.05; 128-point fixed quadrature; trace-matched precision",
         "prior_policy":"reuse original build_precision only; no fit to true gains, tail or this batch's outcomes",
         "risk_formula":"||L*m_g+c+B*m_eta||^2+tr(L*Rg*L^H+B*Ceta*B^H)+2Re tr(L*Cg_eta*B^H)",
         "assumptions":["freeze A/S/W/Q/previous/lambda within each solve","include c=M^-1 lambda previous",
                        "nominal zero means/independence must be labelled model assumptions, not selected-data truths"],
         "identifiability_gap":"conditional means and gain-disturbance cross covariance not identified by the supplied penalty; no supported prospective ranking exists",
         "interval":"reuse original 32-channel paired DIR intervals, all strengths reported; no new receiver or strength reselection",
         "falsification":"no pre-exposure ranking was frozen; report retrospective agreement/disagreement without a prediction-success label",
         "oracle":"true-g/true-tail spectra and realized risks explicitly oracle-only, never deployable predictions"}
    ],
    "pilot_stage":{
        "N":1024,"rho":.5,"c1":c1,"c2":c2,"l_max":102,"K":24,
        "arms":[{"id":"P02","pilot":"stored_p0","W":2},{"id":"P03","pilot":"stored_p0","W":3},
                {"id":"C33","pilot":"b338","W":3},{"id":"P04","pilot":"stored_p0","W":4},
                {"id":"C54","pilot":"b855","W":4}],
        "new_pilots_file":str(pilot_file.relative_to(ROOT)),
        "pilot_formula":"s_b[n]=sqrt(rho)exp(-j*pi*b*n^2/N); p_b=DAFT_c1,c2(s_b); b855 occupies only part of DAFT bins",
        "baseline":"original first initialization/selection and fit, K24; original p0 arrays retained bitwise",
        "paired_observation":"y_new=y_old+H_true*(p_new-p_old); H_true confined to simulator and oracle scoring",
        "primary":"per-channel equal mean of linear complete-H NMSE at 7 and 8dB",
        "contrasts":["C33-P03","C33-P02","C54-P04","C54-P02"],
        "bootstrap":{"unit":"32 channel clusters; both SNRs resampled together","draws":20000,
                     "seed":202609150402,"method":"percentile with Bonferroni four contrasts, simultaneous 95%"},
        "promotion":"both relevant CI upper limits <0 and both SNR point differences nonpositive; engineering/raw checks pass",
        "max_promotions":1,"tie_break":"smaller primary mean NMSE, exact tie W3",
        "stop":"CI crossing zero is insufficient evidence; no extra roots, blocks or FER; no universal-null claim",
        "engineering_blocks":[0,20],"engineering_included_in_32":True,
        "run_order":"after fixed engineering blocks, seeded permutation of block/SNR/arm tasks; seed 202609150401",
        "signal_constraints":{"native_payload_papr_db_max":12.,"native_payload_peak_power_max":16.,
            "normalization":"component energies fixed; no per-block renormalization or clipping",
            "oversampling":"also report 4x centered-DFT zero-pad interpolation, payload and CPP separately; native gate retains original definition",
            "hardware_claim":False}
    },
    "oracle_stage":{
        "O1_S":"complete H_true p cancellation; detection with original final-S Frobenius projection; frozen terminal prior/noise/temperature",
        "O1_F":"complete physical H in cancellation and detection; include every strictly nonzero matrix entry; same BP kernel/iterations; graph density and cost reported",
        "O2":"t=9 original FULL S and previous; one true-data CE per point, zero BP/LDPC",
        "O3":"preserve t0; only replace CE-local mu with true d at t=1 after ce(1), before x_total; original previous retained; mode=mean; legal t1 BP/checkpoint decode; normal feedback t>=2",
        "default_replay":"reuse existing equality evidence when source changes cannot affect old route; otherwise only four engineering points",
        "engineering_included_in_block_budget":True,"not_information_theoretic_upper_bound":True
    },
    "conditional_FER":{
        "qualified_shrinkage":None,"strong_classical":"original FULL plus zero-centered identity precision strength .1 (DirichletGainPrior kind=ridge); source and scale same as original DIR",
        "comparison":"p*/W* against stored_p0/W*, same K24; original W2 is descriptive anchor",
        "max_new_F":128,"outer_iterations":10,"new_confirmation":False,
        "excluded_if":"no PILOT-02 promotion","no_0p2dB_confirmation_from_32_blocks":True
    },
    "resource_contract":{
        "device":"CPU; NVML mismatch verified in inventory","global_workers_max":2,"threads_per_worker":1,
        "stage_wall_seconds_max":7200,"stage_new_peak_bytes_max":20*1024**3,
        "includes":"setup, execution, failures, intermediates; internal CE/BP/LDPC itemized but not added again to F budget",
        "stage_caps":{"O1_S":{"T":64,"D":64},"O1_F":{"T":64,"D":64},"O2":{"CE":64},
                      "O3":{"F":64,"CE_per_F":9},"pilot_initial":{"CE":320},
                      "pilot_conditional":{"F":128},"shared_default":{"F":4},
                      "SYN_candidate_likelihood":{"offline_differences":5120,"BP":0,"LDPC":0}},
        "overall_original_max":{"F":324,"T":128,"D":128,"independent_CE":384},
        "current_conditional_max_F":196,
        "memory":"check MemAvailable and estimated peak before each stage; O1-F engineering must establish dense-graph feasibility before remaining 60 points",
        "overrun":"save failure/cost and stop affected stage; no automatic increase or alternate detector",
        "server_write_root":"/data/guoyikun","tmux_prefix":"g_",
        "no_extra_data":"original G0/raw/failed runs/CONF/D_test immutable; no repeated completed experiments"
    },
    "future_confirmation":"nontrivial predictive validation and method CONF are separate deferred scopes; no present candidate or claim is promoted by this file",
    "publication_gate":"no requirement to hit two predictions; algebra and null/inconclusive results do not establish publishability"
}
TARGET.write_text(json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False)+"\n")
digest = hashlib.sha256(TARGET.read_bytes()).hexdigest()
TARGET.with_suffix(".sha256").write_text(digest+"  "+TARGET.name+"\n")
print(json.dumps({"frozen_at_utc":now,"path":str(TARGET),"sha256":digest,
                  "receiver_calls":0,"original_failure_groups":groups}))
