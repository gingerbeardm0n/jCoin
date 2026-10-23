#!/usr/bin/env bash
# Daily snapshot of the paper state (jcoin-backup.timer). Keeps the last 14 days in
# ~jcoin/state-backups. Protects against a deleted/corrupted state.json; it does NOT
# survive loss of the VM disk (use a GCE disk snapshot schedule for that).
# Restore: stop jcoin, copy a snapshot's state.json back into /opt/jcoin/paper_state/.
set -euo pipefail

SRC=/opt/jcoin/paper_state
DEST="$HOME/state-backups"
mkdir -p "$DEST"
STAMP=$(date -u +%Y%m%dT%H%MZ)
tar -czf "$DEST/paper_state-$STAMP.tgz" -C "$SRC" --exclude=cache .
ls -1t "$DEST"/paper_state-*.tgz | tail -n +15 | xargs -r rm -f
logger -t jcoin-backup "saved $DEST/paper_state-$STAMP.tgz"
