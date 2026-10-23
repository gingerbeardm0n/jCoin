#!/usr/bin/env bash
# Daily snapshot of the paper state (jcoin-backup.timer). Keeps the last 14 days in
# ~jcoin/state-backups. Protects against a deleted/corrupted state.json; it does NOT
# survive loss of the VM disk (use a GCE disk snapshot schedule for that).
# Restore: stop jcoin, copy a snapshot's state.json back into /opt/jcoin/paper_state/.
set -euo pipefail

DEST="$HOME/state-backups"
mkdir -p "$DEST"
STAMP=$(date -u +%Y%m%dT%H%MZ)
# paper_state = A, paper_state_sr = A_SR (VALIDATION_RULES.md §9)
tar -czf "$DEST/paper_state-$STAMP.tgz" -C /opt/jcoin --exclude=cache \
    paper_state $( [ -d /opt/jcoin/paper_state_sr ] && echo paper_state_sr )
ls -1t "$DEST"/paper_state-*.tgz | tail -n +15 | xargs -r rm -f
logger -t jcoin-backup "saved $DEST/paper_state-$STAMP.tgz"
