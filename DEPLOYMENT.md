# Deploying UniSphere

This guide describes a conventional single-server deployment (Ubuntu 22.04, MySQL 8, Gunicorn + eventlet, Nginx). It has been exercised locally with the dev server and the test suite; adapt hostnames, paths and secrets to your environment and verify each step on your server.

## 1. System packages

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential mysql-server nginx pkg-config default-libmysqlclient-dev
```

## 2. MySQL

```bash
sudo mysql_secure_installation
sudo mysql <<'SQL'
CREATE DATABASE unisphere CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'unisphere'@'localhost' IDENTIFIED BY 'CHANGE_ME_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON unisphere.* TO 'unisphere'@'localhost';
FLUSH PRIVILEGES;
SQL
```

Enable automated backups (e.g. nightly `mysqldump unisphere | gzip > /backups/unisphere-$(date +%F).sql.gz`).

## 3. Application user & code

```bash
sudo adduser --system --group --home /srv/unisphere unisphere
sudo -u unisphere git clone <repo> /srv/unisphere/app
cd /srv/unisphere/app
sudo -u unisphere python3 -m venv .venv
sudo -u unisphere .venv/bin/pip install -r requirements.txt
```

## 4. Environment

Create `/srv/unisphere/app/.env` (mode 600, owned by `unisphere`):

```
FLASK_ENV=production
SECRET_KEY=<python -c "import secrets;print(secrets.token_hex(32))">
DATABASE_URL=mysql+pymysql://unisphere:CHANGE_ME_STRONG_PASSWORD@localhost:3306/unisphere?charset=utf8mb4
UPLOAD_FOLDER=/srv/unisphere/uploads
SESSION_COOKIE_SECURE=true
SOCKETIO_ASYNC_MODE=eventlet
# SOCKETIO_MESSAGE_QUEUE=redis://localhost:6379/0   # only when running >1 worker
```

### Persistent image storage

Uploaded images are written to `UPLOAD_FOLDER` and served from `/uploads/<file>`. Keep this directory **outside** the code checkout so redeploys never touch it, and include it in backups:

```bash
sudo mkdir -p /srv/unisphere/uploads && sudo chown unisphere:unisphere /srv/unisphere/uploads
```

On platforms with ephemeral disks (Heroku-style, container PaaS) mount a persistent volume at that path or point it at network storage; otherwise images disappear on restart.

## 5. Database migrations

```bash
cd /srv/unisphere/app
sudo -u unisphere env FLASK_APP=run.py .venv/bin/flask db upgrade
# optional demo data:  sudo -u unisphere env FLASK_APP=run.py .venv/bin/flask seed
```

Run `flask db upgrade` after every deploy that includes a new migration.

## 6. Gunicorn (Socket.IO-aware)

Flask-SocketIO needs an async worker. **Use exactly one eventlet worker** unless you configure a Redis message queue (see §8).

`/etc/systemd/system/unisphere.service`:

```ini
[Unit]
Description=UniSphere (Gunicorn + eventlet)
After=network.target mysql.service

[Service]
User=unisphere
Group=unisphere
WorkingDirectory=/srv/unisphere/app
EnvironmentFile=/srv/unisphere/app/.env
ExecStart=/srv/unisphere/app/.venv/bin/gunicorn -k eventlet -w 1 -b 127.0.0.1:8000 --timeout 120 run:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now unisphere
curl http://127.0.0.1:8000/health      # {"status":"ok"}
```

## 7. Nginx + HTTPS

`/etc/nginx/sites-available/unisphere`:

```nginx
server {
    listen 80;
    server_name unisphere.example.com;
    client_max_body_size 10M;          # must be >= MAX_UPLOAD_MB

    location /static/ {
        alias /srv/unisphere/app/app/static/;
        expires 7d;
    }

    location /socket.io/ {
        proxy_pass http://127.0.0.1:8000/socket.io/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/unisphere /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d unisphere.example.com     # installs the TLS cert and redirects HTTP→HTTPS
```

With HTTPS in place keep `SESSION_COOKIE_SECURE=true`.

## 8. Scaling beyond one worker

Socket.IO keeps per-connection state in the worker. To run several Gunicorn workers or several servers:

1. Install Redis (`sudo apt install redis-server`).
2. Set `SOCKETIO_MESSAGE_QUEUE=redis://localhost:6379/0` in `.env`.
3. Raise `-w` in the systemd unit (still `-k eventlet`).
4. Enable sticky sessions on any load balancer in front of Nginx (`ip_hash` in an Nginx `upstream`).

Without Socket.IO, chat still works: the client falls back to polling `GET /api/conversations/<id>/messages` every few seconds, and the plain-form send endpoint works with JavaScript disabled.

## 9. Updating

```bash
cd /srv/unisphere/app
sudo -u unisphere git pull
sudo -u unisphere .venv/bin/pip install -r requirements.txt
sudo -u unisphere env FLASK_APP=run.py .venv/bin/flask db upgrade
sudo systemctl restart unisphere
```

## 10. Checklist

- [ ] `SECRET_KEY` set and not committed
- [ ] MySQL password rotated from the dev default
- [ ] `UPLOAD_FOLDER` on persistent storage and backed up
- [ ] `flask db upgrade` applied
- [ ] HTTPS working, `SESSION_COOKIE_SECURE=true`
- [ ] `/health` returns 200 behind Nginx
- [ ] Only one eventlet worker, or Redis queue configured
