# Diagram Request — BEng FYP Thesis Block Diagrams (bitmap / web AI version)

Use this prompt when asking a web AI image generator (ChatGPT with DALL-E / Imagen, Midjourney, Napkin.ai, Gemini with Imagen, etc.) to render the two block diagrams for the thesis. **Preferred path is still TikZ** (see the LaTeX-request variant at the bottom of this file); use this bitmap brief only when the AI cannot output vector code.

⚠ **Bitmap AI caveat**: current image-gen models frequently garble technical text ("1,041 params" → "1041 prms", etc.). After you receive the bitmap, **zoom in and verify every number and every math symbol manually** before putting it into the thesis. If any label is wrong, either regenerate or overlay corrected text in Inkscape / Figma / Keynote.

---

## Files to upload along with this prompt

Upload these 4 files (they sit in `paper/` of the repo):
1. `sections/Section2.tex` — contains Algorithm 1 (the classical joint receiver) and §2.6 the learned head specification
2. `sections/Section1.tex` — symbol conventions and contribution context
3. `math_commands.tex` — all custom macros (`\Heff`, `\Nsub`, `\rhop`, `\kleak`, `\Ppath`, `\ClassicalJoint`, `\LearnedHead`, etc.)
4. `main.tex` — thesis preamble (shows font = Times/mathptmx, geometry = 6em margins on A4, 12pt, `\onehalfspacing`)

You may optionally also attach the current `paper/oracle_io/new_loop/main_with_tikz_head.pdf` so the model can see the current draft and the existing TikZ version of Figure B.

---

## Prompt — Figure A (Classical Joint Receiver) + Figure B (Learned Head)

Generate two publication-quality block diagrams for a UoG/UESTC BEng Final Year Project thesis on an AFDM-SP channel estimation and data detection receiver. Output **two separate bitmaps at 300 DPI, 16:9 landscape layout each**, sized so that at 16 cm print width the smallest text is still legible (approx. 8 pt equivalent). Follow the style and content specifications below exactly. **Do not invent extra blocks, do not add decorative icons, do not include cartoon underwater / acoustic / ocean imagery — this is a technical signal-processing diagram for an engineering thesis, not a marketing illustration.**

### Global style — BOTH figures

- **Background**: pure white (#FFFFFF). No gradient, no drop shadow, no paper texture.
- **Palette**: monochrome grayscale + a single accent colour. Use:
  - black `#000000` for all strokes and arrows
  - light gray `#EEEEEE` for the fill of classical / non-learned blocks
  - muted blue `#D8E4F3` for the fill of learned-MLP blocks (pair-encoder, scorer, final ranker)
  - slightly darker blue `#B8CCE8` for the final deployment (top-K-add ranker) block to visually distinguish deployment from training stages
- **Block shape**: rounded rectangles, 1 pt stroke, 3 pt corner radius. Minimum padding 6 pt inside each block.
- **Typography**: serif body (Times-Roman / STIX-like), italic for parameter annotations, regular weight for all other labels. Math symbols rendered properly ($\mathbb{R}^{16}$, $\mathbf{h}$, $\hat{\mathbf{x}}_d$, subscripts like $P_{\text{path}}, k_{\text{leak}}, \gamma_h, \tau_h, \rho_p, T_{\text{out}}, T_{\text{mp}}, K_{\text{add}}, \Phi, \hat{S}$). No emojis, no flourishes.
- **Arrows**: solid, `{Stealth}` style arrowheads, 1 pt line weight. Directional — every arrow must be unambiguous about which block feeds which.
- **Loop arrow** (only in Figure A): dashed 0.75 pt line, with a small "for $t = 1, \dots, T_{\text{out}} = 5$" label hugging the curve.
- **No colour gradients, no 3D bevels, no transparent overlays.**

---

### Figure A — Classical Joint OMP-once + Inner LS/MP-BP Receiver

This visualises Algorithm 1 of the thesis. Laid out top-to-bottom (portrait flow inside a landscape frame is fine) with one centred vertical chain plus a loop-back arrow for the outer iteration:

1. **Input block** (top): label = "`input`"; body = "chirp-domain received $\mathbf{y} \in \mathbb{C}^{N_{\text{sub}}}$, Zadoff-Chu pilot $\mathbf{x}_p$ (root $r = 7$), dictionary $\Phi \in \mathbb{C}^{N_{\text{sub}} \times Q}$, pilot fraction $\rho_p = 0.5$"

2. **OMP-once** block: label "OMP-once"; body "target sparsity $P_{\text{path}} = 8$ → physical support $\hat{S}^{(0)}$, initial gains $\hat{\mathbf{h}}^{(0)}$"

3. **LMMSE init** block: "LMMSE init on $\hat{S}^{(0)}$ → initial data estimate $\hat{\mathbf{x}}_d^{(0)}$"

4. **Outer-loop dashed rectangle** enclosing the following four sub-blocks, with a small label "for $t = 1, \dots, T_{\text{out}} = 5$" in the top-right corner of the rectangle:

   4a. **Data-cancellation residual**: "$\mathbf{r}^{(t)} = \mathbf{y} - \sqrt{1 - \rho_p}\, \mathbf{H}_{\text{eff}}(\hat{\mathbf{h}}^{(t-1)})\, \hat{\mathbf{x}}_d^{(t-1)}$"

   4b. **Damped DA-LS refit** (learned-blue fill optional — this is classical so keep gray): "$\hat{\mathbf{h}}^{(t)} = (1 - \gamma_h)\hat{\mathbf{h}}^{(t-1)} + \gamma_h \Phi_{\hat{S}}^{\dagger} \mathbf{r}^{(t)}$, with $\gamma_h = 0.7$"

   4c. **Sparse MP-BP detection**: "Dirichlet-expanded virtual-tap factor graph, $k_{\text{leak}} = 2$ (5 virtual taps per path), inner iterations $T_{\text{mp}} = 20$, MP damping 0.5 → $\hat{\mathbf{x}}_d^{(t)}$, per-symbol variance $\sigma_{d,i}^2$"

   4d. **Adaptive $\sigma^2$ update + prune**: "threshold $\tau_h = 10^{-2} \cdot \max|\hat{h}|$, always retain top-$P_{\text{path}}$"

   A dashed arrow loops from block 4d back to block 4a with the label "next outer iteration".

5. **Final output block**: "QPSK hard-decision demap → $\hat{\mathbf{x}}_d$ (bit stream)"

**Side annotation — small box in the bottom-right corner** of the figure, titled "key hyperparameters", listing:
- $P_{\text{path}} = 8$, $k_{\text{leak}} = 2$
- $T_{\text{out}} = 5$, $T_{\text{mp}} = 20$
- $\gamma_h = 0.7$, $\tau_h = 10^{-2} \max|\hat{h}|$
- $\rho_p = 0.5$

**Branch-out to learned head** (small): a short dotted line from block 4a/4b going OUT to a tiny outlined rectangle labelled "learned head — see Fig. B, invoked twice at $t = 0$". Do not render Figure B contents here; this is just a visual cross-reference.

**Caption line (to appear below the bitmap)**: "Classical joint OMP-once + inner LS/MP-BP receiver (Algorithm 1)."

---

### Figure B — C2-rel F2-P Learned Support-Refinement Head

Laid out as two parallel input streams at the top that merge into a single vertical chain at the bottom. **Blue fill** for the two MLP blocks and for the final deployment ranker; gray fill for everything else.

**Top row — two side-by-side input blocks**:

- **Left** (gray): "self-feature $\mathbf{u}_i \in \mathbb{R}^{7}$"
  - Small italic annotation underneath, 1 line, 6 pt: "components: $\log|\Phi_i^H \mathbf{r}|$, margin-to-weakest-active, norm. delay, norm. Doppler, residual proj. norm, rank, leak-neighbour flag"

- **Right** (gray): "pair feature $\mathbf{v}_{i,s} \in \mathbb{R}^{6}$"
  - Small italic annotation underneath: "components: $l_i - l_s$, $k_i - k_s$, $\log|\hat{h}_s|$, $|\Phi_i^H \Phi_s|$, $\|(\Delta l, \Delta k)\| / (l_{\max} + 2 k_{\max})$, $|\hat{h}_s| / \max_{s'} |\hat{h}_{s'}|$"

**Pipeline from the right (pair) input, flowing downward**:

- **Pair encoder MLP** (blue fill): header "pair encoder MLP", body "$\mathbb{R}^{6} \to \mathbb{R}^{16} \to \mathbb{R}^{16}$", italic footer "384 params"
- **Order-invariant pool**: header "order-invariant pool", body "concat$(\max_{s}, \text{mean}_{s}) \Rightarrow \mathbb{R}^{32}$"

**Merge node** (small circle with $\oplus$ inside), positioned centrally below and between the two input streams — receives the self-feature $\mathbf{u}_i$ from the left and the 32-D pool output from the right.

**Central chain below the merge, going downward**:

- **$\boldsymbol{\phi}_i \in \mathbb{R}^{39}$** (gray, small)
- **Scorer MLP** (blue fill): header "scorer MLP", body "$\mathbb{R}^{39} \to \mathbb{R}^{16} \to \mathbb{R}^{1}$", italic footer "657 params"
- **logit $s_i$** (gray)
- **Deterministic top-$K_{\text{add}}$ ranker** (darker blue fill): header "top-$K_{\text{add}}$ ranker", italic footer "ranking-only deployment"

**Bottom banner**: italic one-line annotation "total trainable parameters: $384 + 657 = 1\,041$".

**Caption**: "C2-rel F2-P learned support-refinement head. Pair encoder (384 params) + order-invariant pooling + scorer MLP (657 params) deployed as a deterministic top-$K_{\text{add}}$ ranker."

---

### Self-check before you return the images

1. Every blue block has either "384 params" or "657 params" correctly italicised under the MLP description. Neither count is merged, split, or rounded.
2. The $\mathbb{R}^{6} \to \mathbb{R}^{16} \to \mathbb{R}^{16}$ and $\mathbb{R}^{39} \to \mathbb{R}^{16} \to \mathbb{R}^{1}$ dimensions appear verbatim with the double-struck "R" symbol rendered correctly (or a reasonable substitute such as "R^6 → R^16 → R^16" if math font is unavailable — do NOT write "R6", "R 16" or "R^{16,16}").
3. In Figure A, the dashed outer-loop rectangle cleanly encloses exactly four sub-blocks and has the "for $t = 1, \dots, T_{\text{out}} = 5$" label.
4. In Figure A, the data-cancellation residual and DA-LS equations are readable at 16 cm width without zooming in beyond 100%.
5. No block has an unintended extra label, gradient, shadow, underline, or underline-like underline.
6. Both figures have the same stroke weight, font family, corner radius, and colour palette.

If any of the checks fail, redraw rather than return an incorrect bitmap.

---

## Alternative — LaTeX / TikZ prompt (preferred; reproduces the current in-thesis figure)

The thesis already ships a TikZ version of Figure B at `fig:head_arch` in `sections/Section2.tex`. If you want the web AI to produce **editable TikZ source code** instead of a bitmap (recommended for print-quality output), replace the two "Figure A / Figure B" specifications above with the following one-liner:

> "Produce both figures as TikZ LaTeX source (not as bitmap images). Only use `\usepackage{tikz}` and `\usetikzlibrary{arrows.meta, positioning, calc, shapes.geometric, fit, backgrounds}`. Wrap each figure in `\begin{figure}[t] \centering \resizebox{\linewidth}{!}{\begin{tikzpicture} ... \end{tikzpicture}} \caption{...} \label{fig:classical_joint_arch}` / `\label{fig:head_arch}`, matching the style rules (serif font, gray/blue accent palette, rounded 3 pt corners, 1 pt strokes, Stealth arrowheads). Return **only** the LaTeX code — no prose commentary. Preserve all math symbols, parameter counts, and data-flow arrows exactly as specified above."

This produces editable vector source that compiles directly into `main.tex` alongside the existing TikZ figure — no bitmap workflow required.
