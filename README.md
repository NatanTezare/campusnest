# CampusNest

A web system that helps USIU-Africa students find off-campus hostels: search by name, rank hostels
against your budget / distance / amenities with a **fuzzy-logic engine**, compare hostels side by side,
and read or leave reviews. Hostel owners add and edit their own listings (with photos).

**Stack (same approach as SmartKeja):** Python + FastAPI backend, React (Vite) frontend, SQLite in dev
(PostgreSQL by setting `DATABASE_URL`), JWT auth with two roles: `student` and `owner`.

```
campusnest-app/
├── backend/
│   ├── app/
│   │   ├── main.py          app + CORS + static photo serving
│   │   ├── models.py        User, Hostel, RoomType, Amenity, hostel_amenity, Review, Photo, Flag   (= ER diagram)
│   │   ├── scoring.py       fuzzy-logic recommendation engine (pure Python, unit-tested)
│   │   ├── security.py      PBKDF2 password hashing, JWT, role guards
│   │   ├── schemas.py       request/response validation
│   │   ├── routers/         auth.py · hostels.py · reviews.py · feedback.py
│   │   ├── import_hostels.py  bulk-load real hostels from a CSV file
│   │   └── seed.py          sample data + demo accounts
│   └── tests/               50 tests (scoring, API, evaluation, importer, deployment)
├── frontend/src/            React app: pages/, components/, context.jsx, api.js
├── data/hostels_template.csv   template for the CSV importer
├── render.yaml              Render blueprint for the backend (see Deploying)
├── backend/perf_check.py    speed test with 500 hostels (NFR2 evidence)
└── e2e/e2e_smoke.py         optional browser test (Playwright)
```

## Run it

### 1. Backend (terminal 1)
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows      (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m app.seed              # creates the DB + sample hostels + demo accounts
python -m uvicorn app.main:app --reload --port 8000     # 'python -m' avoids PATH problems on Windows
```
API docs (try every endpoint in the browser): http://localhost:8000/docs

### 2. Frontend (terminal 2)
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173

**Demo accounts:** student `student@usiu.ac.ke / student123` · owner `owner@usiu.ac.ke / owner123`
(or create your own on the Create account tab, choosing Student or Hostel owner).

### Database (SQLite by default, PostgreSQL + DBeaver recommended)
The default is a SQLite file, `backend/campusnest.db`. To use PostgreSQL instead:
1. Install PostgreSQL (remember the `postgres` password you set) and create an empty database called `campusnest`
   (in DBeaver: right-click *Databases* → *Create New Database*).
2. In `backend/`, copy `.env.example` to `.env` and put your password in `DATABASE_URL`.
3. `pip install -r requirements.txt` (includes the `psycopg` driver), then `python -m app.seed`
   and start the server. Tables are created automatically on startup.
4. In DBeaver: *New Database Connection* → *PostgreSQL* → host `localhost`, port `5432`, database `campusnest`,
   user `postgres`, your password → *Test Connection*. Browse **Databases → campusnest → Schemas → public → Tables**.

To look at the SQLite file in DBeaver instead: *New Database Connection* → *SQLite* → path to `backend/campusnest.db`.
Tables: `users`, `hostels`, `room_types`, `amenities`, `hostel_amenity`, `reviews`, `photos`, `flags`.

**After a schema change** (like adding room types) an existing database keeps its old tables. For development data run
`python -m app.seed --reset` once: it drops all tables, recreates them and loads the sample data.
(Never use `--reset` on real data; for that you would add a migration tool such as Alembic.)

### Tests
```bash
cd backend && python -m pytest -q          # 50 tests (SQLite)
# against PostgreSQL:  TEST_DATABASE_URL=postgresql+psycopg://postgres:PASSWORD@localhost:5432/campusnest_test python -m pytest -q
```

### Settings (optional environment variables)
| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./campusnest.db` | e.g. `postgresql+psycopg://user:pass@host/db` (or put it in `backend/.env`) |
| `SECRET_KEY` | dev value | **Change in production** (JWT signing) |
| `CORS_ORIGINS` | localhost:5173 | comma-separated allowed frontend origins |
| `VITE_API_URL` | *(empty, uses dev proxy)* | backend URL when the frontend is deployed separately |

## Evaluation page (Objective v)
Students open **Feedback** in the nav bar and answer five short questions: hours the old way took, minutes it took with
CampusNest, ease (1-5), would they recommend it, and a comment. One response per student (sending again updates it).
`GET /api/feedback/summary` (and the "Results so far" card) report the average ease, the share who would recommend,
and **time saved** = `1 - (avg CampusNest hours / avg old-way hours)`, calculated only from students who answered both
time questions. Use these numbers in your testing/evaluation chapter. Individual answers are visible in DBeaver (`feedback` table).

## Importing REAL hostels from a CSV
1. Copy `data/hostels_template.csv`, delete the two EXAMPLE rows and fill in your real hostels (Excel / Google Sheets, save as CSV).
   `amenities` are separated by `;`. `rooms` look like `Single room:11000;Twin sharing:7500;Studio:16000:full`
   (price = KES per person per month, add `:full` if that room type is fully booked).
2. Create (or choose) a hostel-owner account on the website, e.g. `owner@usiu.ac.ke`.
3. From `backend/`, check the file first, then import:
```bash
python -m app.import_hostels ../data/hostels.csv --owner owner@usiu.ac.ke --dry-run
python -m app.import_hostels ../data/hostels.csv --owner owner@usiu.ac.ke
```
Rows with problems are listed with their line number and what to fix; hostels the owner already has are skipped,
so re-running is safe. Photos are added afterwards by the owner through *Edit listing*.

## Room types
A hostel has one or more **room types** (Single room, Twin sharing, Triple sharing, Bedsitter, Studio), each with its
own price and Open/Full status. **Prices are per person per month**, so a twin room shows each person's share.
- The hostel shows *from KES X*, the cheapest room that is still open.
- If a student picks a room type, hostels without it are left out and each hostel is scored by that room.
  With *Any*, each hostel is scored by its best-fitting room (the "Best fit" line in *Why this match?*).
- A hostel counts as fully booked only when every room type is full.
- Owners edit rooms in the listing form; removing a row removes that room type.

## How the recommendation works (Objective iii)
Each criterion becomes a fuzzy membership degree between 0 and 1 (`falling()` in `scoring.py`):

| Criterion | Full score until | Reaches 0 at | Weight |
|---|---|---|---|
| Price | student's budget | 150% of budget | 0.35 |
| Distance | student's max distance | 2× max distance | 0.25 |
| Amenities | – | share of wanted amenities present | 0.30 |
| Rating | – | Bayesian-smoothed review average (few reviews ≈ neutral) | 0.10 |

The weighted sum is multiplied by one fuzzy rule: **IF price is too high AND distance is too far THEN penalise**
(`1 − 0.5·min(1−price, 1−distance)`). Fully booked hostels are shown but halved. Every result carries
plain-English `reasons` ("Within your budget", "Missing: Kitchen", …), shown as *Why this match?*.
Weights can be overridden per request (`weights` in `POST /api/hostels/recommend`).

## API summary (`/api`)
| Method & path | Who | Purpose |
|---|---|---|
| `POST /auth/register`, `/auth/login`, `GET /auth/me` | all | accounts (FR1) |
| `GET /hostels?q=` | all | list / search by name |
| `POST /hostels/recommend` | all | ranked matches with scores + reasons (FR2, FR3) |
| `GET /hostels/compare?ids=1,2,3` | all | side-by-side + best value per row (FR4) |
| `GET /hostels/{id}` | all | detail with reviews (FR8) |
| `POST /hostels`, `PUT/DELETE /hostels/{id}` | owner (own) | add / edit / delete listing incl. its `rooms` (FR5) |
| `POST /hostels/{id}/photos`, `DELETE …/photos/{pid}` | owner (own) | photo upload (JPEG/PNG/WebP ≤ 5 MB, max 6) |
| `GET /hostels/mine` | owner | my hostels |
| `POST /hostels/{id}/reviews` | student | rate / review, one per student (FR6) |
| `POST /hostels/{id}/flag` | student | report inaccurate listing (FR7) |

## Deploying (live link)
Three free services, each doing one job:

| Part | Service | Why |
|---|---|---|
| Database | **Neon** (Postgres) | free and does not expire (Render's free database is deleted after 30 days) |
| Backend API | **Render** web service (`render.yaml`) | free; it *sleeps after ~15 min idle* and takes about a minute to wake |
| Frontend | **Vercel** (`frontend/vercel.json`) | free static hosting |

1. **Neon:** create a project and copy the connection string (`postgresql://...?sslmode=require`).
2. **Render:** New → Blueprint → pick the GitHub repo. Set `DATABASE_URL` (the Neon string) and `CORS_ORIGINS` (your Vercel URL).
   `SECRET_KEY` is generated automatically. Check `https://<your-api>.onrender.com/api/health`.
3. **Vercel:** import the repo, root directory `frontend`, add the environment variable `VITE_API_URL` = your Render URL
   (no trailing slash), then deploy.
4. **Load data into Neon from your laptop** (no server shell needed): put the Neon string in `backend/.env` as
   `DATABASE_URL=...`, run `python -m app.seed` or `python -m app.import_hostels ...`, then remove it from `.env`.
- Photos are compressed to JPEG (max 1280 px, location metadata removed) and stored **in the database**, so they survive
  hosts that wipe their disk. Before a demo, open the API URL once to wake the sleeping server.
- With `ENVIRONMENT=production` the app refuses to start with the default secret key.
- Speed check: `cd backend && python perf_check.py` (500 hostels, limit 3,000 ms).

## Notes
- Sample hostels in `seed.py` are **placeholders**; replace them with the real data from your survey and owners.
- Reviewers appear by first name only. Photos are checked by file signature, not just the extension.
- Browser smoke test (needs `pip install playwright && playwright install chromium`, both servers running):
  `python e2e/e2e_smoke.py`
