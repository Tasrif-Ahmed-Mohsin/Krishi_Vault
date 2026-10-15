# Deploying KrishiVault on an Azure Virtual Machine (Ubuntu)

This guide covers production deployment of KrishiVault on an **Azure Virtual Machine** running Ubuntu 22.04 or 24.04 LTS, using **Systemd**, **Nginx** reverse proxy, and **Let's Encrypt SSL**.

---

## 1. Azure VM Provisioning

### Recommended Specifications
- **Image**: Ubuntu Server 22.04 LTS (x64 Gen2) or 24.04 LTS
- **Size**: `Standard_B2s` (2 vCPUs, 4 GiB memory) or `Standard_B2ms` (2 vCPUs, 8 GiB memory)
- **OS Disk**: 30 GiB Standard SSD / Premium SSD
- **Public IP**: Static (or assign a DNS name like `<yourapp>.eastus.cloudapp.azure.com` in Azure Portal)

### Network Security Group (Inbound Port Rules)
In Azure Portal, navigate to **Networking** for your VM and add:

| Priority | Name | Port | Protocol | Source | Action |
|---|---|---|---|---|---|
| 300 | `Allow-SSH` | `22` | TCP | Your IP (or Any) | Allow |
| 310 | `Allow-HTTP` | `80` | TCP | Any (`*`) | Allow |
| 320 | `Allow-HTTPS` | `443` | TCP | Any (`*`) | Allow |

---

## 2. Server OS Initialization

SSH into your Azure VM:
```bash
ssh azureuser@<YOUR_VM_PUBLIC_IP>
```

Run system updates and install required dependencies:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv python3-dev git nginx certbot python3-certbot-nginx curl ufw
```

---

## 3. Clone Repository & Setup Virtual Environment

Clone the repository to `/opt/krishivault` (or your home directory):
```bash
sudo mkdir -p /opt/krishivault
sudo chown -R $USER:$USER /opt/krishivault
git clone https://github.com/Tasrif-Ahmed-Mohsin/Krishi_Vault.git /opt/krishivault
cd /opt/krishivault/krishivault-pipeline
```

Create and activate Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-cloud.txt
pip install gunicorn
```

Verify tests pass on the VM:
```bash
python -m pytest
```

---

## 4. Environment Variables & Secret Configuration

Since secrets are **never stored in git**, create your production `.env` and Google Service Account key directly on the VM:

### A. Create `.env`
```bash
nano /opt/krishivault/krishivault-pipeline/.env
```

Paste your production secrets:
```ini
# Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Google Cloud Text-to-Speech
GOOGLE_APPLICATION_CREDENTIALS=/opt/krishivault/krishivault-pipeline/credentials/gcp-tts.json

# REVE SMS
SMS_BASE_URL=https://smpp.revesms.com:7790
SMS_API_KEY=your_sms_api_key
SMS_SECRET_KEY=your_sms_secret_key
SMS_SENDER_ID=your_sender_id
SMS_LIVE=1

# VoiceBlast (SysTech)
VOICEBLAST_BASE_URL=http://voice.smsvaults.work
VOICEBLAST_USER=your_voiceblast_user
VOICEBLAST_PASSWORD=your_voiceblast_password
VOICEBLAST_CALLER_ID=09612010692
VOICEBLAST_DEFAULT_AUDIO_ID=1106
VOICEBLAST_LIVE=1

# Optional Weather / Scraper
OPENWEATHER_API_KEY=
```

Restrict permissions on `.env`:
```bash
chmod 600 /opt/krishivault/krishivault-pipeline/.env
```

### B. Place Google Service Account Key
```bash
mkdir -p /opt/krishivault/krishivault-pipeline/credentials
chmod 700 /opt/krishivault/krishivault-pipeline/credentials
nano /opt/krishivault/krishivault-pipeline/credentials/gcp-tts.json
```
*(Paste your Google Cloud Service Account JSON and save)*:
```bash
chmod 600 /opt/krishivault/krishivault-pipeline/credentials/gcp-tts.json
```

---

## 5. Systemd Daemon Configuration

Create a systemd service to run KrishiVault automatically in the background and survive reboots.

```bash
sudo nano /etc/systemd/system/krishivault.service
```

Paste the following service definition:
```ini
[Unit]
Description=KrishiVault FastAPI Telephony & AI Service
After=network.target

[Service]
User=azureuser
Group=azureuser
WorkingDirectory=/opt/krishivault/krishivault-pipeline
Environment="PATH=/opt/krishivault/krishivault-pipeline/venv/bin"
ExecStart=/opt/krishivault/krishivault-pipeline/venv/bin/gunicorn \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    src.main:app \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/krishivault_access.log \
    --error-logfile /var/log/krishivault_error.log

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable krishivault
sudo systemctl start krishivault
sudo systemctl status krishivault
```

---

## 6. Nginx Reverse Proxy & SSL Setup

Configure Nginx to route external web traffic to the local Gunicorn/FastAPI process.

```bash
sudo nano /etc/nginx/sites-available/krishivault
```

Paste the configuration (replace `your-domain.com` with your actual domain or Azure DNS name):
```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (for live preview/audio streaming)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable the site and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/krishivault /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### Install Free Let's Encrypt SSL
```bash
sudo certbot --nginx -d your-domain.com
```
Certbot will automatically configure HTTPS on port 443 and auto-renew the certificates.

---

## 7. Firewall (UFW)
Enable Ubuntu's built-in firewall:
```bash
sudo ufw allow 22/tcp
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
sudo ufw status
```

---

## 8. Continuous Updates (One-Click Pull & Restart)

Save this update script at `/opt/krishivault/update.sh`:
```bash
sudo nano /opt/krishivault/update.sh
```

```bash
#!/bin/bash
set -e
cd /opt/krishivault
echo "Pulling latest changes from git..."
git pull origin main

cd /opt/krishivault/krishivault-pipeline
source venv/bin/activate
echo "Updating packages..."
pip install -q -r requirements-cloud.txt

echo "Running tests..."
python -m pytest

echo "Restarting KrishiVault service..."
sudo systemctl restart krishivault
echo "Deployment updated successfully!"
```

Make it executable:
```bash
chmod +x /opt/krishivault/update.sh
```

Whenever you push changes to GitHub, run:
```bash
/opt/krishivault/update.sh
```
