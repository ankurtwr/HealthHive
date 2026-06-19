#!/bin/bash
# ============================================================
# HealthHive — Quick Update / Redeploy Script
# Run from inside the EC2 instance after pushing code to GitHub.
#
# Usage:
#   chmod +x deploy/deploy.sh
#   ./deploy/deploy.sh
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓] $1${NC}"; }
warn() { echo -e "${YELLOW}[!] $1${NC}"; }

APP_DIR="/home/ubuntu/HealthHive"
VENV_DIR="$APP_DIR/venv"

cd "$APP_DIR"

warn "Pulling latest code from GitHub..."
git pull origin main
log "Code updated"

source "$VENV_DIR/bin/activate"

warn "Installing any new dependencies..."
pip install -r requirements.txt --quiet
log "Dependencies up to date"

deactivate

warn "Restarting Gunicorn service..."
sudo systemctl restart healthhive
sleep 2
sudo systemctl is-active --quiet healthhive && log "HealthHive is running!" || echo "ERROR: Service failed — check: sudo journalctl -u healthhive -f"
