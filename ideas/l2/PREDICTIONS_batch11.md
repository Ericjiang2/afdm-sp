# L2 batch 11: decision rule and prediction (written 2026-11-21 18:0x, before running; runner l, Claude Fable 5.2)
l09 stage 1, both halves, with the time-domain channel built explicitly (ideas/l2/l2_l09_cluster.py; U scenario, frames 41000-41059, perfect channel knowledge)
- Why a second run: in l2_l09_basis.py the "single carrier" basis was obtained through physical.daft; equal thresholds would also come out for any other
  spreading basis, so that run does not prove the basis was the time basis. Here A = diag(l2) F diag(l1) / sqrt(N) is written out and gated:
  G1: || A H_t A^H - H_frame || / || H_frame || < 1e-9 on every P1 frame, H_t built from the paths (delay shift, CPP factor, Doppler ramp).
- Channels: (a) P1 frame as generated; (b) cluster: same delays and per-path powers, each path split into 4 equal-power rays with random phases and
  Doppler 2 cos(theta) bins, theta ~ U[0, 2 pi) (my construction, not the project's Jakes-4 generator).
- Quantities: per-symbol soft-cancellation LMMSE SINR in the bases AFDM / single carrier / OFDM on a grid of prior variances v, bit information by the J function;
  (i) threshold_v1: SNR where the frame-mean information at v = 1 reaches .57; (ii) tunnel threshold: lowest SNR at which the (3,6) code's EXIT tunnel opens
  (model and merged schedule of l2_exit_tunnel.py; v from the decoder extrinsic information by Gauss-Hermite quadrature of 1 - E tanh^2(L/2)).
- Rule (the card's numbers, fixed; the verdict uses the tunnel threshold): claim (i) holds if |AFDM - SC| <= 0.15 dB on P1; claim (iii) holds if AFDM is better
  than SC by >= 0.5 dB on the cluster channel. If (iii) fails the card's phase diagram is not supported at this ray spread.
- Predictions: G1 passes and (i) holds — .90; (iii) holds (>= 0.5 dB) — .35; AFDM better than SC on the cluster by some margin > 0.1 dB — .75;
  OFDM tunnel threshold worse than AFDM on P1 by >= 0.3 dB — .70.
