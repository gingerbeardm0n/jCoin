#!/usr/bin/env bash
# Auto-update: pull from GitHub, run tests, switch only if they pass.
# Called by a systemd timer (jcoin-update.timer) every hour before the daemon tick.
# If tests fail, the old code stays in place and the daemon runs on what worked last.

set -euo pipefail

REPO=/opt/jcoin
VENV="$REPO/.venv/bin"
LOG_TAG="jcoin-update"

cd "$REPO"

# Fetch latest
git fetch origin main --quiet 2>&1 | logger -t "$LOG_TAG" || true

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    logger -t "$LOG_TAG" "up to date ($LOCAL)"
    exit 0
fi

logger -t "$LOG_TAG" "update available: $LOCAL -> $REMOTE"

# Pull
git merge origin/main --ff-only --quiet 2>&1 | logger -t "$LOG_TAG"
MERGE_RC=$?

if [ $MERGE_RC -ne 0 ]; then
    logger -t "$LOG_TAG" "merge failed (non-ff), reverting"
    git reset --hard "$LOCAL" 2>&1 | logger -t "$LOG_TAG"
    exit 1
fi

# Install any new deps
"$VENV/pip" install -q -e . 2>&1 | logger -t "$LOG_TAG" || true

# Run tests
if "$VENV/python" -m pytest tests/ -q --tb=short 2>&1 | logger -t "$LOG_TAG"; then
    logger -t "$LOG_TAG" "tests passed on $REMOTE — update live"
    # Restart the daemon so it picks up new code
    sudo systemctl restart jcoin 2>&1 | logger -t "$LOG_TAG" || true
else
    logger -t "$LOG_TAG" "tests FAILED — rolling back to $LOCAL"
    git reset --hard "$LOCAL" 2>&1 | logger -t "$LOG_TAG"
    "$VENV/pip" install -q -e . 2>&1 | logger -t "$LOG_TAG" || true
    exit 1
fi
