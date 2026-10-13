# legacy_for_ablation

Per the project CLAUDE.md, these older alt-direction modules are kept for
ablation/comparison in journal-extension work. They are NOT the final-result
code line — that lives in `../afdm_sp_joint_unrolled/`. Imports from outside
this folder should NOT depend on anything inside it.

## Contents

### `afdm_joint_param_unrolled/`
Older "joint parameter learning" receiver — the deprecated learned-MP
variant. Per CLAUDE.md: not a faithful unrolled version of the classical
joint OMP+MP baseline (its MP step is a learned `nn.Linear`, support proposal
is learned logits), and at high SNR it falls below the classical teacher.
Kept here for ablation tables that need to contrast "learned-MP" vs the
faithful unrolled `classical_joint_unrolled` backbone.

### `afdm_sp_refactored/`
Earlier "SP refactor" direction (TurboRefiner / OAMPNet / DeepTurbo phase
work; see the Chinese-titled `实现方案_阶段{二,三,四}` and
`研究日志_阶段一` notes inside). Code only — the bulky `outputs_n512/`
checkpoint folder (707 MB) was staged for deletion (it is reproducible from
this code if needed). Kept for code-reference when reviving any of the older
detector branches.
