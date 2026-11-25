# Implementation and verification

1. Freeze `PREDICTIONS.md` in Git before any experiment or executable
   qualification. Verify the selected inputs, frame schedule, decisions, and
   cost-stop contract against the design and producing C1 source.
2. Keep the irregular PEG constructor, driver, and reader in
   `experiments/matched_ldpc_20261122/`. Use the frozen E1 LDPC helpers so
   the historical decoder file keeps its recorded digest. Validate degrees, rank,
   girth, parity of encoded words, and all-bit recovery on strong noiseless
   likelihoods. Use the C1 T1 white-noise reference to qualify the unchanged
   regular decoder path before fresh channel generation.
3. Bind the actual imported receiver and decoder to the historical C1 sources
   before calling the receiver. Reproduce a historical key through the frozen
   `FULL_R10` path and the experiment interface. Compare its hard decisions
   and round checkpoints where recorded. Run a disjoint three-arm smoke to
   catch skipped refits, rate differences, mismatched observations, or failed
   rows. Measure CPU rather than multiplying concurrent wall timings. Check
   the crossing/analysis path with a known gain and censored curves.
4. After checking CPU load, run one server chain under `/data/guoyikun/`, using
   a `g_` tmux session and single-thread workers. Use the frozen schedule and
   account for qualification, measurement, and analysis in the shared 20
   CPU core-hour budget. Enforce a process CPU limit across the controller and
   workers, leave time to save measured CPU use, and stop before a wave whose
   projected completion exceeds the remaining allocation. Emit DONE or STOPPED
   and retain completed cells and any explicitly partial rows.
5. Verify unique keys and complete pairing before deriving the results. Return
   the small `results.json` and status log, record raw paths with MD5, apply the
   frozen verdict and score any resolved prediction. Update the funnel card,
   `STATE.md`, and task with the outcome and evidence location. Commit only
   task files and keep large outputs on deinlab.
