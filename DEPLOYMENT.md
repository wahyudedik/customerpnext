# Qalcuity ERP — Deployment Guide (AAPanel)

> **Platform:** VPS + AAPanel + Docker
> **Target:** Production deployment di `qalcuity.com`
> **Last Updated:** 2026-08-25

---

## ⚠️ CRITICAL — Docker Volume Mount Issue

> **⚠️ CRITICAL:** In this Docker setup, the host's `apps/qalcuity/` directory is NOT shared with the container. Always run `git pull` INSIDE the container via `docker compose exec backend`. Running `git pull` on the host only updates the host copy, which the container never reads.

**Why this matters:**

The `docker-compose.yml` uses **Docker named volumes** (`apps:`, `sites:`, `bench-env:`) for the container's filesystem. These volumes are **independent** of the host's directory structure. When you run `git pull` on the VPS host at `/opt/qalcuity/frappe_docker/apps/qalcuity/`, it updates the **host's copy** — but the container reads from its own `apps` volume at `/home/frappe/frappe-bench/apps/qalcuity/`.

**Wrong approach:**
```bash
# ❌ This ONLY updates the host copy — container is UNAWARE
cd /opt/qalcuity/frappe_docker/apps/qalcuity && git pull origin main
```

**Correct approach:**
```bash
# ✅ This updates the code INSIDE the container where the app actually runs
docker compose exec backend bash -c "cd /home/frappe/frappe-bench/apps/qalcuity && git pull upstream main"
```

### Environment Context

| Item | Value |
|------|-------|
| VPS path (host) | `/opt/qalcuity/frappe_docker/` |
| App path (container) | `/home/frappe/frappe-bench/apps/qalcuity/` |
| Git remote inside container | `upstream` (verify with `git remote -v` inside container) |
| Host ↔ Container | **SEPARATE file copies** — volume mounts may not include apps directory on host |
| All `bench` commands | Must run **inside** the `backend` container |
| All `git pull` commands | Must run **inside** the `backend` container |

---

## Prerequisites

| Item | Detail |
|------|--------|
| VPS | Sudah terinstall AAPanel (port default: `8888` atau custom) |
| Docker | Installed via AAPanel → Docker menu |
| Domain | `qalcuity.com` pointing ke VPS IP (A Record) |
| GitHub | Repository `wahyudedik/customerpnext` |
| SSH Access | Atau via AAPanel Terminal |

---

## Tahap 1: Login ke AAPanel

1. Buka browser → `https://<VPS_IP>:8888` (atau port AAPanel kamu)
2. Login dengan akun AAPanel (username & password yang dibuat saat install)
3. Pastikan Docker sudah terinstall:
   - Klik menu **Docker** di sidebar kiri
   - Jika belum terinstall, klik **Docker** → **Install Docker**
   - Tunggu hingga status Docker menunjukkan **Running**

---

## Tahap 2: Buka Terminal di AAPanel

### 2.1 Akses Terminal

Ada 2 cara akses terminal:

**Cara A — AAPanel Terminal (Recommended)**
1. Klik menu **Terminal** di sidebar kiri AAPanel
2. Atau klik ikon **Terminal** di pojok kanan atas
3. Kamu sudah login sebagai `root`

**Cara B — SSH External**
```bash
ssh root@<VPS_IP>
```

### 2.2 Buat Working Directory

```bash
mkdir -p /opt/qalcuity
cd /opt/qalcuity
```

---

## Tahap 3: Clone & Setup Frappe Docker

### 3.1 Clone frappe_docker

```bash
cd /opt/qalcuity
git clone https://github.com/frappe/frappe_docker.git
cd frappe_docker
```

### 3.2 Buat `docker-compose.yml`

Buka AAPanel → **Files** (menu sidebar) → navigasi ke `/opt/qalcuity/frappe_docker/` → buat/edit file `docker-compose.yml`:

Atau via terminal:
```bash
cat > /opt/qalcuity/frappe_docker/docker-compose.yml << 'EOF'
services:
  backend:
    image: frappe/erpnext:v15.30.0
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - apps:/home/frappe/frappe-bench/apps
      - bench-env:/home/frappe/frappe-bench/env
    environment:
      - MARIADB_HOST=db
      - REDIS_CACHE=redis-cache:6379
      - REDIS_QUEUE=redis-queue:6379
      - SOCKETIO_PORT=9000
    depends_on:
      - db
      - redis-cache
      - redis-queue

  frontend:
    image: frappe/erpnext:v15.30.0
    command: ["nginx-entrypoint.sh"]
    ports:
      - "8080:8080"
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - apps:/home/frappe/frappe-bench/apps
    environment:
      - BACKEND=backend:8000
      - SOCKETIO=websocket:9000
      - FRAPPE_SITE_NAME_HEADER=qalcuity.com
    depends_on:
      - backend
      - websocket

  websocket:
    image: frappe/erpnext:v15.30.0
    command: ["node", "/home/frappe/frappe-bench/apps/frappe/socketio.js"]
    ports:
      - "9000:9000"
    volumes:
      - sites:/home/frappe/frappe-bench/sites
    depends_on:
      - backend

  queue-short:
    image: frappe/erpnext:v15.30.0
    command: ["bench", "worker", "--queue", "short"]
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - apps:/home/frappe/frappe-bench/apps
      - bench-env:/home/frappe/frappe-bench/env
    environment:
      - REDIS_CACHE=redis-cache:6379
      - REDIS_QUEUE=redis-queue:6379
    depends_on:
      - redis-queue

  queue-long:
    image: frappe/erpnext:v15.30.0
    command: ["bench", "worker", "--queue", "long,default,short"]
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - apps:/home/frappe/frappe-bench/apps
      - bench-env:/home/frappe/frappe-bench/env
    environment:
      - REDIS_CACHE=redis-cache:6379
      - REDIS_QUEUE=redis-queue:6379
    depends_on:
      - redis-queue

  queue-default:
    image: frappe/erpnext:v15.30.0
    command: ["bench", "worker", "--queue", "default,short"]
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - apps:/home/frappe/frappe-bench/apps
      - bench-env:/home/frappe/frappe-bench/env
    environment:
      - REDIS_CACHE=redis-cache:6379
      - REDIS_QUEUE=redis-queue:6379
    depends_on:
      - redis-queue

  scheduler:
    image: frappe/erpnext:v15.30.0
    command: ["bench", "schedule"]
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - apps:/home/frappe/frappe-bench/apps
      - bench-env:/home/frappe/frappe-bench/env
    environment:
      - REDIS_CACHE=redis-cache:6379
      - REDIS_QUEUE=redis-queue:6379
    depends_on:
      - redis-queue

  db:
    image: mariadb:10.11
    volumes:
      - db-data:/var/lib/mysql
    environment:
      - MYSQL_ROOT_PASSWORD=admin
      - MYSQL_DATABASE=erpnext
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

  redis-cache:
    image: redis:alpine

  redis-queue:
    image: redis:alpine

  cron:
    image: frappe/erpnext:v15.30.0
    command: ["sleep", "infinity"]
    volumes:
      - sites:/home/frappe/frappe-bench/sites
      - apps:/home/frappe/frappe-bench/apps
      - bench-env:/home/frappe/frappe-bench/env
    environment:
      - REDIS_CACHE=redis-cache:6379
      - REDIS_QUEUE=redis-queue:6379
    depends_on:
      - backend

volumes:
  sites:
  apps:
  bench-env:
  db-data:
EOF
```

### 3.3 Jalankan Docker Compose via AAPanel

**Cara A — Via AAPanel Docker Menu (Recommended)**

1. Buka AAPanel → klik menu **Docker** di sidebar
2. Klik tab **Compose** (atau **Docker Compose**)
3. Klik **Create Compose** / **创建编排**
4. Isi:
   - **Name:** `qalcuity-erp`
   - **Path:** `/opt/qalcuity/frappe_docker`
   - **Compose:** pastikan path ke `docker-compose.yml` benar
5. Klik **Start** / **启动**
6. Tunggu semua container status **Running**:
   - `backend` ✅
   - `frontend` ✅
   - `websocket` ✅
   - `queue-short` ✅
   - `queue-long` ✅
   - `queue-default` ✅
   - `scheduler` ✅
   - `db` ✅
   - `redis-cache` ✅
   - `redis-queue` ✅
   - `cron` ✅

**Cara B — Via Terminal**
```bash
cd /opt/qalcuity/frappe_docker
docker compose up -d
```

> **⚠️ Penting:** Jika mengubah `docker-compose.yml` (menambah volume, port, dll), gunakan `docker compose up -d --force-recreate` untuk menerapkan perubahan. `docker compose restart` TIDAK mengubah volume mounts atau port mapping yang sudah ada.

### 3.4 Verifikasi Container

Di terminal AAPanel:
```bash
cd /opt/qalcuity/frappe_docker
docker compose ps
```

Semua container harus **Up**. Jika ada yang **Exit** atau **Restarting**, cek log:
```bash
docker compose logs backend
docker compose logs db
```

### 3.5 Setup Site Config (HTTPS Detection)

Agar Frappe mendeteksi HTTPS dengan benar dari reverse proxy:

```bash
cd /opt/qalcuity/frappe_docker
docker compose exec backend bench --site qalcuity.com set-config scheme https
docker compose exec backend bench --site qalcuity.com set-config host_name https://qalcuity.com
```

### 3.6 Build Assets & Sync ke Frontend

Setelah site dan app terinstall, build aset CSS/JS:

```bash
cd /opt/qalcuity/frappe_docker
docker compose exec backend bench build --force
```

Tunggu hingga selesai (40-60 detik). Lalu **copy aset dari backend ke frontend**:

```bash
# Copy assets dari backend ke frontend
docker compose exec backend tar czf /tmp/assets.tar.gz -C /home/frappe/frappe-bench/sites assets/ && \
docker cp $(docker compose ps -q backend):/tmp/assets.tar.gz /tmp/qalcuity-assets.tar.gz && \
docker cp /tmp/qalcuity-assets.tar.gz $(docker compose ps -q frontend):/tmp/ && \
docker compose exec frontend tar xzf /tmp/qalcuity-assets.tar.gz -C /home/frappe/frappe-bench/sites/ && \
docker compose exec frontend nginx -s reload
```

> **⚠️ Jangan skip asset sync!** Docker named volume TIDAK auto-sync antara backend dan frontend. Setelah `bench build`, frontend masih membaca aset LAMA. Harus copy manual.

---

## Tahap 4: Buat Site & Install App

### 4.1 Masuk ke Backend Container

```bash
cd /opt/qalcuity/frappe_docker
docker compose exec backend bash
```

### 4.2 Buat Site Baru

```bash
bench new-site qalcuity.com \
  --mariadb-root-password admin \
  --admin-password admin123 \
  --install-app erpnext
```

> **Catatan:** `admin123` adalah password Administrator ERPNext. Ganti dengan password yang kuat untuk production.

### 4.3 Clone Qalcuity App

```bash
cd /home/frappe/frappe-bench/apps
git clone https://github.com/wahyudedik/customerpnext.git qalcuity
```

### 4.4 Install Qalcuity ke Site

```bash
bench --site qalcuity.com install-app qalcuity
```

### 4.5 Jalankan Migrate & Restart

```bash
bench --site qalcuity.com migrate
bench restart
```

### 4.6 Exit dari Container

```bash
exit
```

---

## Tahap 5: Setup Domain & SSL

### 5.1 Pastikan Domain DNS Sudah Benar

Di domain registrar (Namecheap/Cloudflare/dll), pastikan:
```
Type: A
Name: @
Value: <VPS_IP>
```

Tunggu DNS propagasi (5-30 menit).

### 5.2 Setup Reverse Proxy via AAPanel

> **⚠️ Penting:** JANGAN pakai menu **Website → Add Site**. Itu untuk website statis/PHP.
> Untuk Docker containers, gunakan menu **Proxy Project**.

1. Buka AAPanel → menu **Website** (atau **网站**) di sidebar
2. Klik **Proxy Project** (atau **添加反向代理项目**)
3. Isi form:
   - **Domain:** `qalcuity.com`
   - **Note:** `Qalcuity ERP`
   - **SSL:** Centang **Enable SSL** → pilih **Let's Encrypt**
   - **Proxy Target:** `http://127.0.0.1:8080`
   - **Support WebSocket:** Centang / Enable
4. Klik **Submit** / **确定**
5. Tunggu SSL certificate ter-generate

> **Cara Alternatif (jika Proxy Project tidak tersedia):**
> 1. Buka AAPanel → **Website** → **Add Site**
> 2. Isi domain `qalcuity.com`, pilih **Static**, enable SSL
> 3. Setelah site dibuat, edit Nginx config manual:
>    - Hapus semua location block yang ada
>    - Tambahkan `proxy_pass http://127.0.0.1:8080` dengan WebSocket support

### 5.3 Verifikasi

Buka browser → `https://qalcuity.com`
- Harus loading halaman login Qalcuity (dengan CSS/JS terload)
- SSL certificate valid (ikon gembok 🔒)
- Tidak ada error 404 di console browser

---

## Tahap 6: Environment Variables (Qalcuity Config)

### 6.1 Masuk ke Container & Buat .env

```bash
cd /opt/qalcuity/frappe_docker
docker compose exec backend bash
cd /home/frappe/frappe-bench/sites/qalcuity.com
```

### 6.2 Buat File `.env`

```bash
cat > .env << 'EOF'
# ============================================
# Qalcuity ERP Configuration
# ============================================

# App Info
QALCUITY_APP_NAME=Qalcuity ERP
QALCUITY_VERSION=0.0.1
QALCUITY_ENV=production

# Site
SITE_NAME=qalcuity.com
SITE_URL=https://qalcuity.com
SUPERADMIN_EMAIL=info@qalcuity.com
COMPANY_NAME=Qalcuity
CURRENCY=IDR

# Payment — Manual Transfer (Default)
BANK_NAME=Bank BRI
BANK_ACCOUNT_NAME=WAHYU DEDIK DWI ASTONO
BANK_ACCOUNT_NUMBER=211801008728508
BANK_BRANCH=-

# Xendit (kosongkan jika belum siap)
XENDIT_API_KEY=
XENDIT_CALLBACK_TOKEN=
XENDIT_API_URL=https://api.xendit.co

# WhatsApp
WHATSAPP_PHONE_NUMBER=6281529211963
WHATSAPP_ENABLED=false

# Notifications
NOTIFY_SUPERADMIN_ON_PAYMENT=true
SUPERADMIN_NOTIFICATION_EMAIL=info@qalcuity.com
NOTIFY_ON_APPROVAL=true
NOTIFY_ON_REJECTION=true
NOTIFY_ON_EXPIRY_WARNING=true

# Security
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
API_RATE_LIMIT=100
SESSION_TIMEOUT=600

# Email (SMTP)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=info@qalcuity.com
SMTP_PASSWORD=<app-password-gmail>
SMTP_USE_TLS=true
NOTIFICATION_EMAIL=info@qalcuity.com
EOF
```

> **Penting:** Ganti `<app-password-gmail>` dengan App Password dari Google Account.

### 6.3 Generate Secret Key

```bash
# Jalankan di dalam container
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
sed -i "s|SECRET_KEY=\$(python3.*|$SECRET_KEY|" .env
```

### 6.4 Exit Container

```bash
exit
```

---

## Tahap 7: Upload Custom App Code

### 7.1 Option A — Git Pull INSIDE Container (Recommended)

> **⚠️ CRITICAL:** `git pull` must run INSIDE the Docker container, not on the host. See [Docker Volume Mount Issue](#⚠️-critical--docker-volume-mount-issue) above.

Setelah push dari lokal ke GitHub, jalankan di VPS terminal:

**Step-by-step (manual):**

```bash
cd /opt/qalcuity/frappe_docker

# Step 1: Pull code INSIDE the container
docker compose exec backend bash -c "cd /home/frappe/frappe-bench/apps/qalcuity && git pull upstream main"

# Step 2: Run bench commands inside the container
docker compose exec backend bench --site qalcuity.com migrate
docker compose exec backend bench --site qalcuity.com clear-cache
docker compose exec backend bench build --force

# Step 3: Copy assets from backend to frontend + reload nginx
docker compose exec backend tar czf /tmp/assets.tar.gz -C /home/frappe/frappe-bench/sites assets/ && \
docker cp $(docker compose ps -q backend):/tmp/assets.tar.gz /tmp/qalcuity-assets.tar.gz && \
docker cp /tmp/qalcuity-assets.tar.gz $(docker compose ps -q frontend):/tmp/ && \
docker compose exec frontend tar xzf /tmp/qalcuity-assets.tar.gz -C /home/frappe/frappe-bench/sites/ && \
docker compose exec frontend nginx -s reload
```

**Complete one-liner (copy-paste):**

```bash
docker compose exec backend bash -c "cd /home/frappe/frappe-bench/apps/qalcuity && git pull upstream main" && docker compose exec backend bench --site qalcuity.com migrate && docker compose exec backend bench --site qalcuity.com clear-cache && docker compose exec backend bench build --force && docker compose exec backend tar czf /tmp/assets.tar.gz -C /home/frappe/frappe-bench/sites assets/ && docker cp $(docker compose ps -q backend):/tmp/assets.tar.gz /tmp/qalcuity-assets.tar.gz && docker cp /tmp/qalcuity-assets.tar.gz $(docker compose ps -q frontend):/tmp/ && docker compose exec frontend tar xzf /tmp/qalcuity-assets.tar.gz -C /home/frappe/frappe-bench/sites/ && docker compose exec frontend nginx -s reload
```

> **Note:** The git remote name inside the container is `upstream` (not `origin`). Verify with `docker compose exec backend bash -c "cd /home/frappe/frappe-bench/apps/qalcuity && git remote -v"`.

### 7.2 Option B — Upload via AAPanel File Manager

1. Buka AAPanel → **Files** di sidebar
2. Navigasi ke `/opt/qalcuity/frappe_docker/`
3. Upload file-file yang diubah (hati-hati, lebih baik pakai Git)
4. Lalu jalankan migrate via terminal

---

## Tahap 8: Testing

### 8.1 Akses Site

Buka browser → `https://qalcuity.com`

### 8.2 Login

- URL: `https://qalcuity.com/login`
- Username: `Administrator`
- Password: `admin123` (atau yang di-set saat `bench new-site`)

### 8.3 Test Full Flow

| Step | URL | Action |
|------|-----|--------|
| 1 | `/register` | Buat customer baru |
| 2 | `/pricing` | Lihat plan yang tersedia |
| 3 | `/checkout` | Pilih plan → submit payment |
| 4 | `/admin-reviews` | Login sebagai admin → approve/reject |
| 5 | `/dashboard` | Lihat subscription status |
| 6 | `/profile` | Edit profil & ganti password |
| 7 | `/account-status` | Detail status langganan |
| 8 | `/subscription-history` | Riwayat perubahan langganan |

### 8.4 Test Bell Icon Notifications

1. Login sebagai Administrator
2. Klik bell icon 🔔 di header
3. Harus muncul notifikasi jika ada payment baru

### 8.5 Test Checkout Bank Accounts

1. Login sebagai customer
2. Buka `/checkout`
3. Harus tampil 4 rekening bank (BRI, JAGO, BTN, BSI)
4. Test copy nomor rekening

---

## Tahap 9: Update Workflow (Development)

> **⚠️ REMINDER:** All `git pull` and `bench` commands must run INSIDE the Docker container. See [Docker Volume Mount Issue](#⚠️-critical--docker-volume-mount-issue).

### Flow: Lokal → Git → VPS Container

```
┌─────────────────────┐
│  LOCAL (VS Code)    │
│  Coding & Edit      │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  git push origin    │
│  main               │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────────────────┐
│  VPS Docker Container           │
│  (backend)                      │
│                                 │
│  1. git pull upstream main      │
│     (INSIDE container!)         │
│  2. bench migrate               │
│  3. bench clear-cache           │
│  4. bench build --force         │
│  5. force-recreate frontend     │
└─────────────────────────────────┘
```

### Step-by-Step Update

**1. Di Lokal — Edit & Push**
```bash
# Edit code di VS Code...
git add .
git commit -m "Sprint X: description"
git push origin main
```

**2. Di VPS — Pull & Update (INSIDE Container)**

Buka AAPanel → **Terminal** → jalankan:

```bash
cd /opt/qalcuity/frappe_docker

# Step 1: Pull code INSIDE the container
docker compose exec backend bash -c "cd /home/frappe/frappe-bench/apps/qalcuity && git pull upstream main"

# Step 2: Migrate database
docker compose exec backend bench --site qalcuity.com migrate

# Step 3: Clear cache
docker compose exec backend bench --site qalcuity.com clear-cache

# Step 4: Rebuild assets (if UI/CSS/JS changed)
docker compose exec backend bench build --force

# Step 5: Copy assets dari backend ke frontend + reload nginx
docker compose exec backend tar czf /tmp/assets.tar.gz -C /home/frappe/frappe-bench/sites assets/ && \
docker cp $(docker compose ps -q backend):/tmp/assets.tar.gz /tmp/qalcuity-assets.tar.gz && \
docker cp /tmp/qalcuity-assets.tar.gz $(docker compose ps -q frontend):/tmp/ && \
docker compose exec frontend tar xzf /tmp/qalcuity-assets.tar.gz -C /home/frappe/frappe-bench/sites/ && \
docker compose exec frontend nginx -s reload
```

> **⚠️ Jangan lupa sync assets!** Docker named volume TIDAK auto-sync antara backend dan frontend. `docker compose restart` TIDAK akan membuat frontend melihat aset baru.

### Shortcut Command (Copy-Paste)

```bash
docker compose exec backend bash -c "cd /home/frappe/frappe-bench/apps/qalcuity && git pull upstream main" && docker compose exec backend bench --site qalcuity.com migrate && docker compose exec backend bench --site qalcuity.com clear-cache && docker compose exec backend bench build --force && docker compose exec backend tar czf /tmp/assets.tar.gz -C /home/frappe/frappe-bench/sites assets/ && docker cp $(docker compose ps -q backend):/tmp/assets.tar.gz /tmp/qalcuity-assets.tar.gz && docker cp /tmp/qalcuity-assets.tar.gz $(docker compose ps -q frontend):/tmp/ && docker compose exec frontend tar xzf /tmp/qalcuity-assets.tar.gz -C /home/frappe/frappe-bench/sites/ && docker compose exec frontend nginx -s reload
```

> **Note:** Run this from `/opt/qalcuity/frappe_docker/` on the VPS host. The entire command executes inside the `backend` container.

---

## Troubleshooting

### Container Not Starting

**Di AAPanel:**
1. Docker → klik tab **Containers**
2. Cari container yang bermasalah
3. Klik **Log** / **日志** untuk melihat error

**Di Terminal:**
```bash
cd /opt/qalcuity/frappe_docker
docker compose logs backend
docker compose logs db
docker compose logs scheduler
```

### Database Connection Error

```bash
cd /opt/qalcuity/frappe_docker
docker compose exec backend bash

# Cek MariaDB running
bench --site qalcuity.com mariadb
# atau
docker compose exec db mysql -u root -padmin -e "SHOW DATABASES;"
```

### App Not Found

```bash
docker compose exec backend bench --site qalcuity.com list-apps
```

Jika `qalcuity` tidak ada di list:
```bash
docker compose exec backend bash
cd /home/frappe/frappe-bench
bench --site qalcuity.com install-app qalcuity
bench --site qalcuity.com migrate
bench restart
```

### White Page / 500 Error

```bash
# Cek error log
docker compose exec backend cat /home/frappe/frappe-bench/sites/qalcuity.com/logs/frappe.log | tail -50
```

### Reset Site (HATI-HATI: Data Hilang!)

```bash
docker compose exec backend bench drop-site qalcuity.com

docker compose exec backend bench new-site qalcuity.com \
  --mariadb-root-password admin \
  --admin-password admin123 \
  --install-app erpnext

docker compose exec backend bash -c "cd /home/frappe/frappe-bench/apps/qalcuity && bench --site qalcuity.com install-app qalcuity && bench --site qalcuity.com migrate && bench restart"
```

### SSL Certificate Expired

1. AAPanel → **Website** → klik site `qalcuity.com`
2. Klik **SSL** / **SSL证书**
3. Klik **Renew** / **续签**
4. Jika gagal, cek DNS sudah benar

### CSS / JS 404 (Halaman Login Tanpa Styling)

Masalah umum: halaman login muncul tapi tanpa CSS/JS (terlihat seperti halaman polos).

**Penyebab:** Frontend container tidak melihat file aset yang sudah di-build.

**Solusi:**

```bash
cd /opt/qalcuity/frappe_docker

# 1. Build aset
docker compose exec backend bench build --force

# 2. Copy assets dari backend ke frontend
docker compose exec backend tar czf /tmp/assets.tar.gz -C /home/frappe/frappe-bench/sites assets/ && \
docker cp $(docker compose ps -q backend):/tmp/assets.tar.gz /tmp/qalcuity-assets.tar.gz && \
docker cp /tmp/qalcuity-assets.tar.gz $(docker compose ps -q frontend):/tmp/ && \
docker compose exec frontend tar xzf /tmp/qalcuity-assets.tar.gz -C /home/frappe/frappe-bench/sites/ && \
docker compose exec frontend nginx -s reload

# 3. Hard refresh di browser: Ctrl+Shift+R
```

> **⚠️ Mengapa harus copy assets manual?**
> Docker named volume TIDAK auto-sync antara backend dan frontend container.
> Setelah `bench build`, aset baru hanya ada di backend. Frontend masih membaca aset LAMA.
> Harus copy manual menggunakan tar + docker cp.

**Cara verifikasi:**
```bash
# Cek apakah frontend melihat file CSS baru
docker compose exec frontend ls /home/frappe/frappe-bench/sites/assets/frappe/dist/css/

# Bandingkan dengan backend
docker compose exec backend ls /home/frappe/frappe-bench/sites/assets/frappe/dist/css/
```

Jika hash file berbeda antara frontend dan backend, berarti assets belum di-sync — jalankan command copy di atas lagi.

### Socket.IO / WebSocket Error

Pastikan Nginx config memiliki block `/socket.io` (lihat Tahap 5.3).

---

## File Structure di VPS

```
/opt/qalcuity/
├── frappe_docker/
│   ├── docker-compose.yml          ← Main compose file
│   └── .env                        ← Docker env (opsional)
│
└── (Docker Volumes)
    ├── sites/
    │   └── qalcuity.com/
    │       ├── site_config.json    ← Site config
    │       ├── .env                ← Qalcuity env vars
    │       ├── private/            ← Private files
    │       ├── public/             ← Public files
    │       └── logs/               ← Log files
    │
    └── apps/
        └── qalcuity/               ← Custom app code (via Git)
            └── qalcuity/
                ├── hooks.py
                ├── api/
                ├── templates/
                ├── public/
                └── ...
```

---

## Quick Reference — AAPanel Navigation

| Task | Menu Path |
|------|-----------|
| Terminal | Sidebar → **Terminal** |
| File Manager | Sidebar → **Files** |
| Docker Containers | Sidebar → **Docker** → **Containers** tab |
| Docker Compose | Sidebar → **Docker** → **Compose** tab |
| Docker Images | Sidebar → **Docker** → **Images** tab |
| Website/Reverse Proxy | Sidebar → **Website** → **Add Site** |
| SSL Certificate | Sidebar → **Website** → Site → **SSL** |
| Nginx Config | Sidebar → **Website** → Site → **Settings** → **Config** |
| Database (phpMyAdmin) | Sidebar → **Database** → **phpMyAdmin** |
| Firewall | Sidebar → **Security** → **Firewall** |
| System Monitor | Sidebar → **Monitoring** → **System** |

---

## Notes

- **⚠️ Docker Volume Mount Issue:** Host's `apps/qalcuity/` is NOT shared with the container. Always `git pull` INSIDE the container via `docker compose exec backend`.
- **Local = Code Only** — tidak ada testing, tidak ada running server
- **VPS = Testing & Production** — semua testing dilakukan di VPS
- **Git = Source of Truth** — semua code harus ada di Git
- **Jangan edit langsung di VPS** — selalu edit di lokal, push ke Git, pull di VPS (inside container)
- **AAPanel = Management UI** — untuk manage Docker, domain, SSL, firewall
- **Port AAPanel default:** `8888` (atau custom saat install)
- **Docker Compose location (host):** `/opt/qalcuity/frappe_docker/`
- **App path (container):** `/home/frappe/frappe-bench/apps/qalcuity/`
- **Git remote inside container:** `upstream` (verify with `git remote -v` inside container)
- **Host ↔ Container files:** SEPARATE — volume mounts do NOT share the host's app directory
- **Frontend nginx port:** `8080` (bukan 80!) — frappe_docker image mendengarkan di port 8080
- **⚠️ CSS Asset Sync = wajib** setelah `bench build` — Docker named volume TIDAK auto-sync antara backend dan frontend. Harus copy manual: `tar + docker cp` (lihat Section 3.6)
- **`docker compose restart` TIDAK sync assets** — hanya restart process, tidak mengubah file di volume
- **site_config.json:** Pastikan `scheme=https` dan `host_name=https://qalcuity.com` agar HTTPS terdeteksi
- **All `bench` commands:** Must run inside the `backend` container via `docker compose exec backend`
- **All `git pull` commands:** Must run inside the `backend` container — never on the host
