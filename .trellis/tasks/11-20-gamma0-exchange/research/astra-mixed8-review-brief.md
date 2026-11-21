# Astra brief: design review of the MIXED8 Γ = 0 test (read-only, one pass)

Model `gpt-6.2-astra`, reasoning effort high. Read-only: do not edit files, run receiver simulations or commit; small in-memory
numerical checks are allowed. Working directory: `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`.

## Read
- `experiments/gamma0_mixed8_20261120/PROTOCOL.md` (the draft under review);
- `research-assets/res-20261120-01.md` and `experiments/gamma0_exchange_20261120/PROTOCOL.md` §7 (the P1 leg, frozen and run);
- `research-assets/res-20261119-04.md`, `experiments/doublet_conflict_20261119/PROTOCOL.md` and `mixed8_receiver.py`;
- `research-assets/res-20261118-02.md` (MIXED8 family, A2g).

## Questions (answer each; be concrete; "no change" where none is needed)
1. Single factor and null arm: does Z differ from CD only in the geometry-stage variance? Is the removal arm plus the simplest
   baselines (F0, H) adequate for crediting or discrediting Γ here? Anything missing?
2. Endpoints: are P-F (FER, ±1.5 pp) and P-D (0.35-bin two-atom rate, ±3 pp) the right primaries, with 600 single-key frames? What
   half-widths do you expect given res-19-04's discordance (14 frames for U vs CD)? Is the singleton-phantom definition sound when true
   co-delay pairs exist?
3. Hypotheses: do H-SC, H-ridge, H-overfit, H-scale predict distinct outcomes? Derive the direction of the 0.35-bin two-atom rate for Z
   versus CD from the difference-mode penalties (Z: λ only; CD: u(1 − |D_N|) + λ; U: adds u on Π_lo) and say whether H-ridge's
   "λ/E versus λ/N" argument holds.
4. Anchors (CD FER in [3%, 9%], S at least 10 pp above CD): sound given res-19-04 (CD 5.5%, A2 30.5%)?
5. Premortem: the most likely way this misleads, and whether the gates catch it.
6. Your own probabilities: P-F categories; P-D categories.

## Output
Final message only, English, ≤ 50 lines, numbered by question, each change marked REQUIRED or SUGGESTED.
