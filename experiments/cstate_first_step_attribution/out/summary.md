# P1 first-step attribution

251 frozen triggers across 107 physical frames. The population is retrospective.

## Frozen majority rule

**Supports majority**. N=240, L=155, B=7, unresolved=78. Supported events among all triggers: 155/251.

The 10,000-draw physical-frame bootstrap uses seed 71626.

Attribution bounds [0.645833, 0.970833].

Lower bound 95% interval [0.563559, 0.723320]. Upper bound 95% interval [0.947598, 0.990869].

## Cumulative funnel

| Criterion | Units |
| --- | --- |
| D_raw repeated-delay additions | 240 |
| Valid anchor | 240 |
| Nonempty W | 235 |
| Decisive fixed D/C reversal in raw and clean | 232 |
| Matching same-slot reversal in raw and clean | 231 |
| Decisive global actions meeting L | 155 |

Across all valid anchors, 155 met the global action condition. Weaker-w subset: 235 paired units, 155 supported and 7 contradicted.

### Clean cells unavailable

| Reason | Units |
| --- | --- |
| D_raw_no_repeat | 11 |

### Contradiction flags and overlaps

| Flags present | Units |
| --- | --- |
| D_clean_repeat_disappears | 7 |

### Individual contradiction flags

| Flag | Units |
| --- | --- |
| D_clean_repeat_disappears | 7 |

### Unresolved reasons

| Reason | Units |
| --- | --- |
| C_clean_no_net_truth_neighbour_recovery | 75 |
| C_raw_no_net_truth_neighbour_recovery | 77 |
| F_clean_no_net_truth_neighbour_recovery | 75 |
| F_raw_no_net_truth_neighbour_recovery | 77 |
| clean_same_slot_no_required_reversal | 1 |
| no_legal_entering_missing_truth_neighbour | 5 |

### Decisive local fixed-pair predictions in the reverse direction

| State | Units |
| --- | --- |
| — | 0 |

### D/C by state, anchor-repeat patterns

| Pattern | Confidence | D_raw/C_raw/D_clean/C_clean | Units |
| --- | --- | --- | --- |
| block_sensitive | decisive | 1010 | 233 |
| joint_only | decisive | 1000 | 7 |

## Fixed-pair and same-slot transitions

### fixed, D_raw to D_clean

| D_raw | D_clean | Units |
| --- | --- | --- |
| repeat | W | 3 |
| repeat | repeat | 232 |

### same_slot, D_raw to D_clean

| D_raw | D_clean | Units |
| --- | --- | --- |
| repeat | W | 2 |
| repeat | repeat | 233 |

### fixed, C_raw to C_clean

| C_raw | C_clean | Units |
| --- | --- | --- |
| W | W | 235 |

### same_slot, C_raw to C_clean

| C_raw | C_clean | Units |
| --- | --- | --- |
| W | W | 234 |
| W | repeat | 1 |

### fixed, F_raw to F_clean

| F_raw | F_clean | Units |
| --- | --- | --- |
| W | W | 235 |

### same_slot, F_raw to F_clean

| F_raw | F_clean | Units |
| --- | --- | --- |
| W | W | 234 |
| W | repeat | 1 |

### fixed, D_raw / C_raw / F_raw

| D_raw | C_raw | F_raw | Units |
| --- | --- | --- | --- |
| repeat | W | W | 235 |

### same_slot, D_raw / C_raw / F_raw

| D_raw | C_raw | F_raw | Units |
| --- | --- | --- | --- |
| repeat | W | W | 235 |

### fixed, D_clean / C_clean / F_clean

| D_clean | C_clean | F_clean | Units |
| --- | --- | --- | --- |
| W | W | W | 3 |
| repeat | W | W | 232 |

### same_slot, D_clean / C_clean / F_clean

| D_clean | C_clean | F_clean | Units |
| --- | --- | --- | --- |
| W | W | W | 2 |
| repeat | W | W | 232 |
| repeat | repeat | repeat | 1 |

### Block budget outcomes

| State | Outcome | Units |
| --- | --- | --- |
| clean | D_prefers_W | 3 |
| clean | actual_reversal | 232 |
| raw | actual_reversal | 235 |

### D_raw, same-slot candidate changes from fixed IDs

| Repeat changed | W changed | Units |
| --- | --- | --- |
| False | False | 235 |

### C_raw, same-slot candidate changes from fixed IDs

| Repeat changed | W changed | Units |
| --- | --- | --- |
| False | False | 6 |
| True | False | 229 |

### F_raw, same-slot candidate changes from fixed IDs

| Repeat changed | W changed | Units |
| --- | --- | --- |
| False | False | 6 |
| True | False | 229 |

### D_clean, same-slot candidate changes from fixed IDs

| Repeat changed | W changed | Units |
| --- | --- | --- |
| False | False | 212 |
| True | False | 22 |
| True | True | 1 |

### C_clean, same-slot candidate changes from fixed IDs

| Repeat changed | W changed | Units |
| --- | --- | --- |
| False | False | 12 |
| True | False | 222 |
| True | True | 1 |

### F_clean, same-slot candidate changes from fixed IDs

| Repeat changed | W changed | Units |
| --- | --- | --- |
| False | False | 12 |
| True | False | 222 |
| True | True | 1 |

### Margins and signed decomposition in objective units

| Term | Min | Median | Max |
| --- | --- | --- | --- |
| m_D | 0.39771854 | 22.135631 | 77.459049 |
| U | 1.3804828 | 26.705898 | 81.324613 |
| R | -1.7103635 | -0.02741637 | 2.037219 |
| I | -4.4056297 | 3.4774742e-05 | 7.7713412 |
| F-C raw | -0.013596308 | -9.3588639e-05 | 0.035626868 |
| F-C clean | -0.013621652 | -0.00010516671 | 0.03498469 |

## All-slot source actions

Raw tables include all 251 keys. Clean tables include explicit NA cells.

### D_raw / C_raw / F_raw

| D_raw | C_raw | F_raw | Units |
| --- | --- | --- | --- |
| new_true_neighbour_net_gain | new_true_neighbour_net_gain | new_true_neighbour_net_gain | 8 |
| new_true_other_doppler | new_true_other_doppler | new_true_other_doppler | 1 |
| none | none | none | 1 |
| repeat_anchor_true | new_false_delay | new_false_delay | 3 |
| repeat_anchor_true | new_true_neighbour_net_gain | new_true_neighbour_net_gain | 160 |
| repeat_anchor_true | new_true_neighbour_trade | new_true_neighbour_trade | 3 |
| repeat_anchor_true | new_true_other_doppler | new_true_other_doppler | 57 |
| repeat_anchor_true | repeat_other_true | repeat_other_true | 5 |
| repeat_anchor_true | same_delay_relocation | same_delay_relocation | 12 |
| same_delay_relocation | same_delay_relocation | same_delay_relocation | 1 |

### D_clean / C_clean / F_clean

| D_clean | C_clean | F_clean | Units |
| --- | --- | --- | --- |
| NA | NA | NA | 11 |
| new_true_neighbour_net_gain | new_true_neighbour_net_gain | new_true_neighbour_net_gain | 2 |
| repeat_anchor_true | new_false_delay | new_false_delay | 3 |
| repeat_anchor_true | new_true_neighbour_net_gain | new_true_neighbour_net_gain | 158 |
| repeat_anchor_true | new_true_neighbour_trade | new_true_neighbour_trade | 3 |
| repeat_anchor_true | new_true_other_doppler | new_true_other_doppler | 53 |
| repeat_anchor_true | repeat_other_true | repeat_other_true | 5 |
| repeat_anchor_true | same_delay_relocation | same_delay_relocation | 11 |
| repeat_other_true | new_true_neighbour_net_gain | new_true_neighbour_net_gain | 2 |
| repeat_other_true | new_true_other_doppler | new_true_other_doppler | 2 |
| repeat_other_true | same_delay_relocation | same_delay_relocation | 1 |

### D_raw to D_clean

| D_raw | D_clean | Units |
| --- | --- | --- |
| new_true_neighbour_net_gain | NA | 8 |
| new_true_other_doppler | NA | 1 |
| none | NA | 1 |
| repeat_anchor_true | new_true_neighbour_net_gain | 2 |
| repeat_anchor_true | repeat_anchor_true | 233 |
| repeat_anchor_true | repeat_other_true | 5 |
| same_delay_relocation | NA | 1 |

### C_raw to C_clean

| C_raw | C_clean | Units |
| --- | --- | --- |
| new_false_delay | new_false_delay | 3 |
| new_true_neighbour_net_gain | NA | 8 |
| new_true_neighbour_net_gain | new_true_neighbour_net_gain | 159 |
| new_true_neighbour_net_gain | new_true_other_doppler | 1 |
| new_true_neighbour_trade | new_true_neighbour_trade | 3 |
| new_true_other_doppler | NA | 1 |
| new_true_other_doppler | new_true_neighbour_net_gain | 3 |
| new_true_other_doppler | new_true_other_doppler | 54 |
| none | NA | 1 |
| repeat_other_true | repeat_other_true | 5 |
| same_delay_relocation | NA | 1 |
| same_delay_relocation | same_delay_relocation | 12 |

### F_raw to F_clean

| F_raw | F_clean | Units |
| --- | --- | --- |
| new_false_delay | new_false_delay | 3 |
| new_true_neighbour_net_gain | NA | 8 |
| new_true_neighbour_net_gain | new_true_neighbour_net_gain | 159 |
| new_true_neighbour_net_gain | new_true_other_doppler | 1 |
| new_true_neighbour_trade | new_true_neighbour_trade | 3 |
| new_true_other_doppler | NA | 1 |
| new_true_other_doppler | new_true_neighbour_net_gain | 3 |
| new_true_other_doppler | new_true_other_doppler | 54 |
| none | NA | 1 |
| repeat_other_true | repeat_other_true | 5 |
| same_delay_relocation | NA | 1 |
| same_delay_relocation | same_delay_relocation | 12 |

| Cell | Available | No edit | Exact candidate ties | Near candidate ties | Ambiguous action | Direct fallback |
| --- | --- | --- | --- | --- | --- | --- |
| D_raw | 251 | 1 | 0 | 0 | 0 | 0 |
| C_raw | 251 | 1 | 0 | 0 | 0 | 0 |
| F_raw | 251 | 1 | 0 | 0 | 0 | 0 |
| D_clean | 240 | 0 | 0 | 0 | 0 | 0 |
| C_clean | 240 | 0 | 0 | 0 | 0 | 0 |
| F_clean | 240 | 0 | 0 | 0 | 0 | 0 |

## Integrity gates

Max fraction is the largest discrepancy divided by its permitted tolerance. Identities are evaluated on every row where their operands are defined.

The noiseless gate subtracts the physical noise at the unit’s SNR. The frozen frame stores the unit noise draw, so the gate multiplies it by `sqrt(raw["sigma2"])` before the observation normalization.

| Gate | Checks | Max absolute discrepancy | Max fraction |
| --- | --- | --- | --- |
| 251 unique keys and 107 physical frames | 1 | 0 | 0 |
| Bfit imaginary part | 480 | 4.7961634663806763e-14 | 4.7887408610536454e-06 |
| Bfit nonnegative | 480 | 0 | 0 |
| D/C S direct score | 480 | 2.2737367544323206e-13 | 7.7055420399475028e-07 |
| D/C S normal matrix | 480 | 2.7847474288855413e-13 | 1.434531863672217e-07 |
| D/C w direct score | 470 | 2.2737367544323206e-13 | 7.7498689930497083e-07 |
| D/C w normal matrix | 470 | 3.0078709995275298e-13 | 1.4375580971314462e-07 |
| D/C w production score | 470 | 2.2737367544323206e-13 | 7.074431737608914e-07 |
| F0 syndrome and decoded hash | 251 | 0 | 0 |
| K = A - Bfit | 480 | 3.836930773104541e-13 | 1.1679108236087113e-05 |
| K = M_D - M_C | 470 | 2.2737367544323206e-13 | 1.0022566362010685e-05 |
| M = G_c - G_w | 1410 | 3.9968028886505635e-13 | 2.8784574808974528e-05 |
| M1 - M0 = Pc - Pw + Xc - Xw | 705 | 1.0644540804349845e-12 | 0.00010308868002651534 |
| M_D1 = M_C0 + U + R + I | 235 | 0 | 0 |
| clean Schur gain | 1425 | 5.804801084252631e-13 | 5.9313848975331739e-05 |
| direct vs production grid | 5419 | 1.0345502232667059e-11 | 2.7536435866778954e-05 |
| eight entering paths | 251 | 0 | 0 |
| frozen sources | 1 | 0 | 0 |
| gain change = P + X | 1425 | 7.7471362658343423e-13 | 7.6021930913296518e-05 |
| noiseless truth relative error | 251 | 7.9037315436751527e-16 | 7.903731543675153e-05 |
| output keys match frozen population | 1 | 0 | 0 |
| positive Schur complement | 1425 | 0 | 0 |
| profile objective | 6859 | 0 | 0 |
| projection orthogonality | 240 | 2.0624035849423238e-12 | 0.00019372463443096495 |
| raw Schur gain | 1425 | 4.5350875832461668e-13 | 4.4124239038599583e-05 |
| shared delays | 1222 | 0 | 0 |
| shared dopplers | 1222 | 0 | 0 |
| shared valid | 1222 | 0 | 0 |
| source accepted direct objective | 1470 | 2.2737367544323206e-13 | 7.9876074659112851e-07 |
| source accepted is source selected | 1473 | 0 | 0 |
| source candidate in bank | 3193 | 0 | 0 |
| source candidate legal | 3193 | 0 | 0 |
| step-zero entering support | 1473 | 0 | 0 |
| unchanged total variance | 251 | 5.6843418860808015e-14 | 4.9745148589221695e-07 |
| z1 = z0 + delta | 1425 | 1.3694935241656982e-12 | 0.00014790140555078648 |
