# Implementation order (v2)

Follow the ordered table in the canonical Mission plan and the single CSV: L00, L01, L02, L10, L11, L03, L04, L12, L13, L14, L15, L17, L18, L05, L06, L16, L07, L08, L09, REVIEW-01. L16 research notes accumulate after each numerical result.

Preserve completed LLR calls; finish their analysis/review/Git first. For each new numerical stage, freeze the contract, test the implementation, quote real CPU engineering cost, then admit development. Continuous Doppler estimation is excluded. CPU/GPU-only and heavy deferrals require explicit evidence and next conditions, never false completion.

Validation: targeted tests → syntax/static checks → real engineering replay → approved development → raw arrays and independent statistics. Main session owns CSV, task/spec updates, dispatch, commits and wrap-up. All implementation and review stay in the main session under the latest user instruction; no repeated bootstrap.

Latest user override: implementation, validation and final review stay in the main session. Do not spawn agents or independent reviewer sessions. Label self-review honestly. CPU first; GPU-only work deferred.
