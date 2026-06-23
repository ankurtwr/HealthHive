#!/bin/bash
# ============================================================
# HealthHive — EC2 Ubuntu 22.04 Full Setup Script
# Run this ONCE after SSH-ing into your fresh EC2 instance.
#
# Usage:
#   chmod +x deploy/setup.sh
#   ./deploy/setup.sh
#
# What it does (matches the deployment guide phases 2-4):
#   - Updates system packages
#   - Installs Python 3, MySQL, Nginx, Tesseract, OpenCV deps
#   - Installs Playwright system dependencies
#   - Clones HealthHive repo
#   - Creates Python venv and installs requirements + gunicorn
#   - Installs Playwright Chromium browser
#   - Prompts you for .env values and creates the .env file
#   - Runs all DB schema migrations
#   - Sets up systemd service for Gunicorn
#   - Configures Nginx as reverse proxy
#   - Starts and enables all services
# ============================================================

set -e  # Exit immediately on any error

# ── Colours for output ────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log()  { echo -e "${GREEN}[✓] $1${NC}"; }
warn() { echo -e "${YELLOW}[!] $1${NC}"; }
err()  { echo -e "${RED}[✗] $1${NC}"; exit 1; }
info() { echo -e "${BLUE}[→] $1${NC}"; }

# ── Configuration ─────────────────────────────────────────────
APP_DIR="/home/ubuntu/HealthHive"
REPO_URL="https://github.com/ankurtwr/HealthHive.git"
VENV_DIR="$APP_DIR/venv"
SERVICE_FILE="/etc/systemd/system/healthhive.service"
NGINX_CONF="/etc/nginx/sites-available/healthhive"
LOG_DIR="/var/log/healthhive"
SOCK_FILE="$APP_DIR/healthhive.sock"

echo ""
echo "========================================================"
echo "  HealthHive EC2 Deployment — Ubuntu 22.04"
echo "========================================================"
echo ""

# ─────────────────────────────────────────────────────────────
# PHASE 2 — System Dependencies
# ─────────────────────────────────────────────────────────────
info "Phase 2: Installing system dependencies..."

sudo apt-get update -y && sudo apt-get upgrade -y
log "System updated"

# Core tools
sudo apt-get install -y \
    python3 python3-pip python3-venv \
    git curl wget \
    build-essential libssl-dev libffi-dev \
    software-properties-common
log "Core tools installed"

# MySQL Server
info "Installing MySQL Server..."
sudo apt-get install -y mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql
log "MySQL installed and started"

# Tesseract OCR
info "Installing Tesseract OCR..."
sudo apt-get install -y tesseract-ocr libtesseract-dev
tesseract --version && log "Tesseract installed: $(tesseract --version | head -1)"

# OpenCV system libraries (without these, 'import cv2' crashes)
info "Installing OpenCV system libraries..."
sudo apt-get install -y \
    libgl1-mesa-glx libglib2.0-0 \
    libsm6 libxrender1 libxext6
log "OpenCV system libs installed"

# Playwright browser system dependencies
info "Installing Playwright browser system dependencies..."
sudo apt-get install -y \
    libnss3 libnspr4 libasound2 \
    libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 \
    xvfb
log "Playwright system deps installed"

# Nginx
info "Installing Nginx..."
sudo apt-get install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx
log "Nginx installed"

# ─────────────────────────────────────────────────────────────
# PHASE 3 — Clone & Configure HealthHive
# ─────────────────────────────────────────────────────────────
info "Phase 3: Cloning HealthHive repository..."

if [ -d "$APP_DIR" ]; then
    warn "Directory $APP_DIR already exists. Pulling latest changes..."
    cd "$APP_DIR" && git pull origin main
else
    git clone "$REPO_URL" "$APP_DIR"
    log "Repository cloned to $APP_DIR"
fi

# Create Python virtual environment
info "Creating Python virtual environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
log "Virtual environment created"

# Install Python dependencies
info "Installing Python requirements (this may take 5-10 minutes)..."
pip install -r "$APP_DIR/requirements.txt"
pip install gunicorn
log "Python dependencies installed"

# Install Playwright Chromium browser (~150MB download)
info "Installing Playwright Chromium browser (~150MB — please wait)..."
playwright install chromium
playwright install-deps chromium
log "Playwright Chromium installed"

deactivate

# ── Database Setup ────────────────────────────────────────────
echo ""
echo "========================================================"
echo "  MySQL Setup"
echo "========================================================"
warn "You need to set a MySQL root password and create the HealthHive DB user."
warn "Run 'sudo mysql_secure_installation' NOW in another terminal if not done yet."
echo ""

read -p "Enter the MySQL DB password you want for the 'healthhive' user: " DB_PASS
read -s -p "" _  # consume any leftover input

# Create DB and user
info "Creating MySQL database 'medcompare' and user 'healthhive'..."
sudo mysql -u root <<EOF
CREATE DATABASE IF NOT EXISTS medcompare
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'healthhive'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON medcompare.* TO 'healthhive'@'localhost';
FLUSH PRIVILEGES;
EOF
log "MySQL database and user created"

# ── Create .env file ──────────────────────────────────────────
echo ""
echo "========================================================"
echo "  Environment Configuration (.env)"
echo "========================================================"
info "Setting up .env file (your secrets — never committed to git)..."

read -p "Enter your Google Gemini API key (or press Enter to skip): " GEMINI_KEY
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

cat > "$APP_DIR/.env" <<EOF
# ── Database ──────────────────────────────────────────────────
DB_HOST=localhost
DB_USER=healthhive
DB_PASSWORD=${DB_PASS}
DB_NAME=medcompare

# ── Flask ─────────────────────────────────────────────────────
SECRET_KEY=${SECRET_KEY}
FLASK_ENV=production

# ── Google Gemini API ─────────────────────────────────────────
GEMINI_API_KEY=${GEMINI_KEY}

# ── Tesseract (Linux path) ────────────────────────────────────
TESSERACT_CMD=/usr/bin/tesseract
EOF

chmod 600 "$APP_DIR/.env"
log ".env created at $APP_DIR/.env (permissions 600 — owner-only)"

# ── Run DB Migrations ─────────────────────────────────────────
info "Running database schema and migrations..."
source "$VENV_DIR/bin/activate"

mysql -u healthhive -p"${DB_PASS}" medcompare < "$APP_DIR/schema.sql"
log "Base schema imported"

mysql -u healthhive -p"${DB_PASS}" medcompare < "$APP_DIR/schema_migration_v2.sql"
log "Migration v2 applied"

mysql -u healthhive -p"${DB_PASS}" medcompare < "$APP_DIR/schema_update.sql"
log "Schema update applied"

cd "$APP_DIR"
python seed_sample.py && log "Sample data seeded"
python scripts/fetch_janaushadhi.py && log "Jan Aushadhi data fetched" || warn "fetch_janaushadhi.py failed — run manually later"

deactivate

# ─────────────────────────────────────────────────────────────
# PHASE 4 — Production Setup (Gunicorn + Nginx)
# ─────────────────────────────────────────────────────────────
info "Phase 4: Configuring Gunicorn and Nginx..."

# Create log directory
sudo mkdir -p "$LOG_DIR"
sudo chown ubuntu:ubuntu "$LOG_DIR"
log "Log directory created at $LOG_DIR"

# ── systemd service ───────────────────────────────────────────
info "Installing systemd service..."
sudo cp "$APP_DIR/deploy/healthhive.service" "$SERVICE_FILE"
sudo systemctl daemon-reload
sudo systemctl enable healthhive
sudo systemctl start healthhive
sleep 2
sudo systemctl is-active --quiet healthhive && log "Gunicorn service is running" || err "Gunicorn service failed to start — check: sudo journalctl -u healthhive -f"

# ── Nginx configuration ───────────────────────────────────────
info "Configuring Nginx..."

# Keep server_name as _ (wildcard catch-all) so the site remains accessible even if the EC2 Public IP changes.
# If you map a domain name later, you can replace _ with your domain name.
# We also print the public IP for convenience.
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || curl -s https://ifconfig.me 2>/dev/null || echo "_")

sudo cp "$APP_DIR/deploy/nginx_healthhive.conf" "$NGINX_CONF"

# Enable site, disable default
sudo ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/healthhive
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload Nginx
sudo nginx -t && sudo systemctl restart nginx
log "Nginx configured and restarted"

# Set socket permissions so Nginx (www-data) can access it
sudo usermod -aG www-data ubuntu
log "Added ubuntu user to www-data group"

# ── Final verification ────────────────────────────────────────
echo ""
echo "========================================================"
echo "  Deployment Complete!"
echo "========================================================"
log "All services configured."
echo ""
echo -e "  ${BLUE}App URL:${NC}        http://${PUBLIC_IP}"
echo -e "  ${BLUE}Gunicorn logs:${NC}  sudo journalctl -u healthhive -f"
echo -e "  ${BLUE}Nginx error log:${NC} sudo tail -f /var/log/nginx/error.log"
echo -e "  ${BLUE}App error log:${NC}  sudo tail -f ${LOG_DIR}/error.log"
echo ""
echo -e "${YELLOW}[!] IMPORTANT: Reboot the instance to apply group changes:${NC}"
echo "    sudo reboot"
echo ""
echo -e "${YELLOW}[!] After reboot, verify with:${NC}"
echo "    sudo systemctl status healthhive"
echo "    sudo systemctl status nginx"
echo ""
