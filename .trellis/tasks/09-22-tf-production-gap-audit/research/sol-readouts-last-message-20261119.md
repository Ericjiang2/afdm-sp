Commit `023ccadb36440b58128a86b1e4fbfe169b0a4ae5`. `model: gpt-6.2-sol`. New frames 0.  
Exact parity on 7,714 F0 records, 7,667 first-exchange records and 1,000 APP E/u records. Maximum relative Γ error `7.07e-16` over 28,000 pairs.

| R1 arm | Median G_P/λ | AUC (T vs P, P vs F), normalized / gross | Smallest c | P(G_T > cλ) |
|---|---:|---|---:|---:|
| A2 scalar | 117.394 | (0.01367, 0.96856) / (0.01140, 0.95078) | 210.374 | 0.0130% |
| A1c CODELAY | 8.201 | (0.58918, 0.08744) / (0.60156, 0.09583) | 75.128 | 2.0217% |

R1 had 7,667 triggered units. The 1,417 empty true-delay classes per arm contributed zero reward.  
R2 sampled 1,000 of 8,102 failed units. Median and p95 were **0.05624 / 0.11217** for max_d |v̂[d]|/u and **0.01543 / 0.06152** for the per-unit AFDM/OFDM ratio.  
CPU use was 1.018231 core-hours for the completed run, plus ≤0.041 for startup and diagnosis. [Summary](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/zero_sim_readouts_20261119/out/summary.json) · [README](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/zero_sim_readouts_20261119/README.md)