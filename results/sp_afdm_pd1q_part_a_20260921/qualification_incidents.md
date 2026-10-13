# Qualification harness incidents

- Initial frozen harness `85365dd0` stopped at N256/P8, iteration0: `competent_4fft: iteration 0 s differs`. Full stderr and process receipt retained in `launch_kernel_failed/`. No receiver campaign call occurred before this gate.
- Minimal reproduction is the first deterministic fixture in that harness (same recorded fixture seed). AF-domain and time-domain residuals were compared without their unitary coordinate conversion. The observation returned by `Channel.apply` is already AF-domain; both implementations correctly receive the same observation.
- `9bc0554f` changes comparison only: IDAFT maps AF/dense residual s into the tensor-free time coordinate. Other states, LLRs, fixture input, tolerance and timed functions are unchanged. Corrected six-case runtime receipt is `kernel_v2/`; the numerical receiver remains `2d130b4d`. This is a qualification-harness defect, not evidence of a receiver numerical defect.
- Before receiver execution, static inspection found plan missing `handoff_sha256`, although producers required it. `a52630af` binds the actual hash from the frozen E1 manifest; `765934d3` records that identity explicitly in the isolated-memory manifest. No numerical parameter or receiver source changed.

Part B remains unstarted. Failed qualification/setup work is retained separately from scientific receiver attempts.

## Packed-truth scoring failure after three primary replays

The three primary replay calls saved six checkpoints and passed receiver parity before the final evidence verifier stopped with `coded error recount differs`. The new scoring wrapper compared decoded arrays directly with E1 packed-bit dictionaries instead of unpacking their payload. This affects newly produced error counts, not the frozen receiver outputs. Execution paused. Original attempts/ledger and launch receipt are preserved; corrected counts must be derived offline from those six checkpoints under an explicitly linked evidence identity. These three calls remain charged; no replay repetition is authorized for this repair. The isolated-memory scoring path requires the same unpacking correction before launch.

Repair outcome: `d1fd9d4f` fixes unpacking at both scoring boundaries and supplies a bounded offline migration. The six saved checkpoints pass the existing verifier and E1 decoded/LLR/path parity under the linked new identity (`receiver_calls_added=0`). Subsequent attribution completed 91 total paid calls / 182 checkpoints, including the same original three replays. The original incorrectly scored run remains excluded from scientific counts and retained as a failure receipt. No primary receiver defect or tuning change was introduced.
