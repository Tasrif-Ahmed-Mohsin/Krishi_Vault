#!/usr/bin/env bash
# ==============================================================================
# KrishiVault Azure VM Automated Bootstrap Script
# Target: Ubuntu 22.04 LTS / 24.04 LTS
# Usage: sudo bash azure_bootstrap.sh [your-domain-or-azure-dns]
# ==============================================================================

set -euo pipefail

DOMAIN="${1:-_}"
INSTALL_DIR="/opt/krishivault"
SERVICE_USER="${SUDO_USER:-azureuser}"

echo "=========================================================="
echo " Starting KrishiVault Azure VM Setup"
echo " User: $SERVICE_USER | Domain: $DOMAIN"
echo "=========================================================="

# 1. Update OS and install prerequisites
echo "[1/6] Updating OS packages and installing system libraries..."
apt-get update -y
apt-get install -y python3-pip python3-venv python3-dev git nginx certbot python3-certbot-nginx curl ufw

# 2. Setup directory and clone or update repo
echo "[2/6] Preparing repository at $INSTALL_DIR..."
if [ ! -d "$INSTALL_DIR/.git" ]; then
    mkdir -p "$INSTALL_DIR"
    git clone https://github.com/Tasrif-Ahmed-Mohsin/Krishi_Vault.git "$INSTALL_DIR"
else
    git -C "$INSTALL_DIR" pull origin main
fi
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

# 3. Setup Python virtual environment
echo "[3/6] Setting up Python virtual environment..."
cd "$INSTALL_DIR/krishivault-pipeline"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-cloud.txt
pip install gunicorn

# 4. Create credentials folder & sample .env if not exists
echo "[4/6] Initializing secure credentials directory..."
mkdir -p credentials
chmod 700 credentials
chown -R "$SERVICE_USER:$SERVICE_USER" credentials

if [ ! -f ".env" ]; then
    cp .env.example .env
    chmod 600 .env
    chown "$SERVICE_USER:$SERVICE_USER" .env
    echo "Created template .env at $INSTALL_DIR/krishivault-pipeline/.env"
fi

# 5. Configure Systemd service
echo "[5/6] Creating systemd service (krishivault.service)..."
cat <<EOF > /etc/systemd/system/krishivault.service
[Unit]
Description=KrishiVault Telephony and AI Service
After=network.target

[Service]
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR/krishivault-pipeline
Environment="PATH=$INSTALL_DIR/krishivault-pipeline/venv/bin"
ExecStart=$INSTALL_DIR/krishivault-pipeline/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.main:app --bind 127.0.0.1:8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable krishivault.service
systemctl restart krishivault.service || true

# 6. Configure Nginx reverse proxy
echo "[6/6] Configuring Nginx reverse proxy..."
cat <<EOF > /etc/nginx/sites-available/krishivault
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 25M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

ln -sf /etc/nginx/sites-available/krishivault /etc/nginx/sites-enabled/krishivault
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

# Firewall rules
ufw allow 22/tcp || true
ufw allow 'Nginx Full' || true

echo "=========================================================="
echo " KrishiVault Azure Bootstrap Complete!"
echo " Next Steps:"
echo " 1. Edit your secrets in: $INSTALL_DIR/krishivault-pipeline/.env"
echo " 2. If using Google Voice, place key in: $INSTALL_DIR/krishivault-pipeline/credentials/gcp-tts.json"
echo " 3. Restart the service: sudo systemctl restart krishivault"
echo " 4. (Optional) Run certbot for SSL: sudo certbot --nginx -d $DOMAIN"
echo "=========================================================="
