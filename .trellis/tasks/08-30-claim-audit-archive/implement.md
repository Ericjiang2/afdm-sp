# Claim-audit archive implementation plan

1. Create `_archive/claim_audits_20260726_20260727/` and copy the six unique HTML payloads byte-for-byte.
2. Generate `MANIFEST.sha256` using archive-relative filenames; compare every archived hash with the source inventory.
3. Write the Obsidian-compatible `README.md` with provenance, chronology, logic chain, experiment/progress mapping, supersession, and links to live project truth.
4. Replace temporary Downloads references in `STATE.md` and the paper parent PRD with stable archive wikilinks; add backward/forward links from E1/E2 cards where relevant.
5. Validate:
   - source/archive SHA-256 equality;
   - all seven source names represented, with one duplicate alias;
   - every linked local target exists;
   - `python3 ./.trellis/scripts/task.py validate claim-audit-archive`;
   - `git diff --check` and scoped diff review.
6. Run Trellis quality check and update spec only if a reusable archival rule was discovered; otherwise record that no spec change is needed.

## Rollback

Remove only the new archive directory and revert the scoped link additions. Source files under Downloads are never modified.
