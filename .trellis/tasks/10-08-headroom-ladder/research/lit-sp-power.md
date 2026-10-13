# lit-sp-power (2026-10-08)

Legend: [AB] abstract/landing page opened via WebFetch. [FT] HTML full text opened via WebFetch (extractor output, not manual read). [SN] search snippet only; page binary / 403 / empty. Author lists tagged [SN] come from search output, not checked against page. All URLs below were opened or appeared in search results.

## Q1. AFDM superimposed pilot (SP): power ratio, fractional Doppler, iterative SP

1. Zheng, Wen, Mao, Xiao, Wang. 2024. arXiv. "Channel Estimation for AFDM With Superimposed Pilots". https://arxiv.org/abs/2404.10232
   Rel: DAFT-domain SP; pilot placement minimizing CE error; iterative CE+detection. No power ratio in abstract. Integer vs fractional Doppler not stated. [AB]
2. Cao, Wen, Huang. 2024. ICCT 2024 pp.1540-1544, DOI 10.1109/ICCT62411.2024.10946599. "Sparse Channel Estimation and Data Detection for AFDM With Superimposed Pilot Scheme". https://ieeexplore.ieee.org/document/10946599/
   Rel: OMP sparse recovery; alternates CE and detection. Power split not visible. [SN]
3. Authors not captured. 2026. arXiv 2607.18881. "Data-aided Channel Estimation and Sensing With Sparse Bayesian Learning for AFDM-ISAC System". https://arxiv.org/abs/2607.18881
   Rel: detected data reused as pseudo-pilots, grid-evolution SBL. Known only via third-party summary; check original. [SN]
4. Authors not captured. 2022. arXiv 2206.12822. "Diagonally Reconstructed Channel Estimation for MIMO-AFDM with Inter-Doppler Interference in Doubly Selective Channels". https://arxiv.org/abs/2206.12822
   Rel: fractional Doppler causes inter-Doppler interference in embedded-pilot (EP) AFDM. EP, not SP. No power optimization. [SN]

Q1 verdict: no AFDM SP paper optimizing pilot-to-data power ratio found. No AFDM SP paper under continuous fractional Doppler found. Fractional-Doppler AFDM CE found only for EP.

## Q2. OTFS / OFDM superimposed pilots (scaling of pilot fraction)

1. Mishra, Singh, Prasad, Budhiraja. arXiv 2020; IEEE TWC 21(4):2258-2274 (2022, journal per search output [SN]). "OTFS Channel Estimation and Data Detection Designs With Superimposed Pilots". https://arxiv.org/abs/2010.15066 ; full HTML https://arxiv.org/html/2010.15066v1
   Rel: only explicit closed-form pilot-power optimum found. Objective = maximize SINR lower bound (not MSE; paper states optimum does not minimize MSE). sigma_p,opt^2 = root of quadratic (Eq. 71), sigma_d^2 = 1 - sigma_p^2. Parameters: SNR, Q, sigma_h^2, M, N (MN), B_h,NI. Table III (Q=5, M=N=16): sigma_p^2 = 0.302 (0 dB) to 0.360 (20 dB), i.e. pilot fraction rises with SNR. No sweep vs Q, M, N. No N/P scaling law. [FT]
2. Huang, Guo, Zhang, Zakharov. 2024. IEEE TVT (early access); arXiv 2309.08177 v2. "Message Passing-Based Joint Channel Estimation and Signal Detection for OTFS with Superimposed Pilots". https://arxiv.org/abs/2309.08177
   Rel: SP in DD domain; iterative MP receiver; GCE-BEM channel. Pilot designed with power concentrated in frequency domain (SP-DD-D) to cut pilot power with ~no CE loss. Pilot fraction symbol not in abstract. Integer vs fractional Doppler not stated. [AB]
3. Kanazawa, Iimori, Pradhan, Malomsoky, Ishikawa. arXiv 2501.15935 (v3 Feb 2026; TVT 2026 per arXiv record). "Superimposed Pilot-Based OTFS: Will It Work?" https://arxiv.org/abs/2501.15935
   Rel: multi-SP per frame + iterative interference cancellation with decoder soft replicas. Search output: pilot-to-data ratio alpha/(1-alpha); optimal alpha depends on SNR, modulation, pilot assignment; no closed form; alpha tuned by simulation for uncoded BER. Abstract says SP scheme has data-pilot interference. [AB] for abstract; alpha detail [SN]
4. Yuan, Li, Wei, Yuan, Ng. 2021. IEEE WCL 10(9):1954-1958, DOI 10.1109/LWC.2021.3088836. "Data-Aided Channel Estimation for OTFS Systems with a Superimposed Pilot and Data Transmission Scheme". https://scholar.xjtu.edu.cn/en/publications/data-aided-channel-estimation-for-otfs-systems-with-a-superimpose/
   Rel: data-aided iterative SP-OTFS: rough CE from pilot symbol, then detect-refine loop. No power-fraction result in abstract. [SN]
5. Jesbin, Mattu, Chockalingam. 2023. WCNC 2023 pp.1-6, DOI 10.1109/WCNC55385.2023.10118899. "Sparse Superimposed Pilot Based Channel Estimation in OTFS Systems". https://ieeexplore.ieee.org/document/10118899/ ; PDF https://ece.iisc.ac.in/~achockal/pdf_files/WCNC2023_SSP_CE.pdf (PDF unreadable)
   Rel: SP on subset of DD bins; optimal pilots-per-frame and power split obtained by simulation, not closed form. [SN]
6. Zhou, Chen, Yu, Lu. 2024. IEEE Commun. Lett. 28 (ADS bib 2024IComL..28.1939Z). "Iterative Channel Estimation for OTFS Systems Based on Low-PAPR Hybrid Superimposed Pilots". https://ieeexplore.ieee.org/document/10550432/
   Rel: one high-power center pilot + low-power edge pilots; claims no pre-set threshold; power levels not shown as optimized. [SN]
7. Lei, Liu, Liu, Wan, Yang. arXiv 2601.22523 (Jan 2026). "Superimposed-Pilot OTFS Under Fractional Doppler: Modular End-to-End Learning". https://arxiv.org/abs/2601.22523
   Rel: only SP + fractional-Doppler paper found. Learned SP placement + U-Net CE/detection. Pilot power ratio not described in abstract. OTFS, not AFDM. [AB]
8. Bajwa, Haupt, Sayeed, Nowak. 2010. Proc. IEEE 98(6):1058-1076, DOI 10.1109/JPROC.2010.2042415. "Compressed Channel Sensing: A New Approach to Estimating Sparse Multipath Channels". http://people.ece.umn.edu/~jdhaupt/publications/proc10_ccs.pdf (PDF unreadable)
   Rel: only N/sparsity scaling result found: pilot-tone count ~ d x polylog(N) (exponent unverified, snippet garbled). Not SP, no power. [SN]

Not found: "Dong" OTFS SP paper (no hit). Zhou attribution from search output only.

## Q3. Training-energy optimization; superimposed-training power allocation

1. Hassibi, Hochwald. 2003. IEEE TIT 49(4), start p.951. "How much training is needed in multiple-antenna wireless links?" DOI 10.1109/TIT.2003.809594. IEEE https://ieeexplore.ieee.org/document/1193803/ (empty on fetch); PDF https://my.ece.utah.edu/~ece6962/project/training_MIMO.pdf (binary, unreadable)
   Rel: result per search snippet: free training/data power -> optimal training length = M (tx antennas); equal-power constraint -> optimum may exceed M; training suboptimal at low SNR. No closed-form power fraction in snippet. [SN]
2. Tugnait, Meng. 2006. IEEE TSP 54(2):752-765. "On superimposed training for channel estimation: performance analysis, training power allocation, and frame synchronization". https://ieeexplore.ieee.org/document/1576999/ (empty on fetch)
   Rel: closest analogue. Closed-form CE variance; training power allocation for Rayleigh channels framed as SNR maximization for equalizer; frame sync. [SN]
3. Ghogho, McLernon, Alameda-Hernandez, Swami. 2005. IEEE SPL 12(3):226-229, DOI 10.1109/LSP.2004.842283. "Channel estimation and symbol detection for block transmission using data-dependent superimposed training". https://eprints.whiterose.ac.uk/id/eprint/692/
   Rel: data-dependent superimposed training (DDST) removes unknown-data effect at estimator; power split matters. Optimum not read. [SN]
4. Authors not captured. 2008. Journal of Electronics (China). "Power allocation of data dependent superimposed training". https://link.springer.com/article/10.1007/s11767-007-0037-9
   Rel: DDST power split; channel-estimation vs detection trade-off. Optimum not visible. [SN]
5. Tugnait, Luo. 2003. IEEE Commun. Lett. "On channel estimation using superimposed training and first-order statistics". https://www.semanticscholar.org/paper/On-channel-estimation-using-superimposed-training-Tugnait-Luo/b78a74274617c2170d544e80b5365aa07f3b7c2e
   Rel: fixed training power split; first-order statistics. Baseline for Tugnait-Meng. [SN]

Not found: single paper by Orozco-Lugo + Tugnait + Ghogho. Orozco-Lugo co-authors appear in Alameda-Hernandez et al. TSP 2007 (frame sync, DC removal) per search output [SN, no URL opened].

## Q4. Threshold effect (Rife-Boorstyn) for pilot power / sparse DD acquisition

1. Rife, Boorstyn. 1974. IEEE TIT 20(5):591-598, DOI 10.1109/TIT.1974.1055282. "Single-tone parameter estimation from discrete-time observations". https://dl.acm.org/doi/10.1109/TIT.1974.1055282 (403); https://ntrs.nasa.gov/citations/19740062423
   Rel: CRB + ML for single tone. Variance meets CRB above threshold SNR, blows up below; low-SNR outliers. Classic reference. [SN]
2. Graff, Humphreys. 2024. arXiv 2407.19106. "OFDM-Based Positioning with Unknown Data Payloads: Bounds and Applications to LEO PNT". https://arxiv.org/abs/2407.19106
   Rel: closest comms-side overlap. Ziv-Zakai bound captures low-SNR thresholding for OFDM TOA with pilots + unknown data; ML and decision-directed estimators. No threshold-based pilot-power design. [AB]
3. Bomfin, Chafii. 2024. arXiv 2410.07667. "Unique Word-Based Frame Design for Bistatic Integrated Sensing and Communication". https://arxiv.org/abs/2410.07667
   Rel: outlier-probability upper bound for integer-grid FFT DD estimator (true DD off-grid). Not ML threshold; not linked to power in abstract. [AB]
4. Raviteja, Phan, Hong. 2018. arXiv 1808.08360 (later journal version not verified). "Embedded Pilot-Aided Channel Estimation for OTFS in Delay-Doppler Channels". https://arxiv.org/abs/1808.08360
   Rel: threshold-based EP-OTFS CE; integer and fractional Doppler both treated. Fractional case needs much higher pilot power; "50 dB" and "threshold ~3 sigma" figures come from secondary summaries, not abstract. [AB; numbers SN]
5. Wang, Wang, Caire. 2026. arXiv 2608.26441. "On A Unified Cramer-Rao Bound Framework for Joint Delay-Doppler Estimation with Multi-Carrier Waveforms". https://arxiv.org/abs/2608.26441
   Rel: CRB side of power allocation across TF symbols. Search output says uniform power can be far from Pareto-optimal CRB. Abstract is one sentence; claim [SN].

Q4 verdict: no comms paper found using Rife-Boorstyn / ML outlier threshold to set pilot power for sparse DD acquisition. Closest: 2407.19106 (ZZB threshold, unknown data, OFDM TOA).

## Q5. Riegler BP-MF citation; mean-field overconfidence

1. Riegler, Kirkelund, Navarro Manchon, Badiu, Fleury. 2013. IEEE TIT 59(1):588-602, DOI 10.1109/TIT.2012.2218573 (journal fields from DBLP search output; DBLP fetch blocked). "Merging Belief Propagation and the Mean Field Approximation: A Free Energy Approach". arXiv 1112.0467 v3 (28 Jun 2012). https://arxiv.org/abs/1112.0467
   Rel: citation CONFIRMED (authors + title verified on arXiv page). Region-based free energy; BP-MF fixed points = stationary points of constrained free energy; convergence under factor-graph conditions; OFDM iterative CE + decoding demo. No overconfidence statement in abstract. [AB]. Unresolved: ResearchGate lists ISTC 2010 DOI 10.1109/ISTC.2010.5613851 (possible earlier version) [SN].
2. Badiu, Kirkelund, Navarro Manchon, Riegler, Fleury. 2012. arXiv 1202.1467 v2 (Jul 2012). "Message-Passing Algorithms for Channel Estimation and Decoding Using Approximate Inference". https://arxiv.org/html/1202.1467
   Rel: companion BP-MF application (Sec. IV-C: BP-MF channel message variance formula, no accuracy analysis). Says BP-EM uses point estimates. No overconfidence statement. Venue not stated. [FT]
3. Odgers, Riegler, Swaroop, Fortuin. 2026. arXiv 2606.25745. "Gaussian Mean Field Variational Inference can Overestimate Predictive Variance". https://arxiv.org/abs/2606.25745
   Rel: conjugate linear regression: MFVI underestimates parameter-space variance but can overestimate predictive variance. Relevant nuance: symbol posteriors are predictive-like. Note author "Ben Riegler" is not Erwin Riegler. [AB]
4. Nguyen, Atzeni, Tolli, Swindlehurst. 2022. arXiv 2205.11649. "A Variational Bayesian Perspective on Massive MIMO Detection". https://arxiv.org/abs/2205.11649
   Rel: wireless VB detection with imperfect CSI; estimates noise variance + covariance. No posterior calibration or mean-field overconfidence analysis in abstract. [AB]
5. Giordano, Broderick, Jordan. arXiv 1506.04088 (NeurIPS 2015 version). "Linear Response Methods for Accurate Covariance Estimates from Mean Field Variational Bayes". https://arxiv.org/pdf/1506.04088
   Rel: MFVB underestimates marginal uncertainty, no cross-covariance; linear-response fix. Search-output statement. [SN]
6. Turner, Sahani. 2011. "Two problems with variational expectation maximisation for time-series models", in Barber, Cemgil, Chiappa (eds.), Bayesian Time Series Models, CUP, ch.5 pp.109-130. https://www.gatsby.ucl.ac.uk/~maneesh/papers/turner-sahani-2010-ildn.pdf
   Rel: VEM bias; posterior uncertainty loss. Cited downstream for MF variance underestimation. [SN]
7. Blei, Kucukelbir, McAuliffe. 2017. JASA; arXiv 1601.00670. "Variational Inference: A Review for Statisticians". https://arxiv.org/pdf/1601.00670
   Rel: VI generally understates posterior variance (objective-driven); "may be acceptable" depending on task. [SN]

Q5 verdict: citation confirmed (yes). Mean-field overconfidence specific to joint channel estimation + detection: not found. Generic MF variance underestimation: well documented (secondary). No wireless paper found measuring JED posterior calibration vs actual CE error.

## Verdict: "pilot-fraction scaling law, SP-AFDM, continuous fractional Doppler, threshold-limited not CRB-limited"

1. NOT FOUND as a whole. No paper matches SP + AFDM + continuous fractional Doppler + power-fraction scaling in N/P/SNR + threshold regime.
2. PARTIAL components: closed-form SINR-optimal SP power exists for SP-OTFS on integer grid (2010.15066 Eq. 71; SNR trend only; no N/P law). Pilot fraction via simulation only for SP-OTFS (2501.15935; WCNC 2023).
3. Fractional Doppler + SP: only learned OTFS (2601.22523) and EP threshold OTFS (1808.08360). No SP-AFDM fractional-Doppler power study.
4. Threshold theory exists (Rife-Boorstyn 1974; ZZB with unknown data 2407.19106) but not mapped to SP pilot-power scaling for sparse DD estimation. CRB side (2608.26441) suggests uniform power is suboptimal, snippet only.
5. Caveat: search-snippet coverage; 7+ PDFs/pages unreadable (IEEE, DBLP, ACM, Springer 403, binary PDFs); US-only search. Before claiming novelty: IEEE Xplore + Scholar full-text search on "superimposed pilot" AND "AFDM" AND ("fractional Doppler" OR "power allocation").
