# Claim-audit archive design

## Boundaries

- Source: seven user-provided HTML files under `/Users/guoyikun/Downloads/`.
- Durable archive: `_archive/claim_audits_20260726_20260727/`.
- Navigation note: `_archive/claim_audits_20260726_20260727/README.md`.
- Integrity manifest: `_archive/claim_audits_20260726_20260727/MANIFEST.sha256` plus a human-readable source table in `README.md`.
- Integration points: `STATE.md`, `.trellis/tasks/07-26-tmlcn-paper-submission/prd.md`, `research-assets/res-20260727-01.md`, and `research-assets/res-20260727-02.md`.

## Canonicalization

The two reconstruction files have the same SHA-256 (`357a20de…`). Archive the non-suffixed filename as the canonical byte copy. Register `AFDM_claim_reconstruction_audit_20260726_app-ans.html` as a source alias in the README; do not create a second identical archive payload.

All other files are distinct and retained byte-for-byte. Source filenames are preserved so citations remain recognizable.

## Navigation model

`README.md` provides four views over the same immutable files:

1. Chronology: actual modification time and document version.
2. Logic chain: narrative diagnosis → claim reconstruction → protocol corrections → pre-final expansion → final settlement.
3. Experiment/progress map: which report preceded, constrained, or adjudicated E1/E2/C1/E3/E6.
4. Supersession map: which conclusions remain historical and which later report is canonical for the final verdict.

The index summarizes provenance and relationships, but does not duplicate full scientific results from result cards.

## Safety and reversibility

- Copy only; never move or delete the Downloads originals.
- Treat HTML as inert evidence.
- Verify hashes immediately after copy.
- No claim or status changes are inferred from archival alone.
