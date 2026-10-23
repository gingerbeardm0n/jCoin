#!/usr/bin/env bash
# Hourly auto-update (jcoin-update.timer): test origin/main in a scratch copy, and only
# if the tests pass fast-forward the live tree and restart the daemon. The live tree is
# never touched by an untested commit. A commit that fails is remembered and not
# retried; failures send a /fail ping to JCOIN_PING_URL (loaded from .env by the unit).
#
# Not for live trading: once real keys are on this VM, disable this timer and deploy
# manually (see AUDIT_2026-10-23.md item 10).

set -uo pipefail

REPO=/opt/jcoin
VENV="$REPO/.venv/bin"
TAG=jcoin-update
BAD_FILE="$HOME/.jcoin_update_bad_sha"

log() { logger -t "$TAG" -- "$*"; }
fail() {
    log "FAILED: $*"
    [ -n "${JCOIN_PING_URL:-}" ] && curl -fsS -m 10 "$JCOIN_PING_URL/fail" >/dev/null 2>&1
    exit 1
}

cd "$REPO" || fail "no repo at $REPO"

git fetch --quiet origin main 2>&1 | logger -t "$TAG" || fail "git fetch"
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    log "up to date ($LOCAL)"
    exit 0
fi
if [ -f "$BAD_FILE" ] && [ "$(cat "$BAD_FILE")" = "$REMOTE" ]; then
    log "skip $REMOTE (already failed tests; waiting for a new commit)"
    exit 0
fi
if ! git merge-base --is-ancestor "$LOCAL" "$REMOTE"; then
    echo "$REMOTE" > "$BAD_FILE"
    fail "origin/main $REMOTE is not a fast-forward of $LOCAL"
fi
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    fail "live tree has local modifications; refusing to update ($(git status --porcelain --untracked-files=no | tr '\n' ' '))"
fi

log "update available: $LOCAL -> $REMOTE; testing in scratch copy"
SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT
git archive "$REMOTE" | tar -x -C "$SCRATCH" || fail "git archive $REMOTE"

# Requirements are installed into the shared venv before testing (additive; a failed
# test run leaves extra packages installed but the old code still running).
"$VENV/pip" install -q -r "$SCRATCH/requirements.txt" 2>&1 | logger -t "$TAG" \
    || { echo "$REMOTE" > "$BAD_FILE"; fail "pip install -r requirements.txt for $REMOTE"; }

if (cd "$SCRATCH" && timeout 600 "$VENV/python" -m pytest tests/ -q --tb=short -p no:cacheprovider) \
        2>&1 | logger -t "$TAG"; then
    log "tests passed on $REMOTE"
else
    echo "$REMOTE" > "$BAD_FILE"
    fail "tests failed on $REMOTE; live tree left at $LOCAL"
fi

git merge --ff-only --quiet "$REMOTE" 2>&1 | logger -t "$TAG" || fail "ff-merge to $REMOTE"
rm -f "$BAD_FILE"
sudo systemctl restart jcoin 2>&1 | logger -t "$TAG" || fail "restart jcoin after update to $REMOTE"
log "update live: $REMOTE"
