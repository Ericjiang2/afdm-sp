# lit-wideband-afdm (2026-10-08)

Scope: literature only. No code run.
Legend: [FT-P] full text, PDF page images read, eqs checked by eye. [FT-X] full text via WebFetch extractor, eq numbers from extractor (medium confidence). [AB] abstract/landing page. [SN] search snippet only. Pith page = third-party AI review, not primary.
Prior SP-AFDM/OTFS lit: research/lit-sp-power.md (not repeated).

## Q1. AFDM + per-path Doppler scale; 2Nc1; c1 design

1. Li, Wang, Ge, Shen, Guan, Wen, Yuen. 2025. arXiv 2507.03537 "AFDM over Wideband Doubly-Dispersive Channels With Time-Scaling Effects". Conf: ICCC 2025, DOI 10.1109/ICCC65529.2025.11148919 [SN]. https://arxiv.org/html/2507.03537 [FT-P pp6-9 + FT-X]
   - Model: per-path delay l_i + scale a_i (eq 11, 18-22). DAF matrix H = sum h_i H_i (eq 18-19); y = Phi(x)h + w (eq 56). Narrowband case = eq 12, 38.
   - Drift term: eq 31b psi in [0, 2Nc1]. eq 32a offset Q = 2Nc1*l + (p-k+2c1*a(a+2)N(N-1))/(1+a). Small-a expansion (mine): alpha-offset ~ 2Nc1 * 2a(N-1).
   - eq 34 width L_i = |[2c1(a^2+2a)N(N-1) + 2c1*a*N^2]/(1+a)| + 2Nv+1. Text: L_i proportional to c1, N, a; "reduces sparsity under severe Doppler spread or long transmission".
   - c1 design: eq 42 separation bound, denominator 2N[(1-a^2)d - 2a(2-a^2)(N-1)], d = l_j - l_i. eq 45 c1 ~ (2kmax + 2amax(N-1) + 2Nv + 1) / (2N[1 - 4amax(N-1)]) (d_min=1). eq 46 N < 1/(4amax) + 1. eq 49-51 quadratic in N. eq 54 narrowband c1 = (2kmax+2Nv+1)/(2N). Sec III: c1 minimized "for sparser representation".
   - Sim: UWA fc=6 kHz, B=4 kHz (df=4 Hz), N=1024, P=4, amax=1e-4 "after resampling" (fn 3, refs 40-42). PEP at N=16. CD-D-OAMP detector.
   - Not in paper: full-diversity analysis under time scaling; resampling method.
   - Third-party: Pith AI review (2026-08-06) says psi coefficient should be (1+a)N not aN, so L_i off ~1/a. No corrected formula. Unverified. https://pith.science/paper/2507.03537 [AB, 3rd party]

2. Bemani, Ksairi, Kountouris. arXiv 2204.12798 (v2 May 2022); journal IEEE TWC 2023 per 2507.03537 ref [9]; ACM listing DOI 10.1109/TWC.2023.3260906 [SN]. "AFDM for Next Generation Wireless Communications". https://arxiv.org/abs/2204.12798 [FT-P pp1-13]
   - Channel: integer or fractional Doppler shift nu_i = N f_i = alpha_i + a_i (sec II-B). No time scaling.
   - Full-diversity c1 (sec IV, eq 40-43): 2Nc1 > 2amax/(lj-li) (40); 2Nc1 > 2(amax+k_nu)/(lj-li) (41); integer case c1 = (2amax+1)/(2N) (42); fractional c1 = (2(amax+xi)+1)/(2N) (43). Non-overlap: 2amax*lmax + 2amax + lmax < N.
   - loc_i = (alpha_i + 2Nc1*l_i)_N (eq 30). Delay gives 2Nc1*l_i; Doppler gives alpha_i only (no N factor).
   - Intro: OCDM cannot reach full diversity in LTV channels.

3. Cao, Zhong, Lyu, Wang, Fu. 2024. arXiv 2405.02660 "AFDM Channel Estimation in Multi-Scale Multi-Lag Channels". GLOBECOM 2024 per comments, DOI 10.1109/GLOBECOM52923.2024.10901055 [SN]. https://arxiv.org/html/2405.02660v2 [FT-X]; abstract https://arxiv.org/abs/2405.02660 [AB]
   - Model: per-path h_i, tau_i, Doppler factor a_i (DTS). CIR eq 3, rx eq 4. DAFT-domain H_bar_i via sinc kernels (eq 5-14). a_i enters only as (1+a_i) in sinc arg; no closed-form alpha offset.
   - Offset loc_i = (Q_i + 2Nc1*l_i)_N (sec II-D); no alpha term. c1 >= (2Qmax+1)/(2N) (sec II-D). Fn 3: 2Nc1*l_i integer.
   - Full diversity: claimed under MSML, by simulation only (sec II-E). No c1-vs-alpha constraint.
   - Setup: UWA motivated, fc=35 kHz, fs=1.5 kHz, N=128, P=5, a ~ 1e-4..1e-2. Resampling only in intro (cites [12], residual error). Estimators: AFDM-IMI (low/mod DTS), AFDM-OMP (high DTS).

No other wideband AFDM c1 design found. HFMC (Q4) uses FM rate K, not c1.

## Q2. AFDM for UWA, 2023-2026

- 2405.02660 (Cao et al.) | 2024 | per-path scale a_i | none in method. (Q1 item 3)
- 2507.03537 (Li et al.) | 2025 | per-path scale a_i | assumed upstream (amax "after resampling"). (Q1 item 1)
- "Spread Spectrum Based AFDM Communications over UWA Channels", ACM DOI 10.1145/3699432.3699491 | 2024 | path-specific Doppler scales cited as challenge; model unverified | unknown. https://dl.acm.org/doi/10.1145/3699432.3699491 [SN; fetch 403]. DAFT-domain PN spreading; claims better BER than SS-OFDM.
- "AFDM-Based Integrated System for Underwater Detection and Communication Waveform Design", IEEE | year unverified | unknown | unknown. https://ieeexplore.ieee.org/document/10978131/ [SN]
- Survey: "AFDM for Communication and Channel Sounding", arXiv 2509.16643 (Sep 2025). UWA subsection, qualitative only. https://arxiv.org/pdf/2509.16643 [SN]
- Not found: AFDM-UWA sea-trial paper; AFDM-UWA paper without resampling beyond 2405/2507.

OCDM precursors (chirp, not AFDM):
- Zhu, Yang, Chen, Xu, Chen. IEEE Access 10 (2022). "Doppler-Resistant OCDM With Multiplex Resampling for Mobile UWA Communication". https://ieeexplore.ieee.org/document/9779721/ [SN]. Multi-resampling branches; Qiandao Lake trials.
- Wang et al. IEEE IoT J 2023. "UWA Communications Based on OCDM for IoUT". https://www.researchgate.net/publication/373086332_Underwater_Acoustic_Communications_Based_on_OCDM_for_Internet_of_Underwater_Things [SN]
- Sensors 2018. "OCDM for Underwater Acoustic Communication". https://pmc.ncbi.nlm.nih.gov/articles/PMC6263921/ [SN]

## Q3. OFDM/OTFS under multi-scale multi-lag UWA: refs + standard fixes

- Li, Zhou, Stojanovic, Freitag, Willett. 2008. IEEE JOE 33(2):198-209, DOI 10.1109/JOE.2008.920471. "Multicarrier Communication over UWA Channels with Nonuniform Doppler Shifts". Preprint https://citeseerx.ist.psu.edu/document?repid=rep1&type=pdf&doi=10267dac32d6f862299969866e326b419c3ac938 ; bib https://www.scirp.org/reference/referencespapers?referenceid=891062 [SN]. Common scale all paths; resample, then uniform residual correction. Page conflict: 2507.03537 ref [1] gives 1638-1649 (Mason 2008 pages); most sources say 198-209.
- Mason, Berger, Zhou, Willett. 2008. IEEE JSAC 26(9):1638-1649, DOI 10.1109/JSAC.2008.081204. Detection, sync, Doppler scale estimation for multicarrier UWA. Bib only; https://link.springer.com/article/10.1007/s11277-012-0600-z (citing refs) [SN]
- Yerramalli, Mitra. 2011. IEEE JOE 36(1):126-138, DOI 10.1109/JOE.2010.2093752. "Optimal Resampling of OFDM Signals for Multiscale-Multilag UWA Channels". https://www.researchgate.net/publication/224224938_Optimal_Resampling_of_OFDM_Signals_for_Multiscale-Multilag_Underwater_Acoustic_Channels [SN]. Origin of MSML term; resampling chosen by HCRB/CRB; summary: optimum near dominant path scale.
- Tu, Duman, Stojanovic, Proakis. 2013 (online 2012). IEEE JOE 38(2):333-346, DOI 10.1109/JOE.2012.2221812. "Multiple-Resampling Receiver Design for OFDM over Doppler-Distorted UWA Channels". https://stuff.mit.edu/people/millitsa/resources/pdfs/kai-joe.pdf [AB: p1 image read; vol/pages SN]. Common-scale resampling leaves post-FFT ICI when per-user/path scales differ. Fix: MR branch per scale, FFT, gradient-descent refinement of sparse estimates. Tested MACE10, KAM08.
- Beygi, Mitra. 2015. IEEE TSP 63(18):4744-4755, DOI 10.1109/TSP.2015.2449266. "Multi-Scale Multi-Lag Channel Estimation Using Low Rank Approximation for OFDM". https://ieeexplore.ieee.org/document/7131580/ [SN]. Low-rank OFDM structure; Prony + ADMM; up to 7 dB gain at low SNR (abstract summary).
- Beygi, Mitra. 2013. IEEE SPL 20(11):1118-1121. "Optimal Bayesian Resampling for OFDM Signaling over Multi-scale Multi-lag Channels". https://usc.academia.edu/SrinivasYerramalli (listing) [SN]. Resampling minimizing total ICI under probabilistic channel.
- Berger, Zhou, Preisig, Willett. 2010. IEEE TSP 58(3):1708-1721, DOI 10.1109/TSP.2009.2038424. "Sparse Channel Estimation for Multicarrier UWA: From Subspace Methods to Compressed Sensing". https://ieeexplore.ieee.org/document/5352256/ [SN]. Root-MUSIC/ESPRIT for limited Doppler spread; OMP/BP for larger spread.
- "A Time-Varying Filter for Doppler Compensation Applied to UWA OFDM", Sensors 19(1):105, DOI 10.3390/s19010105. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6339152/ [SN]. Per-symbol time-scale from pilot tones; sample-by-sample interpolation; resample. Earlier methods assumed constant factor per packet.
- Nature 2025. "Feedforward backpropagated NN for Doppler scale estimation in UWA CP-OFDM". https://www.nature.com/articles/s41598-025-27808-x [SN]
- Wang et al. IEEE TWC 2023. "On the Doppler Squint Effect in OTFS Systems over Doubly-Dispersive Channels". https://arxiv.org/pdf/2302.06156 [SN]. Frequency-dependent Doppler in OTFS.
- Yang, Ma, Liu, Li. IEEE JOE 2025 (vol 51, issue 1, 2026 per arXiv ref). "Underwater Acoustic OTFS With Nonuniform Doppler Shifts: Modeling and Off-Grid Block-Sparse CE". URL NOT RETRIEVED [SN]. Per-path Doppler factor; residual shift persists after time resampling; block-sparse OMP + ML. Do not cite until URL located.
- Arunkumar, Murthy. arXiv 2111.10765 (v3 May 2022). "Orthogonal Delay Scale Space Modulation". Accepted IEEE TSP per comments; venue/vol unconfirmed. https://arxiv.org/abs/2111.10765 [AB]. Fourier-Mellin to delay-scale space; 2D transform replaces ISFFT; near-diagonal channel; UWA/UWB motivation.
- "OTFS modulation for UWA mobile acoustic communications", JASA 154(A), 2023. https://ui.adsabs.harvard.edu/abs/2023ASAJ..154A.249X/abstract [SN]
- "Channel Estimation for OTFS UWA via VAMP", IEEE. https://ieeexplore.ieee.org/document/10723726/ [SN]

Standard fixes: (i) resample by common mean scale; (ii) residual: per-path/per-user MR branches (Tu 2013); (iii) joint MSML estimate (Beygi 2015; Yang 2025 OTFS); (iv) per-symbol pilot-tone scale track + interpolation (Sensors 2019).

## Q4. Doppler-invariant / scale-covariant waveforms linked to AFDM

- Wang, Yuan, Wang, Sun, Hao. 2026. arXiv 2605.19515 (v1 19 May 2026). "Hyperbolic Frequency Multicarrier Modulation for Wideband LTV Channels" (HFMC). https://arxiv.org/html/2605.19515v1 [FT-X; first 100k of 125k chars]. Explicitly AFDM-inspired. Per-path scale a_i (eq 2: r(t)=sum h_i s((1+a_i)t - tau_i)). Subcarriers from one HFM; scale absorbed into equivalent delay (eq 7, 22-25; extractor says eq 7 and 22 differ, unreconciled). 1D input-output. No DAFT formula. No c1; design params K, T0 (eq 33). No full-diversity claim. No resampling. UWA motivated: fc 50 kHz, B 5 kHz, amax 3.43e-3, P=15. Intro calls AFDM narrowband-designed; extractor did not show whether it cites 2507.03537. Check ref list.
- Wang, Shi, Tan, Wang, Sun. 2025. IEEE TWC 24(7):6180-6194. "Orthogonal Hyperbolic Frequency Division Multiplexing Modulation for UWA Communications" (OHFDM). https://ieeexplore.ieee.org/iel8/7693/11078606/10943269.pdf [SN]. Orthogonal HFM subcarriers; abstract claims robustness to path-specific scales; less ICI than OFDM. HFMC intro says it degrades under scaling spread [SN].
- Arunkumar, Murthy (arXiv 2111.10765, above). Mellin scale domain; ODSS subcarriers widen with frequency [SN summary].
- HFM Doppler invariance: "Doppler-invariant property of HFM waveforms". https://www.researchgate.net/publication/229463858_Doppler-invariant_property_of_hyperbolic_frequency_modulated_waveforms [SN]
- HFM probes for Doppler scale + timing, UWA. https://www.researchgate.net/publication/338646592_Joint_Doppler_Scale_Estimation_and_Timing_Synchronization_in_Underwater_Acoustic_Communications [SN]

Link to AFDM: only HFMC (explicit). No paper found combining DAFT with HFM scale covariance or Mellin. Literature says "Doppler-tolerant"; for wideband, scale covariance is the right concept.

## Q5. Superimposed pilots (UWA) for Doppler-scale estimation

- Wang, Qiao, Liang, Chen, Wang, Yang. 2022. Sensors 22(6):2142, DOI 10.3390/s22062142. "Accurate Channel Estimation and Adaptive UWA Communications Based on Gaussian Likelihood and Constellation Aggregation". https://pmc.ncbi.nlm.nih.gov/articles/PMC8955422/ [FT-X]. SP: periodic training, power ratio 0.25:1 (tested 0.15-0.3), subtracted before EQ. Doppler scale NOT estimated: segment CE + GL fusion; average freq offset via HFM head/tail. Sea trial Yellow Sea 2021, fc 12 kHz, B 4 kHz, ~5.5 km, ~0.5 m/s.
- "Doppler and Channel Estimation Using Superimposed LFM Preamble Signal for UWA". https://www.researchgate.net/publication/378273069_Doppler_and_Channel_Estimation_Using_Superimposed_Linear_Frequency_Modulation_Preamble_Signal_for_Underwater_Acoustic_Communication [SN]. Closest hit: Doppler-factor estimator from superimposed LFM preamble + improved OMP. Unverified whether superposed on data or preamble only. Check first.
- "Channel estimation based on superimposed pilot and weighted averaging". https://pmc.ncbi.nlm.nih.gov/articles/PMC9206651/ [SN]. Fetch blocked (reCAPTCHA). Domain and Doppler unknown.
- SP power allocation, OFDM (not UWA): Huang, Li, Li. IEEE TVT 2009. "On the Power Allocation and System Capacity of OFDM Systems Using Superimposed Training Schemes". https://ieeexplore.ieee.org/document/4595665/ [SN]
- SP for AFDM/OTFS: see research/lit-sp-power.md (Zheng 2024 arXiv 2404.10232 [AB]; Mishra 2010.15066 [FT]; Kanazawa 2501.15935 [AB]; Lei 2601.22523 [AB], fractional Doppler, no scale). None estimate per-path scale.
- Non-SP scale estimation for context: pilot tones per symbol (Sensors 2019), HFM probes (ResearchGate 338646592).

## Verdict

Q: "AFDM under per-path Doppler scaling: DAFT-domain model, 2Nc1 magnification, c1 design conflict, SP-based scale-aware receiver" already published?

PARTIALLY.
(a) DAFT-domain I/O, per-path scale: YES. 2405.02660 (2024, sinc form); 2507.03537 (2025, eq 18-22, 56).
(b) 2Nc1 magnification of drift: IMPLICIT. 2507.03537 eq 32a/34: alpha-offset ~ 2Nc1 * 2a(N-1) (my expansion), L_i ~ c1 N a. 2405.02660: 2Nc1*l_i for delay only. No paper states the principle explicitly. Pith AI review disputes coefficient (unverified).
(c) c1 vs wideband conflict: PARTIAL. 2507.03537 couples c1 to amax, N, d: eq 42 needs d(1-a^2) > 2a(2-a^2)(N-1) (~ 4a(N-1)); eq 45 c1 grows with a(N-1); eq 46 N < 1/(4a)+1 for d=1; sparsity-vs-c1 trade-off stated. No paper found analyzing full diversity under time scaling. Bemani eq 40-43 is narrowband only. 2405.02660 full diversity by simulation.
(d) c1 design for wideband: YES (2507.03537 eq 42-46, 54).
(e) SP-based scale-aware AFDM receiver: NOT FOUND. SP-UWA papers do channel tracking only; SP-AFDM/OTFS papers do not estimate scale; UWA scale estimation uses non-SP preambles/tones.

Implication: "DAFT + per-path scale + c1 for wideband" is prior art (Li et al. 2025; Cao et al. 2024). Any novelty claim must be narrower: SP-embedded scale estimation for AFDM + explicit full-diversity analysis under time scaling + drift-induced spread. Cite 2507.03537 as direct prior art. Re-derive its eq 34/45 before relying on them (Pith claim unverified).

## Caveats
- Not verified: ICCC 2025 full text; OHFDM and SS-AFDM full text (SN only); Yang 2025 JOE URL not retrieved; Li 2008 full text not read.
- Blocked: IEEE Xplore pages (not fetched); PMC reCAPTCHA (PMC9206651, PMC6339152); ACM 403.
- "2507.03537 = IEEE TWC" (search summary) unverified; treat as ICCC 2025 + arXiv.
- Coverage: arXiv/IEEE snippets; not exhaustive. No 2026 AFDM-UWA SP paper found.
- Third-party AI review (Pith) and search summaries are not primary; flagged where used.
