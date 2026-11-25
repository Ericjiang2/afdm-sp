You are simulating a hostile senior reviewer for a candidate research contribution (an idea card that passed a cheap L2 simulation). This is a kill-argument adversarial check: do NOT give a balanced review. Construct the single strongest argument for rejecting it.

Files to read (absolute paths; read-only):
- Card: /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-g01.md
- Pre-registration: /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_g_r11_g01.md
- L2 script: /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/g_l2_r11_g01.py
- L2 summary: /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/summary_g_r11_g01.json
- Funnel rules the card was judged under (group [放宽TWC], rival rule, red lines): /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/FUNNEL.md and /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/prompts/round-agy-extra.md
You may search the literature (MIMO-AFDM embedded-pilot channel estimation, Yin et al. TWC 2024, pulse-shaped / continuous-time AFDM, OTFS/OFDM interference whitening, multi-user near-far pilot contamination, SAGE).

Axes (pick the most damaging combination): rival weakness (are Yin24 EPA-DR, Fleury SAGE and MatchedDir given the same knowledge the proposed receiver uses, e.g. exact pulse taps, interference covariance, guard window, iterations? would a sane engineer simply widen the guard or whiten the rival too?); a self-designed operating point (K_strong*P > N_bs, +16 dB near-far, RRC roll-off, guard layout) chosen so that rivals floor; gains of 26x-57x that look too large to be a fair comparison; truth or side-information leakage in the script; whether the difficulty is AFDM-specific or is just generic pulse-shaping leakage that OFDM/OTFS share; claim-vs-evidence gap and prior art.

Constraints: about 200 words (max 250), one coherent argument, cite file:line or JSON keys when accusing, no hedging, no acknowledgement of mitigations. Output only the rejection memo, in English.
