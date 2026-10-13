#!/usr/bin/env bash
# Rebuild the read-only GPT mirror (bare repo.git) from the vault's committed AFDM subtree, then push.
# Usage: sync.sh [vault-ref] [--no-push]   (default ref: trans/tcom-main)
# Exports into a temp dir that is deleted on exit; only repo.git persists.
set -euo pipefail
VAULT=/Users/guoyikun/Downloads/share/claode_birain/my-vault
PREFIX=00_Inbox/AFDM-channel-estimation
REF=trans/tcom-main; PUSH=1
for a in "$@"; do case $a in --no-push) PUSH=0 ;; *) REF=$a ;; esac; done
MIRROR=$(cd "$(dirname "$0")" && pwd)
SHA=$(git -C "$VAULT" rev-parse "$REF")

WT=$(mktemp -d); trap 'rm -rf "$WT"' EXIT
m() { git --git-dir="$MIRROR/repo.git" --work-tree="$WT" "$@"; }
git -C "$VAULT" archive "$SHA:$PREFIX" | tar -x -C "$WT"

cd "$WT"
# Agent runtime traces: not useful for reading. Keep .mission task CSVs (linked from STATE.md).
rm -rf .claude .codex .agents
[ -d .mission ] && find .mission -type f ! -name '*.csv' -delete && find .mission -type d -empty -delete
# Binaries GPT cannot read.
find . -type f \( -iname '*.npz' -o -iname '*.npy' -o -iname '*.pt' -o -iname '*.pth' \
  -o -iname '*.ckpt' -o -iname '*.mat' -o -iname '*.pkl' -o -iname '*.pickle' -o -iname '*.h5' \
  -o -iname '*.gz' -o -iname '*.tgz' -o -iname '*.zip' -o -iname '*.tar' -o -iname '*.7z' \
  -o -iname '*.fig' \) -print0 | xargs -0 rm -f
# Size cap (GitHub warns >50MB, rejects >100MB).
find . -type f -size +50M -print0 | xargs -0 rm -f

cp "$MIRROR/README.gpt.md" README.md
mkdir -p .sync && cp "$MIRROR/sync.sh" "$MIRROR/README.gpt.md" .sync/
m add -A -f .
if m diff --cached --quiet; then echo "no change"; else
  m commit -q -m "sync: vault $REF @ ${SHA:0:12}" \
    -m "Read-only GPT mirror of $PREFIX (committed state)." \
    -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
  m log --oneline -1
fi
if [ "$PUSH" = 1 ]; then m push origin main; fi
