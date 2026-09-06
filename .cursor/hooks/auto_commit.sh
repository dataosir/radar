#!/usr/bin/env bash
# Auto-commit after agent session ends. Never pushes — user decides when to push.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/auto_commit.log"

ts() { date '+%Y-%m-%d %H:%M:%S'; }

log() { echo "[$(ts)] $*" >> "$LOG_FILE"; }

# Consume stdin (required by Cursor hook protocol)
cat > /dev/null

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  log "skip: not a git repository"
  exit 0
fi

if [[ -z "$(git status --porcelain)" ]]; then
  log "skip: working tree clean"
  exit 0
fi

# Stage tracked changes and new files; .gitignore still applies
git add -A

if [[ -z "$(git diff --cached --name-only)" ]]; then
  log "skip: nothing staged after git add"
  exit 0
fi

CHANGED="$(git diff --cached --name-only | head -20)"
STAT="$(git diff --cached --shortstat)"
MSG="auto: agent snapshot $(date '+%Y-%m-%d %H:%M')

${STAT}

Files:
${CHANGED}"

if git commit -m "$MSG"; then
  SHA="$(git rev-parse --short HEAD)"
  log "committed ${SHA}: ${STAT}"
else
  log "commit failed"
  exit 1
fi

exit 0
