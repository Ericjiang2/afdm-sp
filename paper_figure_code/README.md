# Paper Figure — Core Code Package

This folder bundles the core source code used to produce every figure that
appears inside the body of `paper/main.pdf` (the FYP report). It is meant as a
self-contained, reviewable snapshot — not a build system. Trained checkpoints,
intermediate JSON results, and feature caches live elsewhere on the project
disk and are referenced via path arguments at the top of each script.

## Figure → script mapping

| # | Figure file (in paper) | Section | Generator script |
|---|---|---|---|
| 1 | `paper/system_block/fig_singleframe_canonical.pdf` | §2 (System Model) | `mechanism_figures/make_fig_singleframe_canonical.py` |
| 2 | `paper/system_block/fig_dirichlet_kernel.pdf` | §2 / §4 (Mechanism) | `mechanism_figures/make_fig_dirichlet_kernel.py` |
| 3 | `figures/system_block/figure_a_new.png` | §2 (Block diagram) | hand-drawn — image asset only, see `system_block_images/figure_a_new.png` |
| 4 | `figures/system_block/figure_b_new.png` | §2 (Block diagram) | hand-drawn — image asset only, see `system_block_images/figure_b_new.png` |
| 5 | `figures/system_block/figure_c_new.png` | §2 (Block diagram) | hand-drawn — image asset only, see `system_block_images/figure_c_new.png` |
| 6 | `figures/loop13/loop13_combined_4B_ber_mse.png` | §4 (Results — main waterfall) | `result_figures/loop13_combined_4B_plot.py` |
| 7 | `figures/loop13/loop13_iter_convergence_4B.png` | §4 (Results — outer-iter convergence) | `result_figures/loop13_iter_convergence_4B_plot.py` |
| 8 | `figures/loop13/loop13_oracle_headroom.png` | §4 (Results — oracle headroom) | `result_figures/loop13_oracle_headroom_plot.py` |
| 9 | `figures/loop13/loop13_support_recall.png` | §4 (Results — support recall probe) | `result_figures/loop13_support_recall_probe.py` |

## Folder layout

```
paper_figure_code/
├── README.md                        ← this file
│
├── result_figures/                  ← Section 4 quantitative result figures
│   ├── _plot_style.py               (shared IEEE-style helper)
│   ├── loop13_combined_4B_plot.py
│   ├── loop13_iter_convergence_4B_plot.py
│   ├── loop13_oracle_headroom_plot.py
│   └── loop13_support_recall_probe.py
│
├── mechanism_figures/               ← Section 2 mechanism / system figures
│   ├── make_fig_singleframe_canonical.py
│   └── make_fig_dirichlet_kernel.py
│
├── system_block_images/             ← Section 2 hand-drawn block diagrams
│   ├── figure_a_new.png             (no generator code — image asset)
│   ├── figure_b_new.png
│   └── figure_c_new.png
│
└── upstream_experiment_code/        ← Code that produced the JSON inputs
    │                                  consumed by result_figures/*.py
    ├── __init__.py
    ├── afdm_env.py                  (AFDM channel / pilot / framing)
    ├── afdm_baselines.py            (LS / OMP / MP / joint OMP+MP — classical)
    ├── afdm_layers.py               (per-iteration unrolled layers)
    ├── afdm_joint_unrolled.py       (legacy learned joint receiver — ablation)
    ├── classical_joint_unrolled.py  (faithful unroll of joint OMP+MP — main)
    ├── afdm_models.py               (model wrappers)
    ├── afdm_trainer.py              (training loop)
    ├── train_classical_joint_unrolled.py   (training entry point — main line)
    ├── train_joint_unrolled.py             (training entry point — legacy)
    ├── eval_classical_joint_unrolled.py    (eval entry point)
    ├── loop13_new_baselines_eval.py        (produces baselines results.json)
    ├── paired_learned_eval.py              (produces paired/learned results.json)
    └── loop13_iter_convergence_probe.py    (produces iter-convergence results.json)
```

## Notes on completeness

- The result-figure plot scripts in `result_figures/` are **post-processors**:
  each reads one or more `results.json` files produced by the upstream code in
  `upstream_experiment_code/`, then renders the figure. The exact JSON paths
  expected are documented in each plot script's header docstring.

- Two upstream probes referenced inside docstrings — `classical_joint_headroom_probe.py`
  (input to `loop13_oracle_headroom_plot.py`) and `loop9_cache_features.py`
  (input to `loop13_support_recall_probe.py`) — live on the remote training
  server and are **not** part of the local working tree, so they are not
  bundled here. Their JSON / cache outputs have been pulled down to the
  project's `afdm_sp_joint_unrolled/outputs_*` directories and are what the
  bundled plot scripts actually consume.

- `system_block_images/figure_{a,b,c}_new.png` are the three block-diagram
  panels in Section 2. They were drawn by hand in a vector editor; no Python /
  MATLAB generator exists for them, so only the rendered images are bundled.

- All Python files are **byte-identical copies** of the source files in
  `afdm_sp_joint_unrolled/` and `paper/figures_mechanism/` at the time this
  package was assembled. Re-run from those original locations for the
  authoritative version.
