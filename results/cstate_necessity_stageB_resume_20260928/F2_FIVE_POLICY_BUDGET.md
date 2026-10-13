# Five-policy operational budget

One full1024-observation developmental pass;2168 actual calls maximum (2048 prefixes plus120 F0-triggered continuations),5120 logical outcomes. The previous failed19 calls remain separately charged, giving at most2187 calls across the two population attempts. Prior diagnostics/qualification and the completed F1 experiment retain their separate historical counts. Do not reuse or silently exclude any prior failed cost.

Unchanged per-call operational caps: F0/F2E/F2T120s; B/F0_LOCAL900s. Total campaign cap259200s (72h) after preflight; launcher259500s (72h5min) including preflight/cleanup. These are failure-stop ceilings, not estimator iterations or runtime promises. Each failed call remains in the attempt/failure journals. Do not restart automatically.

The first five observed F0 prefixes averaged0.332538s and F2E prefixes15.794807s. Extrapolated full-prefix cost is4.5873h;40 prior-qualified F2T continuations at16.6105s add0.1846h, before the80 matched B/LOCAL continuations and overhead. Thus roughly5h is a capacity estimate, with substantial uncertainty, not a performance finding. No truth was used for this estimate.

Run one numerical process on CPU64 with BLAS/OMP/Torch threads1 and CUDA hidden. All new files/cache/tmp remain under the project in `/data/guoyikun`. Check process ownership and available storage before dispatch. Existing raw and failed-attempt outputs remain untouched; new roots are `population_five_v1`, `population_five_launch_v1`, and `population_five_dispatch_v1`. The prior5.53TB free-space check is historical; use a fresh read-only check at launch. Retrieve small metadata and full-path/hash inventories locally; large raw stays remote.

Memory accounting is the existing per-paid-call Linux process high-water RSS plus the maximum over the complete campaign. It captures the full155-slot downstream receiver and retained shared state; it is not an isolated-arm allocation benchmark. No receiver truncation, extra sampling thread or independent rerun is authorized for memory attribution.
