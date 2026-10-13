#!/usr/bin/env bash
# Rebuild this read-only GPT mirror from the vault's committed AFDM subtree.
# Usage: .sync/sync.sh [vault-ref]   (default: trans/tcom-main). Does not push.
set -euo pipefail
VAULT=/Users/guoyikun/Downloads/share/claode_birain/my-vault
PREFIX=00_Inbox/AFDM-channel-estimation
REF=${1:-trans/tcom-main}
MIRROR=$(cd "$(dirname "$0")/.." && pwd)
SHA=$(git -C "$VAULT" rev-parse "$REF")

cd "$MIRROR"
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name .sync -exec rm -rf {} +
git -C "$VAULT" archive "$SHA:$PREFIX" | tar -x -C "$MIRROR"

# Agent runtime traces: not useful for reading.
rm -rf .mission .claude .codex .agents
# Binaries GPT cannot read.
find . -path ./.git -prune -o -type f \( -iname '*.npz' -o -iname '*.npy' -o -iname '*.pt' \
  -o -iname '*.pth' -o -iname '*.ckpt' -o -iname '*.mat' -o -iname '*.pkl' -o -iname '*.pickle' \
  -o -iname '*.h5' -o -iname '*.gz' -o -iname '*.tgz' -o -iname '*.zip' -o -iname '*.tar' \
  -o -iname '*.7z' -o -iname '*.fig' \) -print0 | xargs -0 rm -f
# Size cap (GitHub warns >50MB, rejects >100MB).
find . -path ./.git -prune -o -type f -size +50M -print0 | xargs -0 rm -f

cp .sync/README.gpt.md README.md
git add -A -f .
if git diff --cached --quiet; then echo "no change"; exit 0; fi
git commit -q -m "sync: vault $REF @ ${SHA:0:12}"
git log --oneline -1
