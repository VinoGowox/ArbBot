# VPS Setup + Auto Deploy Commands (Scanner + Dashboard)

Dokumen ini berisi command lengkap dari nol sampai production:
- Setup VPS Ubuntu
- Jalankan scanner timer + dashboard service
- Setup Nginx reverse proxy + basic auth
- Setup GitHub Actions agar setiap push ke `main` auto-deploy ke VPS

## 0) Variabel yang dipakai

Ganti value sesuai server Anda sebelum eksekusi.

```bash
export APP_USER="arbbot"
export APP_DIR="/opt/interexchange-arbitrage/ArbBot"
export BASE_DIR="/opt/interexchange-arbitrage"
export REPO_URL="https://github.com/VinoGowox/ArbBot.git"
export BRANCH="main"
export DOMAIN_OR_IP="YOUR_SERVER_IP_OR_DOMAIN"
```

## 1) Bootstrap VPS (jalankan di VPS sebagai root)

```bash
sudo -i
apt update
apt -y upgrade
apt -y install git curl wget unzip jq htop tmux ufw fail2ban chrony \
  python3 python3-venv python3-pip build-essential ca-certificates \
  nginx apache2-utils

timedatectl set-timezone Asia/Jakarta
systemctl enable --now chrony

ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw --force enable

systemctl enable --now fail2ban
```

## 2) Buat user + clone repo

```bash
id -u "$APP_USER" >/dev/null 2>&1 || adduser --disabled-password --gecos "" "$APP_USER"
usermod -aG sudo "$APP_USER"

mkdir -p "$BASE_DIR"
chown -R "$APP_USER:$APP_USER" "$BASE_DIR"

sudo -u "$APP_USER" -H bash -lc "cd '$BASE_DIR' && git clone '$REPO_URL'"
sudo -u "$APP_USER" -H bash -lc "cd '$APP_DIR' && git checkout '$BRANCH'"
```

## 3) Buat virtualenv + install dependency

```bash
sudo -u "$APP_USER" -H bash -lc "cd '$APP_DIR' && python3 -m venv .venv"
sudo -u "$APP_USER" -H bash -lc "cd '$APP_DIR' && . .venv/bin/activate && python -m pip install --upgrade pip"
sudo -u "$APP_USER" -H bash -lc "cd '$APP_DIR' && . .venv/bin/activate && pip install -r requirements.txt"
```

## 4) Siapkan file environment

```bash
sudo -u "$APP_USER" -H bash -lc "cp '$APP_DIR/.env.example' '$APP_DIR/.env'"
nano "$APP_DIR/.env"
```

Contoh baseline awal:

```env
SYMBOLS=BTC/USDT,ETH/USDT,SOL/USDT
ENABLED_EXCHANGES=binance,bybit

DEFAULT_TAKER_FEE_RATE=0.001
BINANCE_SPOT_FEE=0.001
BYBIT_SPOT_FEE=0.001

SLIPPAGE_BPS=3
TRADE_SIZE_QUOTE=500
MIN_NET_SPREAD_PCT=0.03
MIN_NET_PROFIT_QUOTE=0.5

SNAPSHOT_CSV_PATH=data/arbitrage_opportunities.csv

TELEGRAM_ENABLED=false
# TELEGRAM_BOT_TOKEN=
# TELEGRAM_CHAT_ID=
```

## 5) Service scanner (oneshot + timer)

```bash
cat > /etc/systemd/system/interexchange-arbitrage.service << 'EOF'
[Unit]
Description=Inter-Exchange Spot Arbitrage Scanner (one run)

[Service]
Type=oneshot
User=arbbot
Group=arbbot
WorkingDirectory=/opt/interexchange-arbitrage/ArbBot
EnvironmentFile=/opt/interexchange-arbitrage/ArbBot/.env
Environment=PYTHONPATH=src
ExecStart=/opt/interexchange-arbitrage/ArbBot/.venv/bin/python /opt/interexchange-arbitrage/ArbBot/main.py
StandardOutput=journal
StandardError=journal
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/opt/interexchange-arbitrage/ArbBot
EOF

cat > /etc/systemd/system/interexchange-arbitrage.timer << 'EOF'
[Unit]
Description=Run interexchange arbitrage scanner periodically

[Timer]
OnBootSec=30s
OnUnitActiveSec=30s
AccuracySec=1s
Unit=interexchange-arbitrage.service

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now interexchange-arbitrage.timer
systemctl start interexchange-arbitrage.service
```

## 6) Service dashboard (uvicorn on localhost)

```bash
cat > /etc/systemd/system/arbbot-dashboard.service << 'EOF'
[Unit]
Description=ArbBot Web Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=arbbot
Group=arbbot
WorkingDirectory=/opt/interexchange-arbitrage/ArbBot
Environment=PYTHONPATH=src
Environment=ARB_SERVICE_NAME=interexchange-arbitrage
ExecStart=/opt/interexchange-arbitrage/ArbBot/.venv/bin/uvicorn interexchange_arbitrage.dashboard.app:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now arbbot-dashboard
```

## 7) Nginx reverse proxy + basic auth

```bash
htpasswd -c /etc/nginx/.htpasswd arbbotadmin

cat > /etc/nginx/sites-available/arbbot-dashboard << 'EOF'
server {
    listen 80 default_server;
    server_name _;

    access_log /var/log/nginx/arbbot_dashboard_access.log;
    error_log  /var/log/nginx/arbbot_dashboard_error.log;

    location / {
        auth_basic "Restricted Dashboard";
        auth_basic_user_file /etc/nginx/.htpasswd;

        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/arbbot-dashboard /etc/nginx/sites-enabled/arbbot-dashboard
nginx -t
systemctl enable --now nginx
systemctl restart nginx
```

## 8) Verifikasi runtime

```bash
systemctl status interexchange-arbitrage.timer --no-pager
systemctl status arbbot-dashboard --no-pager
systemctl status nginx --no-pager

journalctl -u interexchange-arbitrage -n 50 --no-pager
journalctl -u arbbot-dashboard -n 50 --no-pager

curl -I http://127.0.0.1:8000/
curl -I http://127.0.0.1/
```

## 9) Setup SSH key khusus GitHub Actions deploy

### 9a) Di VPS: buat user deploy + authorized_keys

```bash
id -u deploy >/dev/null 2>&1 || adduser --disabled-password --gecos "" deploy
usermod -aG sudo deploy
mkdir -p /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chown -R deploy:deploy /home/deploy/.ssh
```

### 9b) Di lokal (PowerShell): generate key

```powershell
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\arbbot_deploy" -C "github-actions-arbbot"
Get-Content "$env:USERPROFILE\.ssh\arbbot_deploy.pub"
```

### 9c) Di VPS: tempel public key ke deploy user

```bash
nano /home/deploy/.ssh/authorized_keys
chmod 600 /home/deploy/.ssh/authorized_keys
chown deploy:deploy /home/deploy/.ssh/authorized_keys
```

## 10) Script deploy di VPS (dipanggil GitHub Actions)

```bash
cat > /usr/local/bin/arbbot-deploy.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/interexchange-arbitrage/ArbBot"
BRANCH="main"

cd "$APP_DIR"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"

. .venv/bin/activate
pip install -r requirements.txt

systemctl restart arbbot-dashboard
systemctl restart interexchange-arbitrage.timer
systemctl start interexchange-arbitrage.service

echo "Deploy completed"
EOF

chmod +x /usr/local/bin/arbbot-deploy.sh
```

## 11) Batasi sudo untuk deploy user

```bash
cat > /etc/sudoers.d/deploy-arbbot << 'EOF'
deploy ALL=(root) NOPASSWD:/usr/local/bin/arbbot-deploy.sh,/bin/systemctl restart arbbot-dashboard,/bin/systemctl restart interexchange-arbitrage.timer,/bin/systemctl start interexchange-arbitrage.service
EOF
chmod 440 /etc/sudoers.d/deploy-arbbot
visudo -cf /etc/sudoers.d/deploy-arbbot
```

## 12) Tambahkan GitHub Secrets (di repository GitHub)

Masuk: Repo -> Settings -> Secrets and variables -> Actions -> New repository secret

Buat secrets ini:
- `VPS_HOST` = IP publik VPS
- `VPS_USER` = deploy
- `VPS_SSH_KEY` = isi private key `arbbot_deploy` (bukan .pub)

## 13) Buat workflow GitHub Actions auto-deploy

Jalankan dari root repo lokal:

```bash
mkdir -p .github/workflows
cat > .github/workflows/deploy-vps.yml << 'EOF'
name: Deploy To VPS

on:
  push:
    branches: ["main"]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup SSH key
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.VPS_SSH_KEY }}" > ~/.ssh/id_ed25519
          chmod 600 ~/.ssh/id_ed25519
          ssh-keyscan -H "${{ secrets.VPS_HOST }}" >> ~/.ssh/known_hosts

      - name: Run deploy script on VPS
        run: |
          ssh -i ~/.ssh/id_ed25519 "${{ secrets.VPS_USER }}@${{ secrets.VPS_HOST }}" "sudo /usr/local/bin/arbbot-deploy.sh"
EOF
```

Commit dan push:

```bash
git add .github/workflows/deploy-vps.yml
git commit -m "Add VPS auto-deploy workflow"
git push origin main
```

## 14) Uji auto-deploy

1. Ubah file kecil di repo, commit, push ke `main`.
2. Cek tab Actions: workflow `Deploy To VPS` harus sukses.
3. Cek VPS:

```bash
journalctl -u arbbot-dashboard -n 30 --no-pager
journalctl -u interexchange-arbitrage -n 30 --no-pager
```

## 15) Troubleshooting cepat

### Deploy gagal SSH
- Cek secrets `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`
- Cek key pair cocok (`authorized_keys` berisi public key yang benar)

### Deploy sukses tapi service down
```bash
systemctl status arbbot-dashboard --no-pager
journalctl -u arbbot-dashboard -n 100 --no-pager
```

### Dashboard tidak bisa diakses publik
- Cek firewall GCP ingress `tcp:80`
- Cek UFW `80/tcp` terbuka
- Cek nginx status dan config test (`nginx -t`)

---

Selesai. Dengan ini setiap push ke `main` akan auto-deploy ke VPS.
