#!/usr/bin/env bash
set -euo pipefail

APP_USER="${APP_USER:-arbbot}"
APP_DIR="${APP_DIR:-/opt/interexchange-arbitrage/ArbBot}"
BRANCH="${BRANCH:-main}"
FAIL_ONESHOT_START="${FAIL_ONESHOT_START:-0}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "This script must run as root (use sudo)." >&2
  exit 1
fi

if [[ ! -d "$APP_DIR" ]]; then
  echo "APP_DIR not found: $APP_DIR" >&2
  exit 1
fi

if ! id "$APP_USER" >/dev/null 2>&1; then
  echo "APP_USER not found: $APP_USER" >&2
  exit 1
fi

ENV_FILE="$APP_DIR/.env"
ENV_EXAMPLE_FILE="$APP_DIR/.env.example"

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "$ENV_EXAMPLE_FILE" ]]; then
    cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
    chown "$APP_USER:$APP_USER" "$ENV_FILE"
  else
    touch "$ENV_FILE"
    chown "$APP_USER:$APP_USER" "$ENV_FILE"
  fi
fi

# Step 1: sync code
sudo -u "$APP_USER" -H bash -lc "
  set -euo pipefail
  cd '$APP_DIR'
  git fetch origin '$BRANCH'
  git reset --hard 'origin/$BRANCH'
"

# Step 2: merge new env keys from .env.example without overwriting existing values.
if [[ -f "$ENV_EXAMPLE_FILE" ]]; then
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    key="${line%%=*}"
    [[ -z "$key" ]] && continue
    if ! grep -qE "^${key}=" "$ENV_FILE"; then
      printf "\n%s\n" "$line" >> "$ENV_FILE"
    fi
  done < "$ENV_EXAMPLE_FILE"
fi
chown "$APP_USER:$APP_USER" "$ENV_FILE"

# Step 3: install dependencies in venv
sudo -u "$APP_USER" -H bash -lc "
  set -euo pipefail
  cd '$APP_DIR'
  if [[ ! -d .venv ]]; then
    python3 -m venv .venv
  fi
  . .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
"

# Step 4: ensure runtime directories for configured output files exist
mapfile -t OUTPUT_DIRS < <(sudo -u "$APP_USER" -H bash -lc "
  set -euo pipefail
  cd '$APP_DIR'
  . .venv/bin/activate
  PYTHONPATH=src python - <<'PY'
from pathlib import Path
from interexchange_arbitrage.settings import load_settings
s = load_settings(env_file='.env')
paths = [s.snapshot_csv_path, s.paper_state_path, s.paper_trades_csv_path]
for p in paths:
    path = Path(p)
    if not path.is_absolute():
        path = Path('.').resolve() / path
    print(str(path.parent))
PY
")

for dir_path in "${OUTPUT_DIRS[@]}"; do
  [[ -z "$dir_path" ]] && continue
  mkdir -p "$dir_path"
  chown -R "$APP_USER:$APP_USER" "$dir_path"
done

# Step 5: preflight config parse/import validation
sudo -u "$APP_USER" -H bash -lc "
  set -euo pipefail
  cd '$APP_DIR'
  . .venv/bin/activate
  PYTHONPATH=src python - <<'PY'
from interexchange_arbitrage.settings import load_settings
load_settings(env_file='.env')
print('Preflight settings validation: OK')
PY
"

# Step 6: restart services only after preflight passes
systemctl restart arbbot-dashboard
systemctl restart interexchange-arbitrage.timer

# Optional smoke check for the oneshot scanner service.
# A runtime/API hiccup should not break deploy by default.
if ! systemctl start interexchange-arbitrage.service; then
  echo "Warning: interexchange-arbitrage.service failed during smoke start." >&2
  systemctl --no-pager --full status interexchange-arbitrage.service || true
  journalctl -xeu interexchange-arbitrage.service --no-pager -n 120 || true
  if [[ "$FAIL_ONESHOT_START" == "1" ]]; then
    echo "FAIL_ONESHOT_START=1, failing deploy." >&2
    exit 1
  fi
fi

echo "Deploy completed"
