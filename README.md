# UniSphere — Everything You Need. All in One Place.

UniSphere is a student-to-student marketplace built for **Ness Wadia College of Commerce (NWCC), Pune**. Students list textbooks, notes, calculators, stationery, hostel essentials and electronics, then buy and sell directly with classmates through private in-app chat.

Stack: **Flask 3 · SQLAlchemy · Flask-Migrate (Alembic) · MySQL 8 · Flask-Login · Flask-WTF (CSRF) · Flask-SocketIO · Pillow · Bootstrap 5**.

## Features

| Area | What works |
| --- | --- |
| Accounts | Register (first/last name, email, course, year), login/logout, edit profile, change password, public seller profile. Passwords are hashed with PBKDF2-SHA256; no college-email restriction. |
| Listings | Create / edit / delete, up to 5 images uploaded from your device (validated + re-encoded with Pillow, stored on disk), categories, condition, price in ₹, location, mark **Sold / Available**. Ownership enforced server-side. |
| Browse | Database-backed search (title/description), category / condition / price-range filters, sort (newest, price ↑, price ↓), pagination, clear empty states. Sold items are hidden by default. |
| Favourites | One-click save/unsave (AJAX with form fallback), dedicated page, unique per user+listing, sold badge on saved items. |
| Chat | Private buyer↔seller conversation per listing. Real-time via Socket.IO with automatic polling fallback; all messages persisted with sender + timestamp; unread counts; read receipts; outsiders are blocked. No self-chat. |
| Safety | Report a listing or a user (stored in DB, duplicates prevented), minimal admin review page (`flask make-admin`). CSRF on every form, server-side authorization everywhere, safe file serving. |

## Project layout

```
app/
  __init__.py      # application factory, error handlers, CLI (seed, make-admin)
  extensions.py    # db, migrate, login_manager, csrf, socketio
  models.py        # User, Listing, ListingImage, Favourite, Conversation, Message, Report
  constants.py     # courses, years, categories, conditions …
  utils.py         # secure image save/delete (Pillow)
  auth/ listings/ favourites/ chat/ reports/ admin/ main/   # blueprints
  templates/  static/
migrations/        # Alembic migrations
tests/             # pytest suite (runs against a MySQL test DB)
seed.py            # NWCC demo data
run.py             # dev entrypoint (Socket.IO server)
config.py
```

## Quick start (local development)

### 1. Prerequisites
* Python 3.10+
* MySQL 8.x running locally

### 2. Create the databases

```sql
CREATE DATABASE unisphere      CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE unisphere_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;  -- for pytest
CREATE USER 'unisphere'@'localhost' IDENTIFIED BY 'unisphere_dev_pw';
GRANT ALL PRIVILEGES ON unisphere.*      TO 'unisphere'@'localhost';
GRANT ALL PRIVILEGES ON unisphere_test.* TO 'unisphere'@'localhost';
FLUSH PRIVILEGES;
```

### 3. Install & configure

```bash
git clone <this-repo> unisphere && cd unisphere
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then edit SECRET_KEY / DATABASE_URL if needed
```

### 4. Run migrations, seed demo data, start

```bash
export FLASK_APP=run.py
flask db upgrade                # creates all tables
flask seed --reset              # optional: NWCC demo users, listings, chats (drops existing rows!)
python run.py                   # http://127.0.0.1:5000
```

Demo accounts (password **`Password123`**):

| Email | Who |
| --- | --- |
| aarav@demo.unisphere | TY B.COM seller |
| priya@demo.unisphere | SY BBA |
| rohan@demo.unisphere | FY BBA CA |
| sneha@demo.unisphere | TY BBA IB |
| admin@demo.unisphere | admin (can review reports at `/admin/reports`) |

Promote any account to admin with `flask make-admin someone@example.com`.

## Environment variables

See `.env.example`. Key ones:

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Session / CSRF signing key. **Required** in production. |
| `DATABASE_URL` | `mysql+pymysql://user:pass@host:3306/unisphere?charset=utf8mb4` |
| `TEST_DATABASE_URL` | Separate DB used by pytest (tables are created and dropped). |
| `UPLOAD_FOLDER` | Absolute path where listing images are stored (default `instance/uploads`). Must be persistent. |
| `MAX_CONTENT_LENGTH_MB` | Request size cap (default 25). Per-image cap is `MAX_IMAGE_SIZE_MB` (default 5). |
| `SOCKETIO_ASYNC_MODE` | `eventlet` (default) or `threading`. |
| `SOCKETIO_MESSAGE_QUEUE` | e.g. `redis://localhost:6379/0` when running more than one worker. |
| `SESSION_COOKIE_SECURE` | Set `true` behind HTTPS. |
| `DEFAULT_COLLEGE` | Pre-filled college name (default: Ness Wadia College of Commerce, Pune). |

## Migrations

```bash
flask db migrate -m "describe change"   # after editing app/models.py
flask db upgrade                        # apply
flask db downgrade                      # roll back one revision
```

## Tests

```bash
pytest -q          # uses TEST_DATABASE_URL; 19 tests covering auth, listings, uploads,
                   # ownership, search/filter/sort, favourites, chat privacy, reports, CSRF
```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for Gunicorn + eventlet, Nginx, HTTPS, persistent image storage and multi-worker Socket.IO setup.

## Scope notes

Deliberately **not** included: payments/UPI, delivery tracking, OTP or ID verification, AI features, external messaging redirects, large admin dashboards. The college field is free text so other colleges can be onboarded later.
