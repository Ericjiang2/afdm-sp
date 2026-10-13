# Per-candidate attribution (axis B2)

Operating point: ckpt=`ckpt_c2rel_force_topk.pt`  F2-P(refine=2, topm=96, protect=2)  frames=250  k_leak=2

| SNR (dB) | added/frame | main | sidelobe | virtual | false | side+virt% |
|---|---|---|---|---|---|---|
| 15 | 2.00 | 1 | 316 | 183 | 0 | 99.8% |
| 20 | 2.00 | 3 | 303 | 195 | 0 | 99.4% |
| 25 | 2.00 | 0 | 302 | 196 | 2 | 99.6% |
