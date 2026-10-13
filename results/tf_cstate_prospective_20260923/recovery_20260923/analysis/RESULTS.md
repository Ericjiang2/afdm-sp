# Prospective frozen TF versus TF+CSTATE

Independent new observations; 1,024 complete pairs per SNR. Only 6.5 dB is the preregistered primary confirmation cell.

Evidence integrity: **pass**. Primary decision: **pass**.

| SNR (dB) | TF info FER [95% CP] | TF+CSTATE info FER [95% CP] | h (TF only correct) | r (CSTATE only correct) | Δ̂ combined−TF |
|---:|---:|---:|---:|---:|---:|
| 6 | 0.201172 [0.177018, 0.227057] | 0.059570 [0.045869, 0.075866] | 0 | 145 | -0.141602 |
| 6.5 | 0.039062 [0.028051, 0.052814] | 0.005859 [0.002153, 0.012709] | 0 | 34 | -0.033203 |
| 7 | 0.019531 [0.011970, 0.030004] | 0.004883 [0.001587, 0.011358] | 0 | 15 | -0.014648 |

At 6.5 dB the complete paired 2×2 table is both correct=984, TF only correct=0, TF+CSTATE only correct=34, neither correct=6.
The conservative one-sided 95% upper bound for Δ is -0.01950560; the frozen gate requires it to be strictly below zero and integrity valid.
The auxiliary exact conditional McNemar one-sided p-value is 5.8207661e-11; it does not replace the primary bound.

| SNR (dB) | Triggered (fraction) | Rescued | Harmed | Remaining triggered failures | Both wrong (all frames) | Undetected TF / combined | 0.5 s system failures TF / combined | Missing TF / combined | Compact fallbacks |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 6 | 206 (0.2012) | 145 | 0 | 61 | 61 | 0 / 0 | 206 / 79 | 0 / 0 | 0 |
| 6.5 | 40 (0.0391) | 34 | 0 | 6 | 6 | 0 / 0 | 40 / 10 | 0 / 0 | 0 |
| 7 | 20 (0.0195) | 15 | 0 | 5 | 5 | 0 / 0 | 20 / 6 | 0 / 0 | 0 |

| SNR (dB) | 0.5 s both correct | TF only correct | Combined only correct | Neither correct | Ready decoded errors TF / combined |
|---:|---:|---:|---:|---:|---:|
| 6 | 818 | 0 | 127 | 79 | 206 / 79 |
| 6.5 | 984 | 0 | 30 | 10 | 40 / 10 |
| 7 | 1004 | 0 | 14 | 6 | 20 / 6 |

| SNR (dB) | Zero syndrome but coded word wrong TF / combined | Information word correct but other coded bits wrong TF / combined |
|---:|---:|---:|
| 6 | 0 / 0 | 0 / 0 |
| 6.5 | 0 / 0 | 0 / 0 |
| 7 | 0 / 0 | 0 / 0 |

| SNR (dB) | TF info bit errors / BER | Combined info bit errors / BER | TF coded bit errors / BER | Combined coded bit errors / BER |
|---:|---:|---:|---:|---:|
| 6 | 17771 / 0.01694775 | 4863 / 0.00463772 | 35786 / 0.01706409 | 9868 / 0.00470543 |
| 6.5 | 4836 / 0.00461197 | 641 / 0.00061131 | 9579 / 0.00456762 | 1362 / 0.00064945 |
| 7 | 2807 / 0.00267696 | 452 / 0.00043106 | 5665 / 0.00270128 | 899 / 0.00042868 |

A missing or unready 0.5 s decision is a system deadline failure on the full 1,024-pair denominator, not a fabricated bit error. Ready-only decoded error counts and checkpoint identities are in summary.json and CSV.

Complete receiver latency includes input load, native replay, trigger, conditional CSTATE, raw serialization, and durable decision write. The final ledger append and paired audit are outside the receiver clock.

| SNR (dB) | Cohort | TF mean / p95 (s) | Combined mean / p95 (s) | Paired Δ mean / p95 (s) | Mean paired ratio | Ratio of means |
|---:|---|---:|---:|---:|---:|---:|
| 6 | all (n=1024) | 0.3334 / 0.3787 | 0.3775 / 0.5686 | 0.0441 / 0.2326 | 1.1336 | 1.1324 |
| 6 | trigger (n=206) | 0.3405 / 0.3890 | 0.5563 / 0.6064 | 0.2157 / 0.2789 | 1.6391 | 1.6335 |
| 6 | nontrigger (n=818) | 0.3316 / 0.3759 | 0.3325 / 0.3781 | 0.0009 / 0.0533 | 1.0063 | 1.0028 |
| 6.5 | all (n=1024) | 0.3285 / 0.3686 | 0.3375 / 0.3804 | 0.0091 / 0.0627 | 1.0324 | 1.0276 |
| 6.5 | trigger (n=40) | 0.3350 / 0.3763 | 0.5615 / 0.6013 | 0.2266 / 0.2732 | 1.6827 | 1.6764 |
| 6.5 | nontrigger (n=984) | 0.3282 / 0.3682 | 0.3284 / 0.3677 | 0.0002 / 0.0528 | 1.0059 | 1.0006 |
| 7 | all (n=1024) | 0.3251 / 0.3648 | 0.3298 / 0.3659 | 0.0047 / 0.0528 | 1.0182 | 1.0146 |
| 7 | trigger (n=20) | 0.3459 / 0.3773 | 0.5692 / 0.6299 | 0.2233 / 0.2966 | 1.6524 | 1.6454 |
| 7 | nontrigger (n=1004) | 0.3246 / 0.3641 | 0.3250 / 0.3614 | 0.0004 / 0.0483 | 1.0056 | 1.0012 |

Full complete-receiver latency distributions follow. Each five-number cell is mean / median / p90 / p95 / maximum. Paired Δ is combined minus TF; paired ratio is combined divided by TF.

| SNR (dB) | Cohort | Quantity | Mean / median / p90 / p95 / max |
|---:|---|---|---:|
| 6 | all (n=1024) | TF seconds | 0.3334 / 0.3260 / 0.3657 / 0.3787 / 0.4819 |
| 6 | all (n=1024) | Combined seconds | 0.3775 / 0.3312 / 0.5478 / 0.5686 / 0.7486 |
| 6 | all (n=1024) | Paired Δ seconds | 0.0441 / 0.0066 / 0.2151 / 0.2326 / 0.3744 |
| 6 | all (n=1024) | Paired ratio | 1.1336 / 1.0210 / 1.6394 / 1.7087 / 2.0992 |
| 6 | trigger (n=206) | TF seconds | 0.3405 / 0.3343 / 0.3696 / 0.3890 / 0.4548 |
| 6 | trigger (n=206) | Combined seconds | 0.5563 / 0.5478 / 0.5911 / 0.6064 / 0.7486 |
| 6 | trigger (n=206) | Paired Δ seconds | 0.2157 / 0.2151 / 0.2560 / 0.2789 / 0.3744 |
| 6 | trigger (n=206) | Paired ratio | 1.6391 / 1.6394 / 1.7902 / 1.8358 / 2.0992 |
| 6 | nontrigger (n=818) | TF seconds | 0.3316 / 0.3236 / 0.3637 / 0.3759 / 0.4819 |
| 6 | nontrigger (n=818) | Combined seconds | 0.3325 / 0.3247 / 0.3647 / 0.3781 / 0.4683 |
| 6 | nontrigger (n=818) | Paired Δ seconds | 0.0009 / 0.0005 / 0.0435 / 0.0533 / 0.1258 |
| 6 | nontrigger (n=818) | Paired ratio | 1.0063 / 1.0016 / 1.1359 / 1.1668 / 1.3966 |
| 6.5 | all (n=1024) | TF seconds | 0.3285 / 0.3230 / 0.3589 / 0.3686 / 0.4211 |
| 6.5 | all (n=1024) | Combined seconds | 0.3375 / 0.3243 / 0.3650 / 0.3804 / 0.6200 |
| 6.5 | all (n=1024) | Paired Δ seconds | 0.0091 / 0.0013 / 0.0513 / 0.0627 / 0.2949 |
| 6.5 | all (n=1024) | Paired ratio | 1.0324 / 1.0039 / 1.1643 / 1.2037 / 1.9073 |
| 6.5 | trigger (n=40) | TF seconds | 0.3350 / 0.3270 / 0.3660 / 0.3763 / 0.4211 |
| 6.5 | trigger (n=40) | Combined seconds | 0.5615 / 0.5575 / 0.5957 / 0.6013 / 0.6200 |
| 6.5 | trigger (n=40) | Paired Δ seconds | 0.2266 / 0.2260 / 0.2691 / 0.2732 / 0.2949 |
| 6.5 | trigger (n=40) | Paired ratio | 1.6827 / 1.7011 / 1.8275 / 1.8375 / 1.9073 |
| 6.5 | nontrigger (n=984) | TF seconds | 0.3282 / 0.3227 / 0.3587 / 0.3682 / 0.4119 |
| 6.5 | nontrigger (n=984) | Combined seconds | 0.3284 / 0.3228 / 0.3599 / 0.3677 / 0.4279 |
| 6.5 | nontrigger (n=984) | Paired Δ seconds | 0.0002 / -0.0024 / 0.0472 / 0.0528 / 0.1100 |
| 6.5 | nontrigger (n=984) | Paired ratio | 1.0059 / 0.9928 / 1.1498 / 1.1699 / 1.3461 |
| 7 | all (n=1024) | TF seconds | 0.3251 / 0.3187 / 0.3554 / 0.3648 / 0.4404 |
| 7 | all (n=1024) | Combined seconds | 0.3298 / 0.3202 / 0.3557 / 0.3659 / 0.6367 |
| 7 | all (n=1024) | Paired Δ seconds | 0.0047 / 0.0011 / 0.0434 / 0.0528 / 0.3109 |
| 7 | all (n=1024) | Paired ratio | 1.0182 / 1.0036 / 1.1414 / 1.1746 / 1.9755 |
| 7 | trigger (n=20) | TF seconds | 0.3459 / 0.3400 / 0.3691 / 0.3773 / 0.3912 |
| 7 | trigger (n=20) | Combined seconds | 0.5692 / 0.5585 / 0.6108 / 0.6299 / 0.6367 |
| 7 | trigger (n=20) | Paired Δ seconds | 0.2233 / 0.2138 / 0.2706 / 0.2966 / 0.3109 |
| 7 | trigger (n=20) | Paired ratio | 1.6524 / 1.6202 / 1.8114 / 1.8736 / 1.9755 |
| 7 | nontrigger (n=1004) | TF seconds | 0.3246 / 0.3186 / 0.3543 / 0.3641 / 0.4404 |
| 7 | nontrigger (n=1004) | Combined seconds | 0.3250 / 0.3196 / 0.3541 / 0.3614 / 0.4635 |
| 7 | nontrigger (n=1004) | Paired Δ seconds | 0.0004 / 0.0005 / 0.0413 / 0.0483 / 0.0865 |
| 7 | nontrigger (n=1004) | Paired ratio | 1.0056 / 1.0016 / 1.1319 / 1.1549 / 1.2843 |

The 17 exclusive CSTATE stages are below. Each stage includes zero work for nontriggered frames; stage share divides by total complete branch time within the stated cohort.

| SNR (dB) | Cohort | Stage | Mean (s) | Median (s) | p90 (s) | p95 (s) | Max (s) | Share |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 6 | all (n=1024) | message_handling | 0.000054 | 0.000000 | 0.000259 | 0.000281 | 0.000418 | 0.0011 |
| 6 | all (n=1024) | y_transform | 0.000021 | 0.000000 | 0.000101 | 0.000113 | 0.000188 | 0.0004 |
| 6 | all (n=1024) | geometry_setup | 0.000232 | 0.000000 | 0.001100 | 0.001196 | 0.001954 | 0.0048 |
| 6 | all (n=1024) | structural_field_build | 0.003072 | 0.000000 | 0.014104 | 0.014638 | 0.053181 | 0.0635 |
| 6 | all (n=1024) | structural_scoring | 0.000398 | 0.000000 | 0.002000 | 0.002075 | 0.003014 | 0.0082 |
| 6 | all (n=1024) | structural_selection_trace | 0.001007 | 0.000000 | 0.004703 | 0.004819 | 0.069055 | 0.0208 |
| 6 | all (n=1024) | structural_refit_refresh | 0.000647 | 0.000000 | 0.003650 | 0.003705 | 0.005720 | 0.0134 |
| 6 | all (n=1024) | structural_fallback_direct | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.0000 |
| 6 | all (n=1024) | local_refinement | 0.019447 | 0.000000 | 0.095122 | 0.099221 | 0.138229 | 0.4020 |
| 6 | all (n=1024) | geometry_finalization | 0.000323 | 0.000000 | 0.001516 | 0.001598 | 0.002968 | 0.0067 |
| 6 | all (n=1024) | geometry_wrapper_overhead | 0.000031 | 0.000000 | 0.000145 | 0.000158 | 0.000254 | 0.0006 |
| 6 | all (n=1024) | wrapper_validation | 0.000014 | 0.000000 | 0.000066 | 0.000069 | 0.000108 | 0.0003 |
| 6 | all (n=1024) | channel_construction | 0.000007 | 0.000000 | 0.000032 | 0.000033 | 0.000049 | 0.0001 |
| 6 | all (n=1024) | tf | 0.004034 | 0.000000 | 0.019287 | 0.020549 | 0.029528 | 0.0834 |
| 6 | all (n=1024) | ldpc | 0.004074 | 0.000000 | 0.018755 | 0.023921 | 0.034983 | 0.0842 |
| 6 | all (n=1024) | checkpoint_write | 0.003834 | 0.000000 | 0.016607 | 0.020722 | 0.048692 | 0.0793 |
| 6 | all (n=1024) | raw_serialization_hash | 0.011182 | 0.000000 | 0.053174 | 0.057507 | 0.114119 | 0.2311 |
| 6 | trigger (n=206) | message_handling | 0.000269 | 0.000259 | 0.000300 | 0.000307 | 0.000418 | 0.0011 |
| 6 | trigger (n=206) | y_transform | 0.000107 | 0.000101 | 0.000121 | 0.000125 | 0.000188 | 0.0004 |
| 6 | trigger (n=206) | geometry_setup | 0.001154 | 0.001099 | 0.001295 | 0.001319 | 0.001954 | 0.0048 |
| 6 | trigger (n=206) | structural_field_build | 0.015272 | 0.014103 | 0.015346 | 0.019064 | 0.053181 | 0.0635 |
| 6 | trigger (n=206) | structural_scoring | 0.001981 | 0.002000 | 0.002184 | 0.002338 | 0.003014 | 0.0082 |
| 6 | trigger (n=206) | structural_selection_trace | 0.005008 | 0.004702 | 0.005217 | 0.005795 | 0.069055 | 0.0208 |
| 6 | trigger (n=206) | structural_refit_refresh | 0.003217 | 0.003650 | 0.004044 | 0.004126 | 0.005720 | 0.0134 |
| 6 | trigger (n=206) | structural_fallback_direct | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.0000 |
| 6 | trigger (n=206) | local_refinement | 0.096668 | 0.095103 | 0.106449 | 0.110369 | 0.138229 | 0.4020 |
| 6 | trigger (n=206) | geometry_finalization | 0.001607 | 0.001516 | 0.001845 | 0.001919 | 0.002968 | 0.0067 |
| 6 | trigger (n=206) | geometry_wrapper_overhead | 0.000154 | 0.000145 | 0.000180 | 0.000219 | 0.000254 | 0.0006 |
| 6 | trigger (n=206) | wrapper_validation | 0.000068 | 0.000066 | 0.000076 | 0.000084 | 0.000108 | 0.0003 |
| 6 | trigger (n=206) | channel_construction | 0.000032 | 0.000032 | 0.000035 | 0.000037 | 0.000049 | 0.0001 |
| 6 | trigger (n=206) | tf | 0.020053 | 0.019286 | 0.021500 | 0.023357 | 0.029528 | 0.0834 |
| 6 | trigger (n=206) | ldpc | 0.020249 | 0.018746 | 0.024464 | 0.025513 | 0.034983 | 0.0842 |
| 6 | trigger (n=206) | checkpoint_write | 0.019059 | 0.016602 | 0.030926 | 0.033391 | 0.048692 | 0.0793 |
| 6 | trigger (n=206) | raw_serialization_hash | 0.055583 | 0.053174 | 0.064492 | 0.072602 | 0.114119 | 0.2311 |
| 6 | nontrigger (n=818) | message_handling | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6 | nontrigger (n=818) | y_transform | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6 | nontrigger (n=818) | geometry_setup | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6 | nontrigger (n=818) | structural_field_build | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6 | nontrigger (n=818) | structural_scoring | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6 | nontrigger (n=818) | structural_selection_trace | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6 | nontrigger (n=818) | structural_refit_refresh | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6 | nontrigger (n=818) | structural_fallback_direct | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6 | nontrigger (n=818) | local_refinement | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6 | nontrigger (n=818) | geometry_finalization | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6 | nontrigger (n=818) | geometry_wrapper_overhead | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6 | nontrigger (n=818) | wrapper_validation | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6 | nontrigger (n=818) | channel_construction | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6 | nontrigger (n=818) | tf | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6 | nontrigger (n=818) | ldpc | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6 | nontrigger (n=818) | checkpoint_write | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6 | nontrigger (n=818) | raw_serialization_hash | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6.5 | all (n=1024) | message_handling | 0.000010 | 0.000000 | 0.000000 | 0.000000 | 0.000308 | 0.0011 |
| 6.5 | all (n=1024) | y_transform | 0.000004 | 0.000000 | 0.000000 | 0.000000 | 0.000150 | 0.0004 |
| 6.5 | all (n=1024) | geometry_setup | 0.000044 | 0.000000 | 0.000000 | 0.000000 | 0.001426 | 0.0046 |
| 6.5 | all (n=1024) | structural_field_build | 0.000666 | 0.000000 | 0.000000 | 0.000000 | 0.053334 | 0.0687 |
| 6.5 | all (n=1024) | structural_scoring | 0.000079 | 0.000000 | 0.000000 | 0.000000 | 0.002808 | 0.0081 |
| 6.5 | all (n=1024) | structural_selection_trace | 0.000189 | 0.000000 | 0.000000 | 0.000000 | 0.006743 | 0.0195 |
| 6.5 | all (n=1024) | structural_refit_refresh | 0.000142 | 0.000000 | 0.000000 | 0.000000 | 0.004604 | 0.0147 |
| 6.5 | all (n=1024) | structural_fallback_direct | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.0000 |
| 6.5 | all (n=1024) | local_refinement | 0.003927 | 0.000000 | 0.000000 | 0.000000 | 0.132270 | 0.4046 |
| 6.5 | all (n=1024) | geometry_finalization | 0.000061 | 0.000000 | 0.000000 | 0.000000 | 0.002498 | 0.0063 |
| 6.5 | all (n=1024) | geometry_wrapper_overhead | 0.000006 | 0.000000 | 0.000000 | 0.000000 | 0.000203 | 0.0006 |
| 6.5 | all (n=1024) | wrapper_validation | 0.000003 | 0.000000 | 0.000000 | 0.000000 | 0.000086 | 0.0003 |
| 6.5 | all (n=1024) | channel_construction | 0.000001 | 0.000000 | 0.000000 | 0.000000 | 0.000041 | 0.0001 |
| 6.5 | all (n=1024) | tf | 0.000770 | 0.000000 | 0.000000 | 0.000000 | 0.026656 | 0.0794 |
| 6.5 | all (n=1024) | ldpc | 0.000740 | 0.000000 | 0.000000 | 0.000000 | 0.027344 | 0.0763 |
| 6.5 | all (n=1024) | checkpoint_write | 0.000762 | 0.000000 | 0.000000 | 0.000000 | 0.053503 | 0.0785 |
| 6.5 | all (n=1024) | raw_serialization_hash | 0.002300 | 0.000000 | 0.000000 | 0.000000 | 0.094164 | 0.2369 |
| 6.5 | trigger (n=40) | message_handling | 0.000262 | 0.000256 | 0.000290 | 0.000294 | 0.000308 | 0.0011 |
| 6.5 | trigger (n=40) | y_transform | 0.000104 | 0.000100 | 0.000118 | 0.000120 | 0.000150 | 0.0004 |
| 6.5 | trigger (n=40) | geometry_setup | 0.001136 | 0.001105 | 0.001298 | 0.001307 | 0.001426 | 0.0046 |
| 6.5 | trigger (n=40) | structural_field_build | 0.017060 | 0.013949 | 0.015782 | 0.051076 | 0.053334 | 0.0687 |
| 6.5 | trigger (n=40) | structural_scoring | 0.002024 | 0.001978 | 0.002233 | 0.002253 | 0.002808 | 0.0081 |
| 6.5 | trigger (n=40) | structural_selection_trace | 0.004836 | 0.004749 | 0.005307 | 0.005359 | 0.006743 | 0.0195 |
| 6.5 | trigger (n=40) | structural_refit_refresh | 0.003645 | 0.003679 | 0.004150 | 0.004284 | 0.004604 | 0.0147 |
| 6.5 | trigger (n=40) | structural_fallback_direct | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.0000 |
| 6.5 | trigger (n=40) | local_refinement | 0.100527 | 0.099044 | 0.109247 | 0.116237 | 0.132270 | 0.4046 |
| 6.5 | trigger (n=40) | geometry_finalization | 0.001564 | 0.001507 | 0.001626 | 0.001840 | 0.002498 | 0.0063 |
| 6.5 | trigger (n=40) | geometry_wrapper_overhead | 0.000145 | 0.000140 | 0.000159 | 0.000166 | 0.000203 | 0.0006 |
| 6.5 | trigger (n=40) | wrapper_validation | 0.000066 | 0.000064 | 0.000080 | 0.000083 | 0.000086 | 0.0003 |
| 6.5 | trigger (n=40) | channel_construction | 0.000031 | 0.000031 | 0.000033 | 0.000034 | 0.000041 | 0.0001 |
| 6.5 | trigger (n=40) | tf | 0.019723 | 0.019224 | 0.020736 | 0.021026 | 0.026656 | 0.0794 |
| 6.5 | trigger (n=40) | ldpc | 0.018945 | 0.017752 | 0.024113 | 0.025352 | 0.027344 | 0.0763 |
| 6.5 | trigger (n=40) | checkpoint_write | 0.019514 | 0.015438 | 0.031826 | 0.035805 | 0.053503 | 0.0785 |
| 6.5 | trigger (n=40) | raw_serialization_hash | 0.058869 | 0.052849 | 0.084018 | 0.089580 | 0.094164 | 0.2369 |
| 6.5 | nontrigger (n=984) | message_handling | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6.5 | nontrigger (n=984) | y_transform | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6.5 | nontrigger (n=984) | geometry_setup | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6.5 | nontrigger (n=984) | structural_field_build | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6.5 | nontrigger (n=984) | structural_scoring | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6.5 | nontrigger (n=984) | structural_selection_trace | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6.5 | nontrigger (n=984) | structural_refit_refresh | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6.5 | nontrigger (n=984) | structural_fallback_direct | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6.5 | nontrigger (n=984) | local_refinement | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6.5 | nontrigger (n=984) | geometry_finalization | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6.5 | nontrigger (n=984) | geometry_wrapper_overhead | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6.5 | nontrigger (n=984) | wrapper_validation | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6.5 | nontrigger (n=984) | channel_construction | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6.5 | nontrigger (n=984) | tf | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6.5 | nontrigger (n=984) | ldpc | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6.5 | nontrigger (n=984) | checkpoint_write | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 6.5 | nontrigger (n=984) | raw_serialization_hash | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 7 | all (n=1024) | message_handling | 0.000005 | 0.000000 | 0.000000 | 0.000000 | 0.000300 | 0.0010 |
| 7 | all (n=1024) | y_transform | 0.000002 | 0.000000 | 0.000000 | 0.000000 | 0.000122 | 0.0004 |
| 7 | all (n=1024) | geometry_setup | 0.000022 | 0.000000 | 0.000000 | 0.000000 | 0.001299 | 0.0045 |
| 7 | all (n=1024) | structural_field_build | 0.000315 | 0.000000 | 0.000000 | 0.000000 | 0.052704 | 0.0641 |
| 7 | all (n=1024) | structural_scoring | 0.000039 | 0.000000 | 0.000000 | 0.000000 | 0.002242 | 0.0079 |
| 7 | all (n=1024) | structural_selection_trace | 0.000094 | 0.000000 | 0.000000 | 0.000000 | 0.005319 | 0.0191 |
| 7 | all (n=1024) | structural_refit_refresh | 0.000071 | 0.000000 | 0.000000 | 0.000000 | 0.004319 | 0.0144 |
| 7 | all (n=1024) | structural_fallback_direct | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.0000 |
| 7 | all (n=1024) | local_refinement | 0.002006 | 0.000000 | 0.000000 | 0.000000 | 0.119838 | 0.4083 |
| 7 | all (n=1024) | geometry_finalization | 0.000030 | 0.000000 | 0.000000 | 0.000000 | 0.001702 | 0.0060 |
| 7 | all (n=1024) | geometry_wrapper_overhead | 0.000003 | 0.000000 | 0.000000 | 0.000000 | 0.000234 | 0.0006 |
| 7 | all (n=1024) | wrapper_validation | 0.000001 | 0.000000 | 0.000000 | 0.000000 | 0.000074 | 0.0003 |
| 7 | all (n=1024) | channel_construction | 0.000001 | 0.000000 | 0.000000 | 0.000000 | 0.000040 | 0.0001 |
| 7 | all (n=1024) | tf | 0.000379 | 0.000000 | 0.000000 | 0.000000 | 0.020860 | 0.0771 |
| 7 | all (n=1024) | ldpc | 0.000376 | 0.000000 | 0.000000 | 0.000000 | 0.025530 | 0.0766 |
| 7 | all (n=1024) | checkpoint_write | 0.000383 | 0.000000 | 0.000000 | 0.000000 | 0.040581 | 0.0779 |
| 7 | all (n=1024) | raw_serialization_hash | 0.001187 | 0.000000 | 0.000000 | 0.000000 | 0.090100 | 0.2416 |
| 7 | trigger (n=20) | message_handling | 0.000262 | 0.000255 | 0.000290 | 0.000292 | 0.000300 | 0.0010 |
| 7 | trigger (n=20) | y_transform | 0.000104 | 0.000101 | 0.000120 | 0.000121 | 0.000122 | 0.0004 |
| 7 | trigger (n=20) | geometry_setup | 0.001140 | 0.001118 | 0.001263 | 0.001290 | 0.001299 | 0.0045 |
| 7 | trigger (n=20) | structural_field_build | 0.016129 | 0.013945 | 0.015089 | 0.017112 | 0.052704 | 0.0641 |
| 7 | trigger (n=20) | structural_scoring | 0.002000 | 0.001972 | 0.002149 | 0.002164 | 0.002242 | 0.0079 |
| 7 | trigger (n=20) | structural_selection_trace | 0.004807 | 0.004740 | 0.005121 | 0.005228 | 0.005319 | 0.0191 |
| 7 | trigger (n=20) | structural_refit_refresh | 0.003614 | 0.003658 | 0.003739 | 0.004039 | 0.004319 | 0.0144 |
| 7 | trigger (n=20) | structural_fallback_direct | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.0000 |
| 7 | trigger (n=20) | local_refinement | 0.102728 | 0.101402 | 0.113389 | 0.117571 | 0.119838 | 0.4083 |
| 7 | trigger (n=20) | geometry_finalization | 0.001521 | 0.001511 | 0.001575 | 0.001589 | 0.001702 | 0.0060 |
| 7 | trigger (n=20) | geometry_wrapper_overhead | 0.000143 | 0.000140 | 0.000150 | 0.000158 | 0.000234 | 0.0006 |
| 7 | trigger (n=20) | wrapper_validation | 0.000064 | 0.000063 | 0.000072 | 0.000073 | 0.000074 | 0.0003 |
| 7 | trigger (n=20) | channel_construction | 0.000031 | 0.000031 | 0.000033 | 0.000037 | 0.000040 | 0.0001 |
| 7 | trigger (n=20) | tf | 0.019408 | 0.019073 | 0.020705 | 0.020767 | 0.020860 | 0.0771 |
| 7 | trigger (n=20) | ldpc | 0.019267 | 0.017284 | 0.024230 | 0.025107 | 0.025530 | 0.0766 |
| 7 | trigger (n=20) | checkpoint_write | 0.019600 | 0.019137 | 0.026449 | 0.037347 | 0.040581 | 0.0779 |
| 7 | trigger (n=20) | raw_serialization_hash | 0.060782 | 0.053466 | 0.079966 | 0.085759 | 0.090100 | 0.2416 |
| 7 | nontrigger (n=1004) | message_handling | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 7 | nontrigger (n=1004) | y_transform | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 7 | nontrigger (n=1004) | geometry_setup | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 7 | nontrigger (n=1004) | structural_field_build | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 7 | nontrigger (n=1004) | structural_scoring | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 7 | nontrigger (n=1004) | structural_selection_trace | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 7 | nontrigger (n=1004) | structural_refit_refresh | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 7 | nontrigger (n=1004) | structural_fallback_direct | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 7 | nontrigger (n=1004) | local_refinement | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 7 | nontrigger (n=1004) | geometry_finalization | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 7 | nontrigger (n=1004) | geometry_wrapper_overhead | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 7 | nontrigger (n=1004) | wrapper_validation | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 7 | nontrigger (n=1004) | channel_construction | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 7 | nontrigger (n=1004) | tf | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 7 | nontrigger (n=1004) | ldpc | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 7 | nontrigger (n=1004) | checkpoint_write | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |
| 7 | nontrigger (n=1004) | raw_serialization_hash | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |

Per-frame stage values are in stage_times.csv; all 3,072 pairs and 6,144 arm decisions are preserved in frame_outcomes.csv and arm_outcomes.csv.

Observed seal Git commit: `929c679b4797de18271065b8e8bf35b67b6de13f` (2026-09-22T17:59:34+00:00).
Observed seal SHA256: `45d11386e3518389cd6e0d107cd8bee1a44b74115e8b9894a1e90abf0c466253`. The committed observed and truth seal bytes and preregistration blobs were checked with Git in the independent evidence repository before truth payloads were read.

Committed truth seal SHA256: `cb5e737c293848be4206e1480e0d4545869c886d139b655a2867e7c3d2f104d4`.

The 6 and 7 dB comparisons, codeword errors, syndromes, undetected decisions, 0.5 s outcomes, and timing are descriptive. No further parameter search or population claim is inferred from them.
