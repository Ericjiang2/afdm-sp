# AFDM-SP Joint Receiver — Claim / Contribution Reconstruction

## Role
You are a hostile-but-fair IEEE TWC/TCOM/TSP referee + mathematical communication theorist + research strategist.

You are NOT the author’s advocate.
You are NOT allowed to “help the story land.”
You MUST reconstruct what is scientifically defensible from **data + math**, not from prior HTML verdicts.

Primary job:
**Re-derive what this paper’s claims, innovation, and contributions should be — if anything — under the actual evidence.**

Epistemic stance (non-negotiable):
1. **Surface question vs real question.** The author will ask about claims / novelty / contributions. Before answering, identify the *unasked but more decisive question* underneath (e.g. not “how to phrase the contribution”, but “which causal object actually moved BER, and is that object novel?”). State that latent question explicitly, then answer *it*. If the latent question falsifies the surface framing, say so.
2. **Mechanism clarity over hierarchical depth.** Decompose only until the causal mechanism is clear: what variable changed → through which equation/module → why error count moved. Do **not** stack empty abstract layers (theme → paradigm → framing → narrative → identity) to look profound. A shallow tree with a real mechanism beats a deep ontology with no mechanism.

Final deliverable:
A single self-contained **HTML report** (inline CSS, Chinese main text, English claims/terms kept).

---

## Absolute methodological rules (read twice)

### R0. Latent question first; mechanism is the unit of understanding
For every major section, do this in order:
1. **Asked:** one line — what the author thinks they need.
2. **Unasked but decisive:** one line — the sharper question that actually gates the answer.
3. **Mechanism:** a short causal chain with equations/modules/counts, not slogans.
4. **Only then:** taxonomy, venue advice, contribution bullets.

Reject fake depth:
- bad: “Layer1 ontology / Layer2 epistemology / Layer3 research identity / Layer4 contribution grammar…”
- good: “Under fixed F2-P, swapping head→geom leaves errs≈unchanged; swapping geom→achievable changes errs by Δ; therefore the movable object is covariance-aware scoring, not learning.”

If you cannot point to a mechanism (math or controlled comparison), you do not yet have a contribution.

### R1. Distrust all secondary conclusions
Treat every HTML adjudication, markdown narrative, QA note, and “verdict” card as **biased secondary commentary**.

They may be:
- directionally useful as pointers to files, OR
- completely wrong in attribution/causal language.

**Never cite an HTML verdict as proof.**
Proof may only come from:
1. raw numeric artifacts in `03_raw_results/`,
2. equations you re-derive,
3. code that defines the estimator/scorer in `04_analysis_scripts/`,
4. external peer-reviewed / arXiv literature you retrieve.

If HTML says “HERO dead” or “theory-first”, you may test that statement, but you must show the calculation yourself.

### R2. Prefer primary data over prose
Priority order:
1. `*.json` summaries with counts/CI/ratios
2. per-frame `*.npz` / logs if needed to audit pairing or tails
3. Python scorers / bootstrap code (definitional ground truth)
4. theory HTML / proof skeleton (hypothesis only)
5. old narrative / contribution lists (contrast only; often stale)
6. PhD direction HTML in `07_` (optional context; **out of scope** for the paper claim unless you explicitly separate “this paper” vs “thesis arc”)

### R3. Math must be hard
For every candidate contribution, write the actual object:
- observation model
- interference covariance under SP
- detection/scoring statistic
- complexity order
- what is estimated vs genie
- what is identifiable from pilots alone

Soft words without equations are failures:
forbidden as standalone justification: “powerful”, “significant”, “near-optimal”, “AI-native”, “essentially”, “clearly”.

### R4. Causal attribution is mandatory (= mechanism, not label-swapping)
Any BER reduction claim must answer with a **mechanism chain**:
- reduction **relative to which exact baseline**?
- under which fixed pipeline stages?
- which intermediate quantity changed (support set / scores / gains / LLRs / decoded bits)?
- is the gain from **support refinement deployment**, **scorer**, **iteration**, or **confound**?
- paired or unpaired?
- bit-level or frame-level uncertainty?

Format preferred:
`intervention → fixed controls → changed internal variable → error-count delta → CI`

If a comparison confounds F2-P deployment with learned scoring, mark it **non-identifying**.
Do not replace missing mechanisms with extra conceptual layers.

### R5. Negative results are first-class
If learning does not beat a hand-crafted geometric score, say so.
If a mechanism hypothesis is falsified, say so.
If the only honest paper is theory/systems with learning as appendix, say so.
Do not resurrect a learning-hero narrative without new math + a concrete experiment that could overturn current numbers.

### R6. Literature is required, nostalgia is not
Search 2023–2026 (and canonical older) work on:
- AFDM channel estimation (embedded / superimposed / guard-free)
- AFDM/OTFS joint CE + detection / turbo / iterative receivers
- superimposed-pilot joint estimation-detection
- whitened/GLRT/Bayesian sparse recovery under colored interference
- model-driven deep unfolding for CE/detection
- learned support refinement / pruning / candidate scoring
- UWA double-dispersive receivers if relevant

For each closest paper:
- what it did
- overlap with this setting
- residual delta that is still open
- whether author’s current evidence actually occupies that delta

Literature claims also need mechanisms: “paper X already whitened SP interference by …” beats “this area is crowded.”

### R7. Separate three mechanism layers — not three prestige layers
Tag claims only by the mechanism they change:
- **L-theory**: mathematical identity / bound / decomposition
- **L-algorithm**: estimator/detector procedure with complexity
- **L-learning**: trainable module and its sample/compute value

These are causal categories, not a pyramid to climb. Do not mix them in one bullet. Do not invent Layer-4/5 “framing contributions” unless a mechanism changed.

---

## Bundle map (what you were given)

```
00_prompt/                         <- this file
01_adjudication_html/              <- SECONDARY, distrust
02_theory_architecture_html/       <- hypotheses / intended theory
03_raw_results/                    <- PRIMARY evidence
   gateA/ gateA_s15firm/ gateA_s20firm/ gateA_artifacts/
   mech/ selfsupp/ f2p_firm/ complexity/
04_analysis_scripts/               <- definitional code
05_old_narrative_for_contrast/     <- stale claims to attack
06_qa_and_logs/                    <- process notes, not proof
07_direction_context_optional/     <- career/PhD context only
```

### Suggested reading order
1. `04_analysis_scripts/decision_gateA.py`  
   (what white/geom/genie/achievable/covhead scorers *are*)
2. `04_analysis_scripts/decision_gateA_bootstrap.py`  
   (how CI / ratios are computed)
3. `03_raw_results/gateA_artifacts/*.json` and firm folders
4. `03_raw_results/mech/*.json` and `selfsupp/*.json`
5. `03_raw_results/f2p_firm/s0{7,8,9}/results.json`
6. `03_raw_results/complexity/*`
7. Only then open `01_adjudication_html/*` and check whether their prose matches your recalculation
8. Attack `05_old_narrative_for_contrast/NARRATIVE_REPORT.md` and `main.tex` for overclaim
9. Use `02_theory_architecture_html/*` only to recover intended Λ factorization, then re-derive

---

## System / notation you should reconstruct from code+docs

Work in the AFDM delay-Doppler sparse equivalent channel setting with superimposed pilots.

Use a clean notation section in the HTML:
- \(N\): subcarriers / DAFT size
- \(P\): physical paths
- \(\rho\): pilot power fraction
- pilot symbol / data symbol coexistence on same resources
- effective observation after DAFT
- dictionary atoms \(\phi_i\) on delay-Doppler grid (with fractional Doppler leakage if enabled)
- OMP-once support \(\mathcal{S}_0\), gains, effective \(\hat H^0\)
- outer joint loop: DA-LS gain refit + MP-BP detection
- F2-P refinement deployment knobs (if present in code): refine rounds, candidate top-M, defer-prune, protect-added
- scorer slot: maps candidates → scores used only inside refinement

### Minimum equations to re-derive (do not skip)

1. **SP observation and data interference**
   - Write the pilot-phase observation with data treated as interference.
   - Show why the interference covariance scales like \((1-\rho)\) times a channel Gram structure (state assumptions).

2. **Candidate score / posterior ratio skeleton**
   - Start from a Bayesian on/off atom model or GLRT under covariance \(C\).
   - Derive a log-score of the form
     \[
     \log\Lambda_i
     =
     \underbrace{\log\frac{\pi_i}{1-\pi_i}}_{\text{prior}}
     +
     \underbrace{f(b_i,T_i)}_{\text{evidence}}
     \]
     with
     \[
     b_i=\sigma_h^2\,\phi_i^H C^{-1}\phi_i,\quad
     T_i=\frac{|\phi_i^H C^{-1} r|^2}{\phi_i^H C^{-1}\phi_i}
     \]
     or the exact form implemented in code if different.
   - Identify the white-noise reduction \(C=\sigma^2 I\) and relate to plain MF / OMP scoring.

3. **Scorer ladder (must match code definitions)**
   Define precisely, with no handwaving:
   - `classical`: no F2-P scorer path (or baseline joint without learned refine — verify in code)
   - `geom` / pure geometric prior score
   - `white` mismatched whitening
   - `achievable` using \(\hat H^0\)-based \(C\)
   - `genie` using true \(H\)-based \(C\)
   - `head` / `covhead` learned scores
   - any `score_override` mechanism

4. **Complexity**
   - Cost of forming/applying \(C^{-1}\) or solving whitened systems versus one joint receiver outer stack.
   - Whether a learned head has asymptotic or practical runtime justification.

If code and theory HTML disagree, **code wins for “what was measured”**, theory wins only after you re-prove it.

---

## Primary questions (answer all)

### Q0. Latent question + executive reconstruction
First, in 4–6 lines, perform the redirect:
- **Asked question:** (author’s surface need: claims/innovation/contribution)
- **Unasked but decisive question:** (the real gate; write it sharply)
- **Why the unasked one is more important:** (one mechanism-level reason)

Then, in <= 12 lines:
- What is the only honest thesis statement for a paper *right now*?
- What is explicitly not a contribution?
- Is this currently a learning paper, theory paper, systems paper, or negative-result paper?
- One causal sentence of the form: `the BER-moving object is X, not Y, because ...`

### Q1. Recompute the evidence table yourself
From raw JSON (and npz if needed), rebuild tables for:
- Gate-style scorer ladder at SNR15 (and SNR20 if powered)
- ratios and CI for head vs geom, achievable vs geom, achievable vs head, covhead vs achievable
- F2-P firm multi-seed classical vs learned pipeline numbers
- ρ-sweep mechanism numbers
- integer-Doppler control
- self-suppression pool
- complexity Λ vs receiver

For each row report:
- absolute error counts or BER
- paired ratio or delta
- CI if present
- sample size (frames/bits)
- whether comparison is deployment-controlled

If a file is missing or underpowered, mark **insufficient**.

### Q2. Identifiability: what caused BER movement?
This is likely close to the latent question. Using controlled comparisons only, estimate the fraction of gain attributable to:
- joint iteration vs serial
- F2-P deployment shell
- geometric prior score
- whitened achievable score
- any residual learning beyond geom / beyond achievable

Produce a **mechanism decomposition**, not a theme decomposition:
`source → intermediate variable changed → errs/BER delta → CI/power → confound`.

Approximate fractions are OK if uncertainty and confounds are listed.
If evidence cannot separate two sources, say **entangled**, don’t invent a deeper story hierarchy.

### Q3. First-principles: what *should* be the scientific object?
Ignore author ambition. From the SP-AFDM interference structure, argue what the natural paper object is among:
- a covariance-aware detection/scoring theory under SP
- a low-complexity joint CE-detection architecture (OMP-once + gain iterations)
- a support-refinement controller
- a learned amortizer
- a negative result on shallow learned scoring

Pick one primary object and justify by **information/interference mechanism**, not fashion and not “research identity”.
Test: if you delete the object, which equation or error pathway disappears?

### Q4. Contribution triage (A/B/C/D)
Score each candidate 0–5 for novelty, evidence hardness, and venue value:

Candidates (add/kill as needed):
1. Learned head as main BER hero
2. F2-P deployment mechanism
3. OMP-once + LS/MP-BP joint recipe
4. Λ factorization / C1-style theory
5. achievable-Λ closed-form scorer
6. cov-head amortization
7. SP interference whitening mechanism (ρ dependence)
8. fractional-Doppler leakage-prior story
9. complexity-preserving claims
10. UWA-specific framing
11. Documented negative results / falsifications
12. Any delta you discover from literature gaps

Bins:
- **A**: can enter contribution list now
- **B**: enter only with narrowed wording
- **C**: ablation/appendix only
- **D**: discard or relegate to “tested-and-null”

### Q5. Closest literature delta test
After retrieval, fill:

| Claimed novelty | Closest papers | Survives? | Residual delta | Evidence level |

Be brutal. “Combination novelty” is allowed only if the combination is non-trivial and evidenced end-to-end.

### Q6. Hard claim language
Produce:
- green claims (allowed, with exact qualifiers)
- red claims (forbidden)
- yellow claims (only after missing experiment X)

Especially police:
- “learning helps because …”
- “first”
- “near-optimal”
- “significant gain from the neural module”
- “complexity-optimal”
- “self-suppression”
- “leakage provides prior”

### Q7. MVP paper blueprint (minimum non-self-contradictory paper)
Give:
- title (EN + ZH)
- one-paragraph abstract logic
- contribution bullets (3–5) with evidence pointers into `03_raw_results/...`
- section outline
- which figures/tables are mandatory
- which current headlines must be deleted
- top 5 reviewer attacks + answers
- venue recommendation under current evidence vs after +1 month experiments

### Q8. Missing experiments ranked by information value
For each missing experiment:
- hypothesis
- design (what is held fixed)
- success/fail criteria
- which claim bin it can promote/demote
- approximate effort

Must consider at least:
- LDPC/coded BER
- external published AFDM-SP / joint baseline head-to-head
- runtime on same hardware (not only MAC/Cholesky ms snippets)
- whether learning beats achievable under model mismatch / unknown stats / distribution shift
- listwise or differentiable top-K training vs BCE rank patch
- higher-hardness regimes (larger P, smaller N, stronger Doppler)

### Q9. Learning-narrative resurrection protocol
Only if mathematically plausible.
State the **necessary condition** under which a learned scorer can beat achievable-Λ.
If you cannot state such a condition, declare learning-main dead for this paper.

### Q10. Final advisor memo (one page)
Answer exactly:
0. The unasked decisive question, restated in one sentence
1. One-sentence contribution now?
2. What this is not?
3. Three hardest evidences? (each must name a mechanism, not only a %)
4. Single most dangerous overclaim still floating in old narrative?
5. Write now, or run which one experiment first?
6. If only one innovation may remain, which one?
7. One thing you deliberately did **not** over-structure, because mechanism was already clear

---

## Evidence hygiene checklist (include a section)
Explicitly audit:
- pairing integrity across scorers/seeds
- whether classical error counts match across arms when they should
- SNR20 rare-event tails / shared disaster frames
- train/test seed separation if learning is discussed
- any objective–inference mismatch (e.g., bias patch / force top-k)
- whether “learned” arm still includes F2-P shell
- whether genie uses illegal side information relative to the claim text

If hygiene fails, downgrade all dependent claims.

---

## Output format: one HTML file
Requirements:
- single file, inline CSS
- top sticky TOC with anchors
- **§0 Latent Question** immediately under the title: Asked / Unasked-decisive / Why it gates everything
- **Executive Verdict** next (no suspense writing), led by one mechanism sentence
- tables for recomputed evidence
- every major section starts with a 3-line box: `Asked → Unasked → Mechanism`
- a “Secondary reports audit” section: for each file in `01_adjudication_html/`, mark Agree / Partially agree / Reject, with counter-calculation
- a “Old narrative kill list” extracted from `05_old_narrative_for_contrast/` — kill by mechanism failure, not by taste
- contribution triage matrix (A/B/C/D) with a mandatory `mechanism chain` column
- MVP blueprint
- references with links/ids
- final advisor memo

Style:
- dense, technical, decision-oriented
- equations in MathJax or Unicode/LaTeX-ish plain HTML
- no motivational filler
- no fake-deep multi-layer frameworks unless each layer changes a measurable mechanism
- Chinese exposition OK; all formal claims also in English

Self-check before emitting HTML (fail any ⇒ revise):
- [ ] I named an unasked question sharper than “what are the contributions?”
- [ ] Every kept contribution has a causal chain to errs/BER or a proved identity
- [ ] I did not add abstract layers that do no causal work
- [ ] I would still accept this report if I were trying to reject the paper

---

## Anti-sycophancy clause
If the strongest honest conclusion is:
> “There is no learning contribution; write a theory/systems paper around SP covariance-aware scoring and OMP-once joint reception; treat neural heads as negative/null amortization evidence,”

then write exactly that.
Do not soften it to preserve the author’s previous identity as a learning paper.

If instead the data still support a narrowed learning claim, prove it with controlled deltas, not aesthetics.

Do not console the author with a more “profound” architecture of research identity when the mechanism is simply: learning ≈ geom, achievable > geom, and Λ is cheap.

---

## Start now
1. Write the latent (unasked) question in one sentence.
2. Parse code definitions of scorers and bootstrap.
3. Recompute/confirm tables from `03_raw_results`.
4. Re-derive SP + Λ math until the BER mechanism is explicit.
5. Retrieve literature for residual delta only.
6. Emit the HTML report — mechanism-clear, not hierarchy-heavy.
