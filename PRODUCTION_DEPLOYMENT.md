# CBS 3i-Cell Placement Portal - Production Deployment Guide

## 1. Production Architecture Overview
- **Application Layer**: Python Flask 3.0 / WSGI (`wsgi.py`).
- **Database Layer**: MongoDB 7.0+ with connection pooling (50 concurrent connections, read/write retries) and GridFS binary document vault.
- **Security Perimeter**: Flask-Talisman (CSP, HSTS, X-Content-Type), Flask-Limiter (Rate Limiting), Flask-WTF (CSRF Tokens), 16MB max upload defense.
- **Logging Subsystem**: Multi-file rotating log handler (`logs/cbs_portal.log`, 5MB cap with 5 historical archives).
- **Health Probing**: Real-time `/health` and `/api/health` probes for uptime monitors, load balancers, and container orchestration.

---

## 2. Environment Configuration (`.env`)
Create a production `.env` file in the project root:

```env
# Runtime Environment
FLASK_ENV=production
DEBUG=False

# Cryptographic Session Secret (Generate via: python -c "import secrets; print(secrets.token_hex(32))")
SECRET_KEY=e4f9b8c2d1a0e7f6543219876543210fedcba9876543210abcdef1234567890a

# Database Configuration
MONGO_URI=mongodb://127.0.0.1:27017
DB_NAME=placement_system

# Server Binding
HOST=0.0.0.0
PORT=5000

# Security (Activate once domain has valid SSL/TLS certificate)
SESSION_COOKIE_SECURE=True
TALISMAN_FORCE_HTTPS=True

# Upload Controls
MAX_CONTENT_LENGTH=16777216
```

---

## 3. Launching in Production

### Option A: Standard Production (Gunicorn on Linux)
```bash
# Multi-worker production daemon
gunicorn -w 4 -b 0.0.0.0:5000 --access-logfile logs/access.log --error-logfile logs/error.log wsgi:app
```

### Option B: Systemd Service (`/etc/systemd/system/placement-cell.service`)
```ini
[Unit]
Description=CBS Placement Cell ERP Daemon
After=network.target mongodb.service

[Service]
User=www-data
WorkingDirectory=/var/www/placement-cell-project
Environment="PATH=/var/www/placement-cell-project/venv/bin"
ExecStart=/var/www/placement-cell-project/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

### Option C: Standalone Python Server (Windows / Linux)
```bash
python wsgi.py
```

---

## 4. Reverse Proxy Setup (Nginx)

```nginx
server {
    listen 80;
    server_name placement.chetanbusinessschool.edu;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name placement.chetanbusinessschool.edu;

    ssl_certificate /etc/letsencrypt/live/placement.chetanbusinessschool.edu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/placement.chetanbusinessschool.edu/privkey.pem;

    client_max_body_size 16M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /var/www/placement-cell-project/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # Health check bypass
    location /health {
        proxy_pass http://127.0.0.1:5000/health;
        access_log off;
    }
}
```

---

## 5. Automated Health & Monitoring
The service exposes a real-time JSON probe at `/health`:

```bash
curl -f http://127.0.0.1:5000/health
```

**Response (HTTP 200 OK):**
```json
{
  "status": "healthy",
  "database": {
    "connected": true,
    "message": "Connected"
  },
  "service": {
    "name": "CBS Placement ERP",
    "version": "2.5.0-production",
    "environment": "production",
    "timestamp": "2026-10-26T22:12:49.329182"
  }
}
```

---

## 6. Database Maintenance & Backup

```bash
# Automated Daily Backup
mongodump --db placement_system --out /var/backups/mongodb/$(date +%F)

# Backup Rotation (Keep 14 days)
find /var/backups/mongodb/* -mtime +14 -exec rm -rf {} \;
```

---

## 7. Verification Checklist
- [x] All 29 Jinja templates pass compilation with 0 syntax errors (`python validate_templates.py`).
- [x] Full automated test suite passes 100% (`python test_suite.py`).
- [x] Live end-to-end integration verified (`python test_live.py`).
- [x] Branded recovery error pages configured (`403`, `404`, `429`, `500`).
- [x] Rotating log handler active (`logs/cbs_portal.log`).
- [x] Production database connection pool & indexing active.
