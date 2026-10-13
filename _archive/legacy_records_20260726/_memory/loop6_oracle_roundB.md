My blunt read:

**You have a real engineering milestone, but not a reviewer-safe win yet.**
C1 looks like the *right* fix mechanically: it preserves identity at init, targets the off-support residual signal your probe said was alive, uses hard-mode validation/checkpointing, and the best checkpoint was chosen with the gate-aware score rather than mean-Δ. The pre-diagnostic also supports the premise: off-support correlation dominates on-support residual correlation and gets stronger with SNR, while `|c_active|` is effectively dead.  

### 1) Gate verdict

**Round-2 gate, as you restated it here:** **yes, passed — narrowly.**
Your own Round-2 rubric says gate #1 is line dominance at 10/15/20 dB, with ties allowed at low SNR and strict below-classical behavior at high SNR. On the machine-readable audit, `line_dominance=true` at 10, 15, and 20 dB, `stat_sig=false` at all three, and `warnings=[]`; the plotter’s audit logic explicitly defines the gate on 10/15/20 and reports no waterfall warnings.    

**But under the stricter Phase-A wording:** **no, not passed.**
The earlier rubric required learned hard-BER `<` classical hard-BER at 10/15/20 **with 95% Wilson CI separation**. Your structured JSON says `stat_sig=false` at 10, 15, and 20 dB, so that stricter version is not satisfied.  

So the honest one-line verdict is:

**Engineering gate:** pass.
**Submission-grade statistical gate:** not yet.

At 20 dB, the learned arm is better by 39 errors on 1.024M bits, about −1.55% relative, but still inside the current Wilson overlap. That is a *promising trend*, not a defensible “win” against a tough reviewer.  

One more important point: your significance check is conservative because the eval is paired, but the plotter is treating the two BERs with separate Wilson intervals and declaring significance only if `learned_hi < classical_lo`. That ignores pairing information. So I would not say the 20 dB gain is false; I would say it is **not yet demonstrated with the current test**.   

Also, I would fix one thing before anyone presents this: **the prose claim that 25 dB is CI-separated conflicts with the machine-readable JSON.** The briefing says “YES” with learned hi `6.20e-4 <` classical lo `6.29e-4`, but the JSON records classical CI `[5.89e-4, 7.16e-4]` and learned CI `[5.42e-4, 6.65e-4]`, which still overlap. I would trust the JSON/plotter over the prose table unless you find a transcript error.   

### 2) N=256 follow-up

**Yes, acceptable — if you frame it as a regime study, not a rescue mission.**
Your own briefing already states the right interpretation: smaller `N` means weaker classical DA-LS, more headroom, higher BER, much cheaper training/eval, and a real risk of cherry-pick if reported alone. That is exactly the right caveat. 

I would **not** call N=256 misleading by itself. I would call it misleading only if:

* N=256 is shown without N=1024,
* only relative gain is shown,
* or the paper text implies “general improvement” instead of “improvement grows as classical headroom grows.”

The clean reporting format is:

* **one main figure with two panels:** N=256 and N=1024, same SNR axis, same plotting style, same perfect-CSI bound, same C1 recipe;
* **one small table** for 10/15/20/25 giving absolute BER, absolute ΔBER, relative Δ%, and bit counts for both N values;
* and one sentence upfront saying **N=1024 is the primary high-capacity regime, N=256 is a lower-observation stress regime.**

If N=256 wins clearly and N=1024 only trends positive, that is still a publishable story, but the claim becomes:
**“C1 helps most when the classical estimator is observation-limited.”**
That is valid. It is not the same as “C1 dominates classical everywhere.”

### 3) P=6 / P=10: transfer or retrain?

**For science:** transfer-eval first.
**For headline numbers:** retrain per P.

Why I’m splitting it this way:

* The probe evidence says the off-support signal exists across P values, so a transfer check is worth doing and is very cheap. 
* But P changes the operating regime materially. If you want to claim performance at P=6 or P=10, a reviewer can reasonably ask for a checkpoint trained in that regime.

So my recommendation is:

* **Immediate next diagnostic:** transfer-eval the P=8 checkpoint at P=6 and P=10.
* **If one of them looks promising and you want to show it in a main figure:** retrain for that P.

I would not make a “generalizes across P” claim from transfer-only. I *would* use transfer-only as a robustness sanity check.

### 4) Score

**7/10 — almost.**

Why not higher:

* strong mechanism diagnosis,
* correct head redesign,
* correct hard-eval checkpointing,
* identity preserved,
* sane waterfall with no pathologies,
* line dominance at the gate SNRs.  

Why not lower:

* the effect at 20 dB is still too small for a strong claim under your current CI test,
* the 25 dB prose/JSON discrepancy is a red flag,
* and the evidence still reads as “promising trend” rather than “settled result.”  

So the readiness verdict is **almost**.

### 5) The single next experiment I would prioritize

**Rerun the N=1024, P=8 hard paired eval at 20 and 25 dB, but log paired discordant outcomes and analyze the paired difference directly.**

That is the highest-value next step because it resolves the only question that actually matters right now:
**is the current high-SNR gain real, or just too small/noisy to call?**

Concretely:

* same best C1 checkpoint,
* same classical arm,
* same hard-decision mode,
* only SNR 20 and 25 dB,
* log per-frame or per-bit disagreement counts between classical and learned,
* report both the usual Wilson bands **and** a paired significance result.

That experiment does three things at once:

1. settles the 20 dB claim,
2. resolves the 25 dB discrepancy,
3. tells you whether scaling to N=256 is a story-expansion or a rescue attempt.

If that paired test still comes back weak at N=1024, then move to the matched **N=256 + N=1024 two-panel regime study** and frame the story honestly as headroom-dependent.

So the brutally honest summary is:

**Do not oversell the −1.55% at 20 dB.**
Call this a **narrow engineering pass, not yet a statistically defensible win**.
And fix the 25 dB CI inconsistency before this result leaves the room.
