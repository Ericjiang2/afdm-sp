# Model Checkpoint Manifest

**Purpose**: track every `.pt` checkpoint that paper sections, figures, or tables actually depend on, plus where to fetch it. Keeps `.pt` files out of git history (gitignore line 11) while still letting reviewers reproduce results from a single download URL cited in the paper.

**Status**: skeleton. SHA256 + DOI fields are placeholders until the TCOM-submission-r1 reproduction bundle is published to Zenodo / HuggingFace.

---

## Checkpoint registry

| ID | Filename (canonical local path) | Used by | Training script | Status |
|---|---|---|---|---|
| `c2rel-force-topk-loop9` | `afdm_sp_joint_unrolled/outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt` | §3 Table 3 3-seed pooled rows; §3 Table 2 / Fig 3 iter-conv; §3 oracle-headroom decomposition; §3 support-recall; §4 mechanism discussion | `train_classical_joint_unrolled.py` with C2-rel feature set + force-topk bias patch, 8 epochs, AdamW lr 1e-3, BCE + pairwise rank-hinge | live on remote `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_loop9_c2rel_train/` |
| `c2rel-retrain27k-snr25-loop13` | `afdm_sp_joint_unrolled/outputs_loop13_4B_train_27k_with_snr25/ckpt_c2rel_force_topk.pt` | §3 Table 3 single-seed 400-frame illustrative row (seed 20260425) | same recipe as loop9 but trained on 27k-frame 4-SNR cache including SNR=25 dB | live on remote `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_loop13_4B_train_27k_with_snr25/` |

**Reserved IDs** (not yet trained — populated as TCOM feature branches land):

| ID | Will exist after | Notes |
|---|---|---|
| `listwise-seedN` (N ∈ {0..4}) | `trans/listwise-mechanism` branch | 5-seed listwise top-K loss retrain; each seed independently trained on the same 27k-frame cache |
| `qing-sp-afdm-best` | `trans/qing-baseline` branch | Reproduced Qing 2024 SP-AFDM receiver (no learned head; included only to sanity-check the reproduction matches Qing's published BER curves) |

---

## Per-checkpoint detail

### `c2rel-force-topk-loop9`

- **SHA256**: `TBD` (compute via `shasum -a 256 ckpt_c2rel_force_topk.pt` after pulling the file)
- **Size**: TBD MB
- **Zenodo DOI**: `TBD` (will resolve to `https://doi.org/10.5281/zenodo.<id>`)
- **HuggingFace mirror**: `TBD`
- **Training command** (exact, from `outputs_loop9_c2rel_train/run.log`):
  ```bash
  python afdm_sp_joint_unrolled/train_classical_joint_unrolled.py \
      --variant C2-rel --feature-set c2rel \
      --cache afdm_sp_joint_unrolled/outputs_loop9_c2rel_cache \
      --epochs 8 --lr 1e-3 --batch-size 64 --optimizer adamw \
      --loss bce_rank_hinge --rank-hinge-weight 0.1 \
      --force-topk --seed 20260418 \
      --out afdm_sp_joint_unrolled/outputs_loop9_c2rel_train/
  ```
- **Cross-references**: `REPRODUCTION.md` §3 Table 3 pooled rows; §3 iter-conv; §3 oracle-headroom; §3 support-recall.

### `c2rel-retrain27k-snr25-loop13`

- **SHA256**: TBD
- **Size**: TBD MB
- **Zenodo DOI**: TBD
- **HuggingFace mirror**: TBD
- **Training command**: same as `c2rel-force-topk-loop9` but cache includes SNR=25 dB samples and longer trajectory (27k frames × 4 SNRs).
- **Cross-references**: `REPRODUCTION.md` §3 Table 3 single-seed 400-frame row.

---

## How to fetch

When the TCOM-submission-r1 bundle is published, replace the `TBD` lines above and add a one-line fetch script per checkpoint:

```bash
# Example (placeholder)
mkdir -p afdm_sp_joint_unrolled/outputs_loop9_c2rel_train
curl -L https://zenodo.org/record/<id>/files/ckpt_c2rel_force_topk.pt \
     -o afdm_sp_joint_unrolled/outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt
shasum -a 256 -c <(echo "<sha256>  afdm_sp_joint_unrolled/outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt")
```

For now the only way to obtain these `.pt` files is via SSH access to `deinlab` (`/data/guoyikun/00inbox/AFDM-channel-estimation/...`).

---

## Why this file lives here

The project-level `.gitignore` (line 11) blocks all `*.pt` from ever entering git history. That keeps the repo small, but means a reviewer who clones the repo gets the code without the trained models and can't reproduce numerical results. This manifest is the bridge: it documents which checkpoints are load-bearing for the paper, where to download them, and how to verify integrity (SHA256). It is checked into git and should be updated whenever a new paper-cited checkpoint is added or a download URL changes.
