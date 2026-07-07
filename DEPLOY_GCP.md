# Deploying jCoin on Google Cloud (Always Free e2-micro)

Chosen over Render specifically because e2-micro's Always Free tier includes a real,
permanent persistent disk and no idle-timeout/spin-down — `jcoin/live/daemon.py` runs
completely unchanged, no HTTP endpoint or external database rewrite needed (unlike
Render's free tier). `render.yaml` stays in the repo as a documented paid alternative,
unused for now.

**Steps 1-2 are yours** (account/billing, can't be done for you). Everything after
that is copy-paste.

---

## 1. Create the VM

Easiest path: no local install needed — use **Cloud Shell** (a terminal built into the
GCP Console, click the `>_` icon top-right at [console.cloud.google.com](https://console.cloud.google.com)).

```bash
gcloud compute instances create jcoin-bot \
  --zone=us-central1-a \
  --machine-type=e2-micro \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --boot-disk-size=30GB \
  --boot-disk-type=pd-standard
```

`us-central1` (along with `us-west1`/`us-east1`) and `e2-micro` + a 30GB standard disk
are the specific combination that stays inside the Always Free limits — changing zone
or machine type may start incurring cost. Double check the current limits at
[cloud.google.com/free](https://cloud.google.com/free) before creating, since these
terms do shift (Oracle just cut theirs in half this year).

## 2. SSH in

From Cloud Shell (or the Console — VM instances page has a "SSH" button that opens a
browser terminal, no key setup needed):

```bash
gcloud compute ssh jcoin-bot --zone=us-central1-a
```

## 3. Give the VM read-only access to the repo (deploy key)

The repo is private, so the VM needs its own key — never reuse your personal one.

```bash
ssh-keygen -t ed25519 -C "jcoin-vm" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub
```

Copy that output. On GitHub: repo → **Settings → Deploy keys → Add deploy key** →
paste it, leave "Allow write access" **unchecked** (read-only — this key can never
push, only pull).

## 4. Run the setup script

```bash
sudo apt-get install -y git
git clone git@github.com:gingerbeardm0n/jCoin.git /tmp/jcoin-bootstrap
sudo bash /tmp/jcoin-bootstrap/deploy/setup-vm.sh
```

(The script re-clones properly into `/opt/jcoin` as the service user — the `/tmp`
clone above is just to get `setup-vm.sh` itself onto the box first.)

## 5. Add your secrets (never committed, created by hand)

```bash
sudo nano /opt/jcoin/.env
```

```
KRAKEN_FUTURES_KEY=your-demo-or-live-key
KRAKEN_FUTURES_SECRET=your-demo-or-live-secret
JCOIN_PING_URL=https://hc-ping.com/your-check-id-here
```

Use the **same** `JCOIN_PING_URL` you already set up for the Render blueprint — the
heartbeat monitoring doesn't care which host is pinging it.

`JCOIN_STATE_DIR` is deliberately **not** set here — unlike Render, this VM's whole
disk is persistent by default, so the daemon's normal `paper_state/`/`kraken_state/`
paths under `/opt/jcoin` already survive reboots with no extra config.

```bash
sudo chown jcoin:jcoin /opt/jcoin/.env
sudo chmod 600 /opt/jcoin/.env
```

## 6. Start it

```bash
sudo systemctl start jcoin
sudo systemctl status jcoin        # should show "active (running)"
tail -f /opt/jcoin/logs/daemon.log # watch it tick
```

`Restart=always` in the systemd unit means: VM reboots, process crashes, anything —
it comes back on its own. No manual restart, no laptop involved.

## 7. Updating code later

```bash
gcloud compute ssh jcoin-bot --zone=us-central1-a
cd /opt/jcoin && sudo -u jcoin git pull
sudo -u jcoin .venv/bin/pip install -r requirements.txt   # only if deps changed
sudo systemctl restart jcoin
```

## 8. When ready for real Kraken trading (not paper)

Edit `/etc/systemd/system/jcoin.service`, change `--mode paper` to `--mode kraken`
(or `both` to run both side by side), then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart jcoin
```
