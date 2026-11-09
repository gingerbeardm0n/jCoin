#!/usr/bin/env bash
# Daily snapshot of the paper state (jcoin-backup.timer). Keeps the last 14 days in
# ~jcoin/state-backups. Protects against a deleted/corrupted state.json; it does NOT
# survive loss of the VM disk (use a GCE disk snapshot schedule for that).
# Restore: stop jcoin, copy a snapshot's state.json back into /opt/jcoin/paper_state/.
set -euo pipefail

DEST="$HOME/state-backups"
mkdir -p "$DEST"
STAMP=$(date -u +%Y%m%dT%H%MZ)
# paper_state = A, paper_state_sr = A_SR (§9), paper_state_br = A_BR (§11)
EXTRA=""
for d in paper_state_sr paper_state_br; do [ -d "/opt/jcoin/$d" ] && EXTRA="$EXTRA $d"; done
tar -czf "$DEST/paper_state-$STAMP.tgz" -C /opt/jcoin --exclude=cache paper_state $EXTRA
ls -1t "$DEST"/paper_state-*.tgz | tail -n +15 | xargs -r rm -f
logger -t jcoin-backup "saved $DEST/paper_state-$STAMP.tgz"
