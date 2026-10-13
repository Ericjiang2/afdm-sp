# lit-v3: evidence packets for C1 (SP bootstrapping limit) and C2 (AFDM diversity = LTV DoF)

Date 2026-10-08. Task 10-08-doppler-cluster. Input: research/ideation-v3.md.
Contract: EXTRACTION ONLY. No novelty verdicts, no distinction judgments in this file. Main session judges.

## Conventions
- Depth tags. [FT] = full text downloaded to scratchpad (curl; HTML via arxiv.org/html, or PDF via pdftotext) and read/grepped locally. [AB] = abstract only. [SN] = only search-result text; page not opened.
- Text inside "..." is verbatim from the local copy of the cited source. Verified by script: whitespace-normalised substring match against the downloaded text (ligatures and line-break hyphens normalised). arXiv-HTML equations appear as the LaTeX alttext of the page.
- pdftotext drops math symbols (Greek, equations). Where so, quotes with missing symbols are fragments; noted per packet (Sayeed-Aazhang, Ma-Leus-Giannakis).
- Text inside [ ] after a quote = extractor locator/note. Single-quoted text inside [ ] is abbreviated/paraphrased by me, NOT verbatim. Section numbers are from headings preceding the passage; equation/theorem numbers copied from source. Locators marked "inferred" are less certain.
- WebFetch summaries were used only for discovery, never as a quote source. Where a page was blocked (Springer, IEEE, ACM, OpenReview, ResearchGate) the tag is [SN] and the source of the quoted text is stated.
- Ordering: Part A = relevance to C1 (A1 closest on SP + density-evolution; A2 closest on threshold-vs-initial-estimate mechanism; A3 is the Benzine paper requested); Part B = relevance to C2. Benzine (A3) is relevant to both.
- Coverage run: ~22 web searches on SP/EXIT/density-evolution/turbo-CE thresholds, SP-OTFS/AFDM, BEM-order, diversity of AFDM/OTFS/doubly selective, Doppler diversity vs estimation error. In the [FT] sources grepped (terms: converge, threshold, EXIT, bootstrap, initial, number of paths/taps), no threshold was found stated explicitly as a function of channel DoF K, BEM order or Doppler spread. A2 (Porto-de Lamare) states a convergence threshold in terms of initial estimation error and ties that error to number of pilots; A1 (Liang) gives density-evolution convergence vs Eb/N0, rho, M.

# PART A. Evidence packets for C1 (bootstrapping / convergence / threshold / richness)

## A1. Liang, Rave, Fettweis - Iterative Joint Channel Estimation and Decoding Using Superimposed Pilots in OFDM-WLAN
- Cite: T.-J. Liang, W. Rave, G. Fettweis, ICC (preprint header says ICC 2011 and DOI 10.1109/ICC.2006.255288; source header internally inconsistent).
- URL: https://www.vodafone-chair.org/pbls/legacy/t-j-liang/Iterative_Joint_Channel_Estimation_and_Decoding_Using_Superimposed_Pilots_in_OFDM-WLAN.pdf
- Depth: [FT] (pdftotext of full PDF; Secs I-V read).
- (b) MODEL
  - "we used a maximal number of L = 8 taps in" [Sec II]
  - "exponential power delay profile which is assumed to be known" [Sec II]
  - "(assumed to be constant during a burst)" [Sec II]
  - "superimposed pilots are transmitted parallel in time with M unknown data symbols using a fraction" [Sec I; pilot is superimposed on M unknown data OFDM symbols]
- (c) ASSUMPTIONS
  - "are assumed to be i.i.d. and Gaussian-distributed according to the so-called" [Sec II; Gaussian Density Model [3] for decoder LLRs]
- (d) METHOD
  - "The channel state is initially estimated only from the known pilot portion within the received signal." [Sec II]
  - "Starting from the 2nd iteration, the current channel state (assumed to be constant during a burst) is re-estimated using both parts of the received signal (pilots and data)" [Sec II]
  - "As discussed in section III, the variance" [Sec IV-A footnote 2; sentence continues (symbols interleaved in extraction): sigma_EH^2 in the first iteration can be exactly determined by theory]
- (e) RESULTS
  - "The transmission delay is shortened with superimposed pilots to two thirds at the price of at least ten iterations at the receiver." [Sec IV-D]
  - "Fig. 6 (f) shows that such a preamble technique converges after three iterations whereas a superimposed pilot technique requires at least ten iterations." [Sec IV-B3]
- (f) CONVERGENCE / THRESHOLD / INIT / RICHNESS
  - "In this paper we study the conditions under which superimposed pilots can be successfully used for jointly estimating the channel and detecting data." [Abstract]
  - "Under appropriate conditions the density evolution of the LLR values λDecIN and λDecOUT leads to an increase of their associated SNR values" [Sec II]
  - "Generally, if the power ratio becomes too small or too large, the aggregate performance is bad because either the channel estimator or the decoder performs very bad." [Sec IV-B2]
  - "an optimal power ratio exists for a fixed burst length M" [Sec IV-B2]
  - "shows for M = 1, 3 and 4 that, if ρ is fixed, the aggregate performance using a superimposed pilot technique increases monotonously by averaging more symbols to improve the quality of the channel estimate." [Sec IV-B2, Fig. 6(e)]
- NOTE: no statement found tying convergence to number of channel taps L, Doppler spread, or BEM order (grep for converge/threshold/taps).

## A2. Porto, de Lamare - Iterative Channel Estimation, Detection and Decoding for Multi-Antenna Systems with RIS (arXiv 2512.22731)
- URL: https://arxiv.org/abs/2512.22731 (HTML read: https://arxiv.org/html/2512.22731). Depth: [FT] (Secs II, V-C read).
- (b) MODEL
  - "A single-cell multiuser uplink system featuring a multiple-antenna access point (AP) assisted by R reflective intelligent surfaces (RIS)" [Sec II]
  - "exploit encoded pilots (EP), enabling the use of both pilot and parity bits to iteratively refine channel estimates" [Abstract]
  - "assuming a NLOS channel" [Sec V-C]
- (d) METHOD (Sec V-C recursion)
  - "\text{NMSE}^{(\beta+1)}=\text{NMSE}_{\text{min}}+Q\left(\sqrt{\frac{\sigma_{z}^{2}}{\sigma_{e,\beta}^{2}}G_{c}}\right)^{2}" [eq (68)]
  - "Considering a sufficiently large pilot length such that (50) holds (i.e., T\gg L_{e}K )" [Sec V-C; T=pilot length, L_e K = unknown channel coefficients]
- (f) CONVERGENCE / THRESHOLD / INIT
  - "we derive the evolution of the NMSE for channel estimation as a function of the number of iterations and compute the SNR necessary for the iterative method to converge" [Sec V-C]
  - "\sigma_{e,\beta}^{2}>\text{NMSE}_{\text{min}}+Q\left(\sqrt{\frac{\sigma_{z}^{2}}{\sigma_{e,\beta}^{2}}G_{c}}\right)^{2}" [eq (70), convergence condition]
  - "must exceed a certain threshold to ensure the convergence of the iterative processing" [Sec V-C after eq (72)]
  - "A smaller number of pilots leads to a higher estimation error, which in turn increases the minimum required transmit power for convergence" [Sec V-C]

## A3. Benzine, Bemani, Ksairi, Slock - Models, Methods and Waveforms for Estimation and Prediction of (Doubly) Sparse Time-Varying Channels (arXiv 2504.13762v2, 7 Nov 2025)
- URL: https://arxiv.org/abs/2504.13762 ; HTML full text https://arxiv.org/html/2504.13762. Depth: [FT] (all sections read incl. V; appendices not read). Note arXiv listing title is '...Doubly Sparse...'; HTML title is '...Sparse...'.
- (b) MODEL
  - "r_{n}=\sum_{p=1}^{N_{\rm p}}g_{p}e^{\imath 2\pi\nu_{p}n\Delta fT_{\rm s}}s(nT_{\rm s}-\tau_{p}T_{\rm s})+z_{n},\quad n\in\mathbb{Z}" [eq (3), Sec II]
  - "h_{l,n}=\sum_{q=-Q}^{Q}I_{l,q}\sum_{i=1}^{N_{\rm D}}\alpha_{l,q,i}e^{\imath 2\pi\frac{n(q+\kappa_{i})}{N}}" [eq (29), Def. 4 off-grid DS-LTV]
  - "\alpha_{l,q,i}\sim\mathcal{CN}\left(0,\sigma_{\alpha}^{2}\right)" [Def. 4]
  - "Thanks to this relaxation, the channel model becomes compatible with CDL models." [Sec IV-A, Remark 2]
  - "N=4096,L=30,Q=7" [Sec V on-grid sim: p_d=0.2, p_D in {0.2,0.4}]
  - "( N=2048,Q=7,N_{\rm p}=46 )" [Fig. 12 caption (off-grid)]
  - "( N=2048,L=20,Q=7,p_{\rm d}=p_{\rm D}=0.2 )" [Fig. 13 caption]
- (c) ASSUMPTIONS
  - "As opposed to the joint channel estimation and data detection approach of [26], we only consider pilot-based channel estimation." [Sec III-C; [26]=Ranasinghe et al. TWC 2025]
  - "Note that the knowledge of the delay-Doppler sparsity support, i.e., of \left\{I_{l,q}\right\}_{l=0\cdots L-1,q=-Q\cdots Q} , at the receiver side is now assumed." [Sec IV-D]
  - "The number N_{\rm p} of pilots is sufficiently large for the MSE associated with estimating \boldsymbol{\beta} (and hence \mathbf{h}_{l}^{\rm BEM} per (43)) to converge to zero as \sigma_{w}^{2}\to 0" [Assumption 3]
- (d) METHOD
  - "\hat{\boldsymbol{\beta}}=\mathbf{B}\left(\sigma_{\alpha}^{2}\mathbf{M}_{\rm p}^{H}\mathbf{M}_{\rm p}+\sigma_{w}^{2}\mathbf{I}\right)^{-1}\mathbf{M}_{\rm p}^{H}\mathbf{y}_{\rm p}" [eq (40), LMMSE of DPSS-BEM coeffs]
  - "HiHTP is known to converge, with a geometric convergence rate, provided that the associated HiRIP is small enough" [Sec III-C (on-grid CS estimator only)]
- (e) RESULTS
  - "let P_{\rm afdm} be the smallest integer satisfying (L-1)P_{\rm afdm}+2Q+1\geq s_{\rm d}s_{\rm D}" [Theorem 2]
  - "if we set Q_{\rm BEM}\geq C\log\frac{1}{\epsilon} for some constant C" [Theorem 3 (precision of off-grid model)]
  - "shows that as few as 4 DPSS basis functions ( Q_{\rm BEM}=4 ) are sufficient to achieve good-enough precision" [Sec IV-C]
- (f) CONVERGENCE / ORDER / DIVERSITY / RICHNESS
  - "Note that this value is unrelated to the Doppler spread value 2Q+1 : a larger Doppler spread does not imply the need for a larger value of Q_{\rm BEM} ." [Sec IV-C]
  - "While increasing Q_{\rm BEM} improves the precision of the model, it also increases the number of unknowns to be estimated, revealing the trade-off between model precision and pilot overhead." [Sec V]
  - "This is why Q_{\rm BEM}=3 yields the best MSE at the lower SNR value as opposed to Q_{\rm BEM}=4 at the higher." [Sec V, Fig. 12]
  - "When P_{\rm afdm}\triangleq 2N|c_{1}| is set to 2Q+1 , AFDM achieves full diversity [20] and the measurements are non-compressive." [Sec III-C after Thm 2]
  - "Note that, since OTFS is a full-diversity waveform for LTV channels," [Sec III-C]
  - "This also hints at the possibility that the performance advantage over OTFS tends to diminish as the channel becomes less sparse." [Sec V, Fig. 10]
  - "While data-aided approaches can improve estimation accuracy, we believe that the relative performance comparison results we obtain assuming pure pilot-based channel estimation will continue to hold under the joint approach" [Sec III-C]
- NOTE: grep found no superimposed pilot, no EXIT/threshold analysis, no diversity theorem proved in this paper (diversity cited to [20]).

## A4. Mishra, Singh, Prasad, Budhiraja - OTFS Channel Estimation And Data Detection Designs With Superimposed Pilots (arXiv 2010.15066)
- URL: https://arxiv.org/abs/2010.15066 ; HTML https://arxiv.org/html/2010.15066v1. Depth: [FT] (Secs I-VI grep-guided + Secs III-B, IV read).
- (b) MODEL
  - "The quantity Q is the number of propagation paths" [Sec II]
  - "We use, similar to [7], a 5 -tap delay-Doppler channel whose parameters are given in Table II." [Sec VI]
- (d) METHOD
  - "This algorithm is initialized with data detected by the SP-NI design." [Sec III-B after Alg. 2]
  - "proposed SP-I algorithm when ||\hat{\mathbf{h}}^{(n)}-\hat{\mathbf{h}}^{(n+1)}||^{2}<10^{-6} or when the number of iteration 10 , whichever is achieved earlier" [Sec VI (stopping rule of SP-I)]
- (e)/(f) RESULTS, INIT, CONVERGENCE
  - "The first SP design estimates channel by treating data as interference, which degrades its performance at high signal to noise ratio." [Abstract]
  - "We also derive a lower bound on the signal-to-interference-plus-noise ratio of the proposed designs, and maximize it by optimally allocating power between data and pilot symbols." [Abstract]
  - "estimates channel by treating data as interference, which as shown later in Section-VI, degrades its performance at high SNR values" [Sec III-B]

## A5. Kanazawa, Iimori, Pradhan, Malomsoky, Ishikawa - Superimposed Pilot-Based OTFS: Will It Work? (arXiv 2501.15935v3, Feb 2026)
- URL: https://arxiv.org/abs/2501.15935 ; HTML https://arxiv.org/html/2501.15935. Depth: [FT] (grep-guided; Secs III-V read).
- (b) MODEL
  - "We apply the doubly-selective fading channel with the number of paths P=4" [Sec V; h_i ~ CN(0,1/P), uniform power profile]
  - "Note that we set fixed maximum delay shift l_{\mathrm{max}}=4 and Doppler shift k_{\mathrm{max}}=2" [Sec V]
  - "the maximum number of pilots is N_{p}=9 for the multiple-SP scheme" [Sec V]
- (d) METHOD
  - "The SP-based scheme employs the threshold \gamma_{\mathrm{SP}}^{(0)} in the initial stage of an iterative interference cancellation algorithm, which is composed of channel estimation and symbol detection." [Sec III-C]
  - "deriving the optimal updated threshold is a challenging task, as the progress of the interference cancellation depends on the accuracy of the estimated data symbols and channel matrices for each trial" [Sec III-C]
- (e)/(f) RESULTS, INIT, CONVERGENCE
  - "In the SP-based scheme, the received symbols contain inevitable data-pilot interference, resulting in poor channel estimation accuracy." [Sec V]
  - "it tended to converge after a few trials" [Sec V-C]
  - "the single superimposed pilot (SP)-based scheme experiences inevitable data-pilot interference, leading to coarse channel estimation" [Abstract]

## A6. Zheng, Wen, Mao, Xiao, Wang - Channel Estimation for AFDM With Superimposed Pilots (arXiv 2404.10232; IEEE TVT per [28] in 2607.18881)
- URL: https://arxiv.org/abs/2404.10232 ; HTML https://arxiv.org/html/2404.10232. Depth: [FT] (short paper, Secs III-IV read).
- (b) MODEL
  - "we consider the AFDM system with N=512 and quadrature PSK. The maximum Doppler shift index \alpha_{\text{max}}=2 , and the maximum delay index l_{\text{max}}=2. The number of channel paths is P=3." [Sec IV]
  - "Each channel path has a different delay index and random Doppler index chosen from [-\alpha_{\text{max}},\alpha_{\text{max}}]." [Sec IV]
  - "we eliminate the guard samples to allow full data transmission and place the pilots on top of the data signal in the DAFT domain" [Sec III-A]
- (c)/(d) ASSUMPTIONS, METHOD
  - "Therefore, we can treat \boldsymbol{\Phi}_{d}\mathbf{x}_{d} as part of the effective noise in the process of channel estimation" [Sec III-B]
  - "we introduce a threshold criterion to estimate" [Sec III-B; path-indicator b via threshold gamma]
  - "To achieve more precise estimation, we resort to the iterative interference cancellation." [Sec III-D]
- (e)/(f) RESULTS
  - "It is observed that when the number of pilots is fixed, the MSE performance is improved as the number of iterations increases." [Sec IV, Fig. 2]
  - "as the pilot number increases, the channel estimation performs better and the effect of the iterative algorithm is more obvious" [Sec IV]
  - "as the \text{SNR}_{d} increases when \text{SNR}_{d} >21 dB, the BER performance deteriorates with the increasing \text{SNR}_{d}" [Sec IV, Fig. 3 (pilot power fixed)]

## A7. Luo, Guan, Ge, Jiang, Meng, Gonzalez G. - Data-aided Channel Estimation and Sensing With Sparse Bayesian Learning for AFDM-ISAC System (arXiv 2607.18881, 21 Jul 2026)
- URL: https://arxiv.org/abs/2607.18881 ; HTML https://arxiv.org/html/2607.18881. Depth: [FT] (Sec I, VI read; algorithm sections skimmed).
- (b) MODEL
  - "employs N=256 subcarriers together with 4-QAM modulation" [Sec VI]
  - "We consider R=3 targets in this system" [Sec VI]
  - "The maximum normalized Doppler shift is considered to be k_{max}=2" [Sec VI]
- (d) METHOD
  - "reliably decoded data symbols are fed back as additional pseudo-pilot information to assist channel estimation and sensing" [Abstract]
- (e)/(f) INIT, CONVERGENCE, PILOT-POWER
  - "As observed, the performance at t=1 is relatively poor because only the pilot symbols are available and the data symbols are treated as interference." [Sec VI-B, Fig. 5]
  - "reach a steady level after roughly four iterations" [Sec VI-B, Fig. 5]
  - "all curves first improve and then degrade as the pilot power increases" [Sec VI-B, Fig. 7 (BER vs pilot power)]

## A8. Wang, Pan, Ren, Li, Wang - Model-Order-Adaptive Channel Estimation for AFDM Systems with Fractional Delay and Doppler (arXiv 2610.09970, 7 Oct 2026)
- URL: https://arxiv.org/abs/2610.09970 ; HTML https://arxiv.org/html/2610.09970. Depth: [FT] (Secs I, VII-VIII read; estimator sections skimmed).
- (b) MODEL / (c) ASSUMPTIONS
  - "A dual-pilot reference symbol is employed for path and delay initialization" [Abstract; embedded/dual pilots, discrete-path model with unknown path count]
  - "As the path number increases from 6 to 10, the NMSE performance degrades and more paths are missed at both maximum velocities." [Sec VII, Fig. 9 (300 and 600 km/h)]
- (f) RICHNESS / DIVERSITY vs ESTIMATION
  - "Under a fixed pilot budget, the receiver needs to resolve extra DD responses and estimate more path gains from the same received samples." [Sec VII]
  - "For both mobility scenarios, the BER increases as the true path number increases" [Sec VII, Fig. 10 (SNR 30 dB)]
  - "Although additional resolvable paths can offer stronger diversity when perfect CSI is available [6], they simultaneously enlarge the set of unknown channel parameters under a fixed pilot overhead." [Sec VII]
  - "the degradation in channel accuracy may outweigh the diversity gain promised by a larger number of paths" [Sec VII]
- NOTE: in the passages read, BER vs true path number is reported as increasing over 6..10 paths (Fig. 10); no perfect-CSI BER curve vs path number was seen in those passages; estimator is pilot-aided (dual-pilot reference symbol), not superimposed.

## A9. Fang, Rugini, Leus - Block Transmissions over Doubly Selective Channels: Iterative Channel Estimation and Turbo Equalization (EURASIP JASP 2010, 974652)
- URL: https://link.springer.com/content/pdf/10.1155/2010/974652.pdf (PDF fetched). Depth: [FT] (Secs 1-6 read, Secs 4-5 closely).
- (b) MODEL
  - "Rayleigh distributed with uniform power-delay profile" [Sec 5; E{|h_{n,l}|^2}=1/(L+1), Jakes Doppler spectrum]
  - "the normalized Doppler frequency is fd T = 0.15/N" [Sec 5 (high-mobility case)]
- (c)/(d) ASSUMPTIONS, METHOD
  - "Linear minimum mean-squared error (MMSE) pilot-assisted channel estimators are presented, and the soft data estimates from the turbo equalizers are used to improve the quality of the channel estimates." [Abstract]
  - "In the first iteration, no prior information is available" [Sec 3]
  - "The BEM coefficients h are assumed to be uncorrelated with the transmitted signal s and the noise" [Assumption 3 (Sec 4)]
- (f) CONVERGENCE / DIVERSITY / RICHNESS
  - "It can be shown that, as the values of Doppler spread and channel length increase, a lower BER can be achieved at high SNR." [Sec 5, Figs 8-9 (turbo EQ with perfect CSI after 3 iterations)]
  - "However, the achievable diversity gain is difficult to analyze" [Sec 5]
  - "can even provide multiplicative delay-Doppler diversity gains [1, 2]" [Sec 1; [1]=Sayeed-Aazhang, [2]=Ma-Giannakis]

## A10. Keykhosravi, Bedeer - Joint Superimposed Pilot-aided Channel Estimation and Data Detection for FTN Signaling over Doubly-Selective Channels (arXiv 2503.17565)
- URL: https://arxiv.org/abs/2503.17565 ; HTML https://arxiv.org/html/2503.17565v1. Depth: [FT] (grep-guided; Secs II-V partially read).
- (b) MODEL
  - "Q=2\lceil{f_{d}N\tau T}\rceil is the BEM order" [Sec II (CE-BEM)]
  - "tapped delay line models featuring only two non-zero taps" [Sec V (ITU-R channel models, 2 taps)]
- (d) METHOD / (e) RESULTS
  - "SP-aided joint channel estimation and data detection (JCEDD) method" [Abstract; updates channel estimate in each turbo-equalization iteration]
  - "At equivalent SE and a higher fading rate on the order of $10^{-3}$" [Abstract]

## A11. Takeuchi - Iterative LMMSE Channel Estimation, Multiuser Detection, and Decoding via Spatial Coupling (arXiv 1412.6223)
- URL: https://arxiv.org/abs/1412.6223 ; HTML https://arxiv.org/html/1412.6223. Depth: [FT] (Sec IV density-evolution threshold passages read; rest skimmed).
- (b) MODEL
  - "We consider a pilot-assisted MIMO STC BICM scheme" [Sec II-A; block fading with coherence time T, T_tr pilots]
  - "coherence time T=64 and the number of pilots T_{\mathrm{tr}}=6" [Sec V (sim)]
- (f) THRESHOLD
  - "We shall define the threshold for the iterative CE-MUDD." [Sec IV]
  - "in the large-system limit after taking M\to\infty if and only if the SNR 1/N_{0} is larger than the threshold" [Sec IV; sentence subject: The iterative CE-MUDD can achieve an average BER below epsilon]
  - "thresholds are independent of the number of inner iterations" [Sec V, Table II discussion (section number inferred)]

## A12. Yoon, Moon - Soft-Decision-Driven Channel Estimation for Pipelined Turbo Receivers (arXiv 1104.0419)
- URL: https://arxiv.org/abs/1104.0419. Depth: [FT] (EXIT discussion Sec V-A read).
- (f) EXIT with imperfect CSI
  - "the demapper EXIT curve is also based on the assumption of perfect channel estimation" [Sec V-A]
  - "The gap between each stair-case MI trajectory and the demapper EXIT curve represents the performance loss due to imperfect-CSI." [Sec V-A]

## A13. Li, Zhou, Cao, Zhang, Wen, Li, Jin - Learning-Aided Iterative Receiver for Superimposed Pilots (arXiv 2507.10074)
- URL: https://arxiv.org/abs/2507.10074. Depth: [FT] (grep-guided; Secs II-III, V skimmed).
- (d) METHOD / (f) INIT, CONVERGENCE
  - "At the first JCDD iteration ( i=1 ), initial channel estimates are obtained using the LMMSE-based method:" [Sec III]
  - "the proposed JCDD receiver converges after I=2 iterations, achieving BLER performance comparable to the ideal" [Sec V (high mobility)]
## A14. Doppler-diversity vs channel-estimation-error trade-off cluster (richness double-edged under imperfect CSI)

### A14a. Hou, Ling, Wang - Performance of High-Mobility MIMO Communications with Doppler Diversity (arXiv 1910.06491)
- URL: https://arxiv.org/abs/1910.06491 ; HTML https://arxiv.org/html/1910.06491. Depth: [FT] (Sec I, V read; used here mainly as the intro's pointer to the trade-off literature).
- (b) MODEL
  - "we adopt simple repetition coding" [Sec I]
  - "pilot-assisted repetition coding and spatial multiplexing" [Sec I, contribution 1 (MMSE channel estimation, imperfect CSI)]
  - "The Doppler spread is set to 200 Hz" [Sec V]
- (f) RICHNESS / TRADE-OFF (statements about prior work, Sec I)
  - "In high-mobility scenarios, the channel estimation error will not be negligible." [Sec I]
  - "For a fast fading channel with a short coherence time, the channel estimation performance could be worse, while higher Doppler diversity could be exploited" [Sec I; cites [5]=Baissas & Sayeed, 'Channel estimation errors versus Doppler diversity in fast fading channels', Asilomar 2000]
  - "In [6], the performance of Doppler diversity in the case of imperfect channel estimation was studied, and the trade-off between the channel estimation error and Doppler diversity was derived." [Sec I; [6]=Zhou, Wu, Fan, IEEE TWC 2015]
  - "In [7], the results were further extended to single-input multiple-output systems." [Sec I; [7]=Mahamadu et al., IEEE Access 2018]
  - "When the Doppler spread increases, the average SER of the MRC-like receiver will decrease." [Sec V (estimation error included in model)]

### A14b. Zhou, Wu, Fan - High Mobility Wireless Communications With Doppler Diversity: Fundamental Performance Limits (IEEE TWC 14(12):6981-6992, 2015)
- URL: https://ieeexplore.ieee.org/abstract/document/7174567/. Depth: [SN] (search-result text quoting the abstract; page not opened).
  - "The objective of this paper is to quantify the fundamental tradeoff between Doppler diversity and channel estimation errors in high mobility systems." [abstract via WebSearch]
  - "the maximum Doppler diversity order achievable with imperfect channel state information (CSI), and the loss in signal-to-noise ratio (SNR) caused by channel estimation errors." [abstract via WebSearch]
- (search-summary paraphrase, not verbatim): analysis uses a basic repetition code and an optimal diversity receiver; derives pilot/data energy split.

### A14c. EURASIP JWCN 2015, 'Energy and spectral efficient Doppler diversity transmissions in high-mobility systems with imperfect channel estimation'
- URL: https://link.springer.com/article/10.1186/s13638-015-0374-6. Depth: [SN] (page blocked; only search-result text).
  - "quasi-convex in Doppler spread" [fragment as quoted in WebSearch output; surrounding claim not verified]
- Also in this cluster, not opened: Mahamadu, Wu, Ma, Zhou, Tang, Fan, 'Fundamental Tradeoff Between Doppler Diversity and Channel Estimation Errors in SIMO High Mobility Communication Systems', IEEE Access 6:21867-21878 (2018), https://ieeexplore.ieee.org/document/8336855/ [bibliographic details from WebSearch only].

# PART B. Evidence packets for C2 (diversity = LTV DoF vs path count)

## B1. Ma, Giannakis - Maximum-diversity transmissions over doubly selective wireless channels (IEEE Trans. Inf. Theory 49(7):1832-1840, July 2003)
- URLs: https://ieeexplore.ieee.org/document/1207384/ ; https://dl.acm.org/doi/10.1109/TIT.2003.813485 (both returned 403/empty to my fetches). Depth: [SN] for abstract text (via WebSearch results quoting those pages) + [FT] restatement of the (Q+1)(L+1) result in Shenoy et al. (B4). Full text NOT obtained (no free PDF found; spincom.umn.edu path 404).
- (e) MAIN RESULT as quoted in search results
  - "Relying on a basis expansion model of the doubly selective channel, we prove that the maximum achievable multipath-Doppler diversity order is determined by the rank of the correlation matrix of the channel's expansion coefficients, and is multiplicative in the effective degrees of freedom that the channel exhibits in the time and frequency dimensions." [abstract]
  - "We design such block precoded transmissions. The corresponding designs for frequency-selective or time-selective channels follow as special cases" [abstract]
- Time-selective precursor (Ma, Giannakis, 'Maximum-Diversity Transmissions over Time-Selective Wireless Channels', WCNC 2002; URL https://www.researchgate.net/publication/2494809_Maximum-Diversity_Transmissions_over_Time-Selective_Wireless_Channels ; [SN]):
  - "Relying on a basis expansion model of time-selective channels, we find that the maximum achievable Doppler diversity is determined by the rank of the correlation matrix of the channel 's expansion coefficients." [abstract via WebSearch]

## B2. Ma, Leus, Giannakis - Space-Time-Doppler Block Coding for Correlated Time-Selective Fading Channels (IEEE Trans. Signal Process. 53(6):2167-2181, June 2005)
- URL: https://sps.ewi.tudelft.nl/pubs/ma05tsp.pdf. Depth: [FT] (pdftotext raw; math symbols dropped by extraction, so equations/Prop. 1 symbols are missing from quotes).
- (b) MODEL
  - "Based on a parsimonious basis expansion model for the underlying time-selective (and possibly correlated) channels, we quantify these gains in closed form." [Abstract]
  - "allow these coefficients to be correlated, but since we will work on a block-by-block basis" [Sec II (BEM)]
  - "the Jakes' model is not as useful, because the number of parameters can be prohibitively large" [Sec II]
- (e) RESULTS (Prop. 1; symbols lost in extraction)
  - "If the correlation matrix of the channel co" [Prop. 1 (Sec III); extraction jumbled and dropped symbols]
  - "has rank , then the maximum diversity order of" [Prop. 1; rank symbol lost in extraction]
  - "found it to depend on the rank of the BEM" [Sec VII conclusion; '...coefficients’ correlation matrix and the minimum Euclidean distance of the constellation used']
- (f) JAKES-GENERATED CHANNELS (simulation)
  - "we have shown that even for channels generated by Jakes' model, our Doppler diversity claim holds true [15]" [Sec VI, Test Case 4]
  - "GLCP-DPS enables the joint space-Doppler diversity, even when the channels are generated" [Sec VI, Test Case 4; continues 'the Jakes’ model and, thus, do not exactly adhere to the BEM.']

## B3. Sayeed, Aazhang - Joint Multipath-Doppler Diversity in Mobile Wireless Communications (IEEE Trans. Commun. 47(1):123-132, Jan 1999)
- URL: https://minds.wisconsin.edu/bitstream/1793/9406/1/file_1.pdf. Depth: [FT] (pdftotext raw; math symbols dropped, so the exact product expression for the number of diversity channels is lost).
- (b) MODEL
  - "different lags (different scatterers) are uncorrelated (independent)" [Sec II (WSSUS scattering)]
- (e)/(f) RESULTS, DIVERSITY COUNT
  - "We show that the Doppler spread induced by temporal channel variations in fact provides another means for diversity" [Abstract]
  - "independent, flat-fading (diversity) channels by appropriately" [Sec III after eq (20); '...sampling the multipath-Doppler plane']
  - "diversity channels is proportional to the product" [Sec III after eq (20); product expression lost in extraction]
  - "of diversity is proportional to the time-bandwidth product" [Sec III after eq (20)]
  - "even the relatively small Doppler spreads encountered in practice can yield significant diversity gains via appropriate signaling and reception" [Sec I]

## B4. Shenoy, Ghauri, Slock - Diversity Order of Linear Equalizers for Doubly Selective Channels (EURECOM publication 2760)
- URL: https://www.eurecom.fr/en/publication/2760/download/cm-publi-2760.pdf. Depth: [FT] (5 pp. read; used as a verifiable restatement of Ma-Giannakis 2003). Note: D. Slock is also co-author of Benzine et al. (A3).
- (b) MODEL / (e) RESULT RESTATED
  - "In [5], the authors used the Complex-Exponential Basis Expansion Model (CEBEM) [6] with Q + 1 basis functions to model the doubly selective channel of memory L." [Sec I]
  - "the maximum diversity in the channel is upper bounded by (Q + 1)(L + 1)" [Sec I, attributed to [5]=Ma & Giannakis 2003]
  - "and can be achieved when maximum-likelihood decoding is used at the receiver" [Sec I]

## B5. Bemani, Ksairi, Kountouris - Affine Frequency Division Multiplexing for Next Generation Wireless Communications (arXiv 2204.12798; IEEE TWC 22(11):8214-8229, 2023); earlier version arXiv 2104.11331
- URLs: https://arxiv.org/abs/2204.12798 (PDF https://arxiv.org/pdf/2204.12798) ; https://arxiv.org/abs/2104.11331. Depth: [FT] (Secs II-IV, Appendix A statement, sims skimmed).
- (b) MODEL
  - "where P ≥ 1 is the number of paths" [eq (21)]
  - "Note that this model is general and also covers the case where each delay tap can have a Doppler frequency spread by simply allowing for different paths" [Sec II; '... i, j in {1..P} to have the same delay li = lj, while satisfying fi != fj']
- (c) ASSUMPTIONS
  - "Assuming perfect channel state information and ML detection at the receiver" [Sec IV]
  - "diversity analysis is presented only in the case of integer Doppler shifts" [Sec IV]
  - "Theorem 1 given below, also holds for the fractional Doppler case" [Sec IV]
- (e) RESULTS
  - "we show analytically that AFDM can achieve full diversity in doubly dispersive channels, where full diversity refers to the number of multipath components separable in either the delay or the Doppler domain" [Abstract]
  - "Hence, the diversity of AFDM is given by" [Sec IV, eq (48): rho = min_{m!=n} rank(Phi(delta^(m,n))) <= P]
  - "Theorem 1. For a linear time-varying channel with a maximum delay lmax and maximum normalized Doppler shift αmax , AFDM with c1 satisfying (42) achieves full diversity (ρ = P ) if" [Sec IV, Theorem 1]
  - "2αmax + lmax + 2αmax lmax < N." [eq (51)]
  - "We give the proof of Theorem 1 only in the case of integer Doppler shifts." [Appendix A]
- (f) DIVERSITY-RELATED SIM (earlier version 2104.11331)
  - "in a 21-path LTV channel with l_{\max}=2 and \alpha_{\max}=3 . For each delay tap, there are 7 paths with different Doppler shifts from -3 to 3." [Sec VI, Fig. 5]

## B6. Surabhi, Augustine, Chockalingam - On the Diversity of Uncoded OTFS Modulation in Doubly-Dispersive Channels (arXiv 1808.07747; IEEE TWC 18(6):3049-3063, 2019)
- URL: https://arxiv.org/abs/1808.07747 ; HTML https://arxiv.org/html/1808.07747. Depth: [FT] (grep-guided; Secs on diversity, App. A header, sim setup).
- (b) MODEL
  - "and the number of taps is considered to be four (i.e., P=4 )" [simulation section]
  - "We initially assume the fractional parts" [channel-model section; fractional case in App. A]
- (e)/(f) RESULTS, DIVERSITY
  - "where full diversity refers to the number of multipath components separable in either the delay or Doppler dimension" [Abstract]
  - "we prove that the asymptotic diversity order of OTFS (as SNR $\rightarrow \infty$) is one" [Abstract]
  - "\rho_{\tiny\mbox{siso-otfs}}=\min_{i,j\ i\neq j}\ \mbox{rank}(\mathbf{\Delta}_{ij})" [diversity-order derivation (diversity = min rank of codeword-difference matrix)]
  - "on the asymptotic diversity order of OTFS holds even for the more general" [diversity-order section; '...input-output relation which considers non-zero fractional delay and Doppler values ... derived in Appendix A']

## B7. Ge, Meng, G., Wen, Guan, Fan - Linear Precoding Design for OTFS Systems in Time/Frequency Selective Fading Channels (arXiv 2501.00272)
- URL: https://arxiv.org/abs/2501.00272 ; HTML https://arxiv.org/html/2501.00272. Depth: [FT] (text ~36 kB read via grep + Secs II-III).
- (b) MODEL
  - "is the order of BEM basis functions" [Sec II-B; eq (3): h[c]=sum_{q=0}^{Q} c_q e^{j w_q c}, Q=2*ceil(N*fbar_max)]
  - "Note that the BEM facilitates our development and analysis of the diversity for OTFS systems over time-selective fading channels." [Sec II-B]
- (e) RESULTS
  - "the system diversity order is determined by R , which could be as high as the number of bases Q+1 in the BEM" [Sec III (time-selective case)]
  - "the system diversity order is determined by R , which could be as high as the number of resolvable paths L of the channel" [Sec III (frequency-selective case)]
- NOTE: text search for Jakes/Clarke/covariance finds only the title of reference [4] (Ma-Leus-Giannakis, 'correlated time-selective fading channels'); no covariance-rank statement in body.

## B8. Cross-reference quotes already captured above for C2
- AFDM full diversity cited as path-separation property: A3 (Benzine) 'When P_afdm = 2N|c1| is set to 2Q+1, AFDM achieves full diversity [20]'; A7 (Luo) intro; A8 (Wang) 'Although additional resolvable paths can offer stronger diversity when perfect CSI is available [6]'.
  - "AFDM can separate all propagation paths in the DAF domain and allows each transmitted symbol to experience every path coefficient, thereby achieving full diversity in doubly dispersive channels" [A7 Luo et al., Sec I]
  - "can even provide multiplicative delay-Doppler diversity gains [1, 2]" [A9 Fang et al., Sec 1]

## B9. Raviteja, Hong, Viterbo, Biglieri - Effective Diversity of OTFS Modulation (IEEE Wireless Commun. Lett. 9(2):249-253, Feb 2020)
- URL: https://engit.monash.edu/profiles/wp-content/uploads/2017/09/wcl20Raviteja.pdf. Depth: [FT] (abstract, Sec I, diversity cases and Remark 1 read; pdftotext raw).
- (b) MODEL
  - "In this letter we study the diversity of OTFS assuming rectangular waveforms and a delay–Doppler channel with two paths." [Abstract]
- (e)/(f) RESULTS, DIVERSITY
  - "we guarantee a diversity order 2, which is the number P of" [diversity analysis near eq (12); continues '... paths and hence the maximum achievable value.']
  - "OTFS achieves full effective diversity with typical system parameters as P = 2" [concluding discussion]
  - "Future work will show the extension of the above analysis to P values greater than 2." [concluding discussion]
  - "we advocate the use of an effective diversity (ED)" [Sec I]
# PART C. Snippet-only items (no page opened; no verbatim text beyond what is quoted)

C-1. Zemen, Bernado, Czink, Molisch, "Iterative Time-Variant Channel Estimation for 802.11p Using Generalized Discrete Prolate Spheroidal Sequences," IEEE TVT 61(3):1222-1233 (2012). https://ieeexplore.ieee.org/document/6135825/ . Depth [SN]. Text as shown in WebSearch output quoting the abstract:
  - "Due to the tight subspace design, the iterative receiver is able to converge to the same bit error rate (BER) as a receiver with perfect channel knowledge."
  - "the number of iterations sufficient for convergence can be reduced by a factor of 2-3"
  - "this pilot pattern violates the sampling theorem for channels with both large delay spread and large Doppler spread"

C-2. 'EXIT Chart Analysis of an Iterative Receiver with Channel Estimation,' https://ieeexplore.ieee.org/document/4411672/ . Depth [SN]; authors/venue not retrieved. WebSearch output paraphrase only (not verbatim): EXIT function derived for a channel estimator using pilot symbols plus soft decoding information, tested in a CDMA link with FEC and iterative multiuser detection (soft interference cancellation + single-user decoding); J-function used.

C-3. Titles/URLs only (search results; pages blocked or not opened; no text read):
  - 'Doubly-Selective Channel Estimation Using Superimposed Training and Discrete Prolate Spheroidal Basis Models' https://openreview.net/forum?id=wcF80ruBiT (OpenReview browser check blocked fetch); and IEEE 'On Doubly Selective Channel Estimation Using Superimposed Training and Discrete Prolate Spheroidal Sequences' https://ieeexplore.ieee.org/document/4531119/ . Authors not retrieved.
  - 'Doubly-Selective Channel Estimation Using Data-Dependent Superimposed Training and Exponential Bases Models' https://ieeexplore.ieee.org/abstract/document/4067836/ ; 'Self-Interference Suppression in Doubly-Selective Channel Estimation Using Superimposed Training' https://ieeexplore.ieee.org/iel5/4288670/4288671/04289174.pdf ; Auburn thesis 'Doubly-Selective Channel Estimation and Equalization Using Superimposed Training and Basis Expansion Models' http://etd.auburn.edu/handle/10415/884 . Search-result paraphrase only: first stage uses first-order statistics, unknown data acts as interference ('self-interference'), later stage feeds detected symbols back.
  - Tang, Cannizzaro, Leus, Banelli, 'Pilot-assisted time-varying channel estimation for OFDM systems,' IEEE TSP 55:2226-2238 (2007), https://ieeexplore.ieee.org/document/4156430/ : title/venue only.
  - Ma, Leus, Giannakis 2005 is [FT] (B2). Ma-Giannakis 2003 abstract is [SN] (B1).

# PART D. Papers/pages I could NOT access (plain list)
- Ma & Giannakis, 'Maximum-diversity transmissions over doubly selective wireless channels,' IEEE TIT 2003: full text not obtained (IEEE Xplore, ACM, ResearchGate returned 403/empty; spincom.umn.edu path 404; no free PDF found). Abstract text only via search results [B1].
- Zhou, Wu, Fan, IEEE TWC 2015 (Doppler diversity fundamental limits): IEEE Xplore page not opened; abstract fragments via search results only [A14b].
- Mahamadu et al., IEEE Access 2018 (SIMO Doppler diversity vs estimation error): not opened.
- Baissas & Sayeed, 'Channel estimation errors versus Doppler diversity in fast fading channels,' Asilomar 2000: not opened; known only via citation in Hou et al. (A14a).
- EURASIP JWCN 2015 'Energy and spectral efficient Doppler diversity transmissions ... imperfect channel estimation': Springer blocked; only a search-result fragment [A14c].
- Zemen et al., IEEE TVT 2012 (iterative DPSS 802.11p); Zemen & Mecklenbraeuker IEEE TSP 2005 (DPSS channel estimation); Zemen et al. IEEE TWC 2006 (iterative joint CE + MUD, MC-CDMA): not opened (IEEE paywall); no free PDF located.
- IEEE 4411672 'EXIT Chart Analysis of an Iterative Receiver with Channel Estimation': not opened.
- Superimposed-training + BEM/DPSS papers (OpenReview wcF80ruBiT; IEEE 4531119; IEEE 4067836; IEEE 4289174; Auburn thesis): not opened.
- Tang, Cannizzaro, Leus, Banelli, IEEE TSP 2007: not opened (TU Delft path 000/404).
- Ranasinghe, Rou, de Abreu, Takahashi, Ito, 'Joint channel, data, and radar parameter estimation for AFDM systems in doubly-dispersive channels,' IEEE TWC 24(2):1602-1619 (2025) [cited as [26] by Benzine et al. as the joint CE+detection approach]: not located/opened.
- Benzine et al. appendices A-D (proofs; arXiv 2504.13762) not read; main text Secs I-VI read.
- 'AFDM Channel Estimation in Multi-Scale Multi-Lag Channels' (arXiv 2405.02660), 'AFDM-Enabled Integrated Sensing and Communication' (arXiv 2502.14203), 'GI-Free Pilot-Aided Channel Estimation for AFDM' (arXiv 2404.01088): appeared in search results; not opened beyond snippets; no quotes taken.