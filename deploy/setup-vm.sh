#!/usr/bin/env bash
# One-time provisioning for a fresh GCP e2-micro VM (Debian 12). Run with sudo after
# SSHing in. See ../DEPLOY_GCP.md for the steps before and after this script.
#
# Assumes the `jcoin` service user and its deploy key already exist and the public
# key has been added to GitHub as a read-only deploy key (DEPLOY_GCP.md step 3).
# The clone runs AS jcoin so it uses jcoin's key (2026-10-14: the old version cloned
# as root, which has no deploy key, so the clone failed).
set -euo pipefail

REPO_URL="git@github.com:gingerbeardm0n/jCoin.git"
APP_DIR="/opt/jcoin"

echo "== system packages =="
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git

echo "== swap (e2-micro has ~1GB RAM; polars/duckdb can spike) =="
if [ ! -f /swapfile ]; then
    fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "== service user =="
id -u jcoin &>/dev/null || useradd --system --create-home --shell /usr/sbin/nologin jcoin

echo "== app dir + clone (as jcoin, using its deploy key) =="
mkdir -p "$APP_DIR" && chown jcoin:jcoin "$APP_DIR"
if [ ! -d "$APP_DIR/.git" ]; then
    sudo -u jcoin env GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new" \
        git clone "$REPO_URL" "$APP_DIR"
else
    echo "  $APP_DIR already cloned (update: cd $APP_DIR && sudo -u jcoin git pull)"
fi

echo "== python venv + deps =="
sudo -u jcoin python3 -m venv "$APP_DIR/.venv"
sudo -u jcoin "$APP_DIR/.venv/bin/pip" install --quiet --upgrade pip
sudo -u jcoin "$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"
sudo -u jcoin mkdir -p "$APP_DIR/logs" "$APP_DIR/paper_state"

if [ ! -f "$APP_DIR/.env" ]; then
    sudo -u jcoin touch "$APP_DIR/.env" && chmod 600 "$APP_DIR/.env"
    echo "== created empty $APP_DIR/.env (add JCOIN_PING_URL=... later) =="
fi

echo "== systemd service =="
cp "$APP_DIR/deploy/jcoin.service" /etc/systemd/system/jcoin.service
systemctl daemon-reload
systemctl enable jcoin

echo "== done. Copy paper_state in if migrating, then: sudo systemctl start jcoin =="
