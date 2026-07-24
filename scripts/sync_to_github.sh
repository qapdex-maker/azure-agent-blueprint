#!/usr/bin/env bash
# scripts/sync_to_github.sh — sync local blueprint -> qapdex-maker/azure-agent-blueprint
#
# Source of truth for DEVELOPMENT: /home/repo/own/Microsoft/azure-agent-blueprint
# Push target (git history):        /tmp/azure-agent-blueprint-push  (origin -> GitHub)
#
# Why two dirs: /home/repo is the NousResearch hermes-agent repo (do NOT commit
# the blueprint there). We keep an isolated, clean git repo in /tmp for GitHub.
#
# Usage:
#   bash scripts/sync_to_github.sh            # copy + commit + push (default msg)
#   bash scripts/sync_to_github.sh "msg"      # custom commit message
#   bash scripts/sync_to_github.sh --dry      # copy only, no commit/push
set -euo pipefail

SRC="/data/data/com.termux/files/home/repo/own/Microsoft/azure-agent-blueprint"
DST="$HOME/azure-agent-blueprint-push"
MSG="${1:-Update Azure Agent Blueprint (sync)}"
DRY=0
[ "${1:-}" = "--dry" ] && { DRY=1; MSG="dry-run"; }

if [ ! -d "$SRC" ]; then echo "SRC missing: $SRC" >&2; exit 1; fi
if [ ! -d "$DST/.git" ]; then echo "DST not a git repo: $DST" >&2; exit 1; fi

# 1) copy blueprint files (portable, no rsync dependency)
# remove old content except .git and .gitignore, then copy fresh
find "$DST" -mindepth 1 -maxdepth 1 ! -name '.git' ! -name '.gitignore' -exec rm -rf {} +
cp -r "$SRC/src" "$SRC/infra" "$SRC/tests" "$SRC/scripts" "$SRC/site" "$SRC/docs" "$DST/" 2>/dev/null || true
for f in README.md azure.yaml Dockerfile requirements.txt ROADMAP.md Tree.md; do
  [ -f "$SRC/$f" ] && cp "$SRC/$f" "$DST/"
done
# drop pycache
find "$DST" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

# 2) show diff
echo "[sync] git status in $DST"
git -C "$DST" status --short

if [ "$DRY" = "1" ]; then
  echo "[sync] dry-run complete (no commit/push)"
  exit 0
fi

# 3) commit + push
git -C "$DST" add -A
if git -C "$DST" diff --cached --quiet; then
  echo "[sync] no changes to commit"
  exit 0
fi
git -C "$DST" commit -q -m "$MSG"
git -C "$DST" push origin master
echo "[sync] pushed: $(git -C "$DST" rev-parse --short HEAD)"
