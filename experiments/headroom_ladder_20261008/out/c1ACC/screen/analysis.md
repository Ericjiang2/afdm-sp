# Frozen ACC headroom screen

Gate verdict: **KILL**. 1536 registered receiver calls; no load screen.

| Candidate | Joint risk/FER/time cells | Beats both risk controls | Verdict |
|---|---:|---:|---|
| AA2 | 0/6 | 0/6 | KILL |
| AA4 | 1/6 | 0/6 | KILL |
| ADPT | 1/6 | 3/6 | KILL |

One candidate must pass risk/FER/time jointly in >=4 cells AND beat both risk controls jointly in >=4 cells; the two sets need not coincide.

| Cell | Candidate | Risk / BASE40 | FER − BASE40 | Seconds / BASE40 | Joint pass | Beats both |
|---|---|---:|---:|---:|---|---|
| 1 | AA2 | 1.17387 | 0 | 0.943399 | False | False |
| 1 | AA4 | 1.16876 | 0 | 0.938857 | False | False |
| 1 | ADPT | 2.48079 | 0.625 | 0.817687 | False | False |
| 2 | AA2 | 1.22818 | 0.25 | 0.806081 | False | False |
| 2 | AA4 | 1.22928 | 0.25 | 0.806387 | False | False |
| 2 | ADPT | 0.986735 | 0.25 | 0.677268 | False | True |
| 3 | AA2 | 1.01045 | 0.03125 | 0.745759 | False | False |
| 3 | AA4 | 1.01896 | 0.03125 | 0.79104 | False | False |
| 3 | ADPT | 1.07477 | 0.0625 | 0.643194 | False | False |
| 4 | AA2 | 1.06199 | 0.1875 | 0.789057 | False | False |
| 4 | AA4 | 1.06322 | 0.1875 | 0.793814 | False | False |
| 4 | ADPT | 1.16156 | 0.25 | 0.687574 | False | False |
| 5 | AA2 | 1.0058 | 0 | 0.821385 | False | False |
| 5 | AA4 | 1.00591 | 0 | 0.779286 | True | False |
| 5 | ADPT | 0.929414 | 0 | 0.656308 | True | True |
| 6 | AA2 | 1.21822 | 0.375 | 0.854159 | False | False |
| 6 | AA4 | 1.21973 | 0.375 | 0.854249 | False | False |
| 6 | ADPT | 0.880077 | 0.375 | 0.719851 | False | True |

Pooled across six cells (192 frames per arm, descriptive):

| Arm | Risk | FER | Seconds/frame | Maps/frame | Accel overhead/frame |
|---|---:|---:|---:|---:|---:|
| BASE20 | 0.147205 | 0.817708 | 0.458465 | 20 | 0 |
| BASE25 | 0.140723 | 0.796875 | 0.514668 | 25 | 0 |
| BASE30 | 0.136681 | 0.744792 | 0.565177 | 30 | 0 |
| BASE40 | 0.131197 | 0.677083 | 0.686197 | 40 | 0 |
| DAMP20 | 2.04226e+36 | 0.833333 | 0.467366 | 20 | 0 |
| AA2 | 0.146576 | 0.817708 | 0.55849 | 25.8385 | 0.0283078 |
| AA4 | 0.146799 | 0.817708 | 0.558164 | 25.849 | 0.0284695 |
| ADPT | 0.136864 | 0.9375 | 0.470034 | 20 | 0.00250217 |

Integrity: 1536 rows; 0 errors. All 192 observation blocks match archived B; maximum BASE20/40 risk difference 0.

Facts: measured endpoints and frozen cell counts above. No later candidate choice or tuning enters the gate.
Inference: KILL closes this frozen acceleration route; it is not a theorem about every possible accelerator.

- Headroom screen uses the B observations: six cells, 32 frames each, R=1, known support; no independent confirmation.
- Cell point counts decide; pooled endpoints are descriptive.
- Full receiver wall time includes acceleration, rejected maps and cheap h observation; excludes post-call truth scoring.
- Per-step overhead excludes map time; full seconds includes every rejected-trial map.
- Concurrent single-thread wall time on one host; not an isolated CPU process-time benchmark.
- No load screen, Kc inference or hyperparameter retuning.

Finite divergence retained: DAMP20 (.5) has pooled risk 2.0422589113e36; maximum frame risk 3.9198367380e38 at cell 1/frame 26. All risks remain finite. No clipping, winsorization, dropped frame or post-result damping change. Details: finite_divergence.json.

All three candidates fail the FER predicate in at least three cells (AA2/AA4 pass 2/6; ADPT 1/6), so timing-border uncertainty cannot make the registered primary gate pass.
