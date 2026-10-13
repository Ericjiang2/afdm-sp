# Pfixed development results

All192 independent blocks ×3 pilots ×3 SNR values were completed and audited from original terminal arrays. Each contrast uses paired blocks; SNR records are not pooled as independent samples. Receiver B0-p2-s0.5 and pilot designs remain frozen.

| SNR dB | p0 errors /192 | p1 errors /192 | p2 errors /192 |
|---|---:|---:|---:|
| 7 | 135 | 143 | 148 |
| 8 | 17 | 23 | 30 |
| 9 | 1 | 2 | 1 |

All1728 power records passed the declared simulation gate. This is not hardware amplifier validation. No per-frame pilot+data normalization or power-failure filtering was applied.

The p1 dictionary-coherence optimization did not produce a positive observed FER reduction against p0 in this fixed-receiver development study. At8dB the paired p1-minus-p0 benefit is -3.125 percentage points; the conservative simultaneous interval for FER_p0-FER_p1 is [-16.75,10.81] percentage points. This wide interval supports neither practical-benefit exclusion nor equivalence.

Pmatched remains necessary: its equal receiver-tuning budget is a distinct protocol, and the original-pilot receiver configuration is held fixed in Pfixed. No conclusion about the best attainable pilot/receiver combination follows from these fixed-configuration point estimates. Both protocols keep all three pilot contrasts for independent confirmation.

Evidence: pilot-development-audit-partial-v2.json binds the raw audit; pilot-fixed-development-statistics-v1.json contains all9 paired W/L counts and intervals. Concurrent complete-F timing is retained but does not satisfy formal COST-02.
