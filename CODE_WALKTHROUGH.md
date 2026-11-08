# CampusNest – Code Walkthrough & Viva Prep

Put this file in your project folder (e.g. `campusnest-app/docs/`) and open it in VS Code with **Ctrl+Shift+V** (preview).
Use **Ctrl+Shift+F** in VS Code to search the whole project for any phrase mentioned below.

---

## 1. The 60-second story (say this first)

> "CampusNest has three layers. The **React frontend** is what the student sees. When they search, it calls the
> **FastAPI backend** over a REST API. The backend scores each hostel with a **fuzzy-logic engine** and reads/writes
> **PostgreSQL** through SQLAlchemy. Students and hostel owners log in with JWT tokens, and the backend checks the
> role on every protected request, so a student can never add a hostel."

```
Browser (React, port 5173)
   │  fetch("/api/hostels/recommend")        ← frontend/src/api.js adds the login token
   ▼
Vite dev proxy  ──►  FastAPI (port 8000)     ← backend/app/main.py → routers/hostels.py
                        │  score_hostel()    ← backend/app/scoring.py  (the fuzzy logic)
                        ▼
                    SQLAlchemy models        ← backend/app/models.py
                        ▼
                    PostgreSQL (DBeaver shows these tables)
```

### What happens when a student clicks "Find hostels"
1. `pages/Search.jsx` saves the preferences in global state and goes to `/results`.
2. `pages/Results.jsx` runs `api.post('/hostels/recommend', prefs)` inside a `useEffect`.
3. `api.js` attaches `Authorization: Bearer <token>` and sends the request. Vite forwards `/api` to port 8000.
4. `routers/hostels.py → recommend()` loads all hostels, and for each room type calls `score_hostel(...)`.
   It keeps each hostel's best room, sorts by score, returns JSON.
5. `Results.jsx` draws one card per hostel with the "% match", the best room, and the "Why this match?" reasons.

---

## 2. Project map (what each file is for)

| File | Job |
|---|---|
| `backend/app/main.py` | Creates the app, allows the frontend (CORS), serves photos, creates tables + amenities on startup |
| `backend/app/models.py` | Database tables: `User, Hostel, RoomType, Amenity, hostel_amenity, Review, Photo, Flag` |
| `backend/app/schemas.py` | Validation of what the API accepts/returns (price > 0, rating 1–5, allowed amenities…) |
| `backend/app/scoring.py` | **The fuzzy-logic recommendation engine** (pure Python, no database) |
| `backend/app/security.py` | Password hashing, JWT tokens, `require_role("owner")` |
| `backend/app/routers/auth.py` | Register, login, "who am I" |
| `backend/app/routers/hostels.py` | Search, recommend, compare, owner add/edit/delete, photo upload |
| `backend/app/routers/reviews.py` | Student reviews and flagging |
| `backend/app/seed.py` | Loads demo hostels/accounts (`--reset` wipes and rebuilds) |
| `backend/tests/` | 28 automated tests |
| `frontend/src/api.js` | One `fetch` wrapper: adds token, turns errors into readable messages |
| `frontend/src/context.jsx` | Global state: logged-in user, compare list, search preferences, toast messages |
| `frontend/src/App.jsx` | The routes + `Guard` that blocks the wrong role from a page |
| `frontend/src/pages/*.jsx` | Login, Search, Results, HostelDetail, Compare, Dashboard, HostelForm |
| `frontend/src/styles.css` | All the colours and layout (USIU theme) |

---

## 3. "Change this for me" cheat sheet

After a **frontend** edit the browser refreshes by itself. After a **backend** edit uvicorn restarts by itself
(because of `--reload`). After editing `.env` you must restart uvicorn (Ctrl+C, run it again).

### Looks (all in `frontend/src/styles.css`)
| He says… | Do this |
|---|---|
| "Change the main colour" | Top of the file, `:root { --blue: #2B3990; … }` → change `--blue` (headers, buttons, prices all follow) |
| "Change the gold/yellow" | `--gold` (stars, the gold button) |
| "Change the background" | `--bg` |
| "Make buttons more/less round" | `.btn { … border-radius: 14px; … }` |
| "Make the header less round" | `.hero { … border-radius: 28px; … }` |
| "Change the font" | `html, body { font-family: … }` |
| "Make the app wider" | `.app { max-width: 460px; … }` |

### Text and labels
| He says… | Where |
|---|---|
| "Change the app title in the browser tab" | `frontend/index.html` → `<title>` |
| "Change the login heading" | `pages/Login.jsx` → the `<Hero title=… sub=…>` line |
| "Change the nav bar items/icons" | `components/Layout.jsx` → the `items` array |
| "Change the default budget/distance" | `context.jsx` → `useState(() => ({ budget: 15000, max_distance_km: 2, … }))` |
| "Change the slider limits" | `pages/Search.jsx` → `type="range" min="3000" max="30000"` and `min="0.3" max="5"` |

### Rules and limits
| He says… | Where |
|---|---|
| "Add a new amenity (e.g. Gym)" | Add `"Gym"` to `AMENITIES` in `backend/app/schemas.py` **and** `frontend/src/api.js`. The backend adds it to the database on startup. |
| "Add a new room type" | Same, with `ROOM_TYPES` in both files |
| "Allow 10 photos instead of 6" | `MAX_PHOTOS` in `backend/app/routers/hostels.py` **and** `pages/HostelForm.jsx` |
| "Max photo size" | `MAX_PHOTO_BYTES` in `routers/hostels.py` |
| "Compare 4 hostels" | `context.jsx` (`c.length >= 3`) and `routers/hostels.py` (`2 <= len(wanted) <= 3`) |
| "Password must be 8 characters" | `schemas.py` → `RegisterIn.password` `min_length=6`, and `minLength={6}` in `pages/Login.jsx` |
| "Stay logged in longer" | `security.py` → `TOKEN_HOURS = 12` |

### The recommendation engine (`backend/app/scoring.py`)
| He says… | Where |
|---|---|
| "Make price matter more" | `DEFAULT_WEIGHTS = {"price": 0.35, "distance": 0.25, "amenities": 0.30, "rating": 0.10}` (they are re-normalised to add to 1) |
| "Be stricter about budget" | `PRICE_TOLERANCE = 1.5` → lower it (1.2 = score hits 0 at 120% of budget) |
| "Be stricter about distance" | `DISTANCE_TOLERANCE = 2.0` |
| "Fully booked hostels should rank even lower" | `UNAVAILABLE_FACTOR = 0.5` → 0.2 |
| "Trust reviews faster" | `PRIOR_WEIGHT = 2` → lower it |
| "Change the over-budget-and-far penalty" | In `score_hostel`, the line `penalty = 1 - 0.5 * min(...)` → change `0.5` |

> After changing weights, run `python -m pytest -q` in `backend`. A couple of tests check rankings, so if one fails
> you can say exactly why: "I changed the weights, so this expected ranking changed."

---

## 4. The important code, explained

### 4.1 The fuzzy logic (`scoring.py`) — he will almost certainly ask about this
**Idea:** instead of "in budget: yes/no", every criterion gets a **degree between 0 and 1**.

```python
def falling(x, full_until, zero_at):
    if x <= full_until: return 1.0          # fully OK
    if x >= zero_at:    return 0.0          # not OK at all
    return (zero_at - x) / (zero_at - full_until)   # in between: a straight-line slope
```
- **Price:** full marks up to the student's budget, sloping down to 0 at 150% of the budget.
  Budget 10,000 and price 12,500 → `(15,000 − 12,500) / 5,000 = 0.5`.
- **Distance:** same idea, 0 at twice the student's maximum distance.
- **Amenities:** `matched wanted amenities ÷ wanted amenities`.
- **Rating:** a *Bayesian average*: `(avg × n + 3 × 2) / (n + 2)`, so one 5-star review doesn't give a perfect score.
  No reviews → neutral 3/5.

Then the weighted sum (price 35%, distance 25%, amenities 30%, rating 10%), then **one fuzzy rule**:

> IF price is too high AND distance is too far THEN reduce the score.
> `penalty = 1 − 0.5 × min(1 − price_fit, 1 − distance_fit)` — `min` is the standard fuzzy "AND".

**Worked example (all numbers verified by running the code).** Student: budget 10,000, max 2 km, wants WiFi + Security.
Hostel: KES 11,000, 1 km, has WiFi only, rated 4.0 by 5 students.

| Criterion | Degree | × weight | = |
|---|---|---|---|
| Price (11,000 vs 10,000) | 0.80 | 0.35 | 0.280 |
| Distance (1 km ≤ 2 km) | 1.00 | 0.25 | 0.250 |
| Amenities (1 of 2) | 0.50 | 0.30 | 0.150 |
| Rating (smoothed 0.743) | 0.74 | 0.10 | 0.074 |
| **Sum → 75% match** (no penalty: distance is fine) | | | **0.754** |

Over budget **and** far (KES 14,000, 3.5 km): price 0.2, distance 0.25 → the penalty multiplies the score by 0.625 → **32%**.
If a student cares only about price (weights price 0.7), the first hostel rises to **78%**.

### 4.2 Rooms: why `room_types` is its own table (`models.py`)
A hostel has *many* room types (single, twin, studio) each with its own price → a **one-to-many** relationship:
`RoomType.hostel_id` is a foreign key to `Hostel.id`. A unique constraint stops listing "Single room" twice.
Prices are per person, so twin and single prices are comparable.
In `recommend()` each room is scored and the hostel keeps its **best** room.

### 4.3 Security (`security.py`)
- **Passwords** are never stored. We store `PBKDF2-SHA256` with a random **salt** and 200,000 iterations, so the
  same password gives a different hash for each user and brute-forcing is slow.
- **Login** returns a **JWT**: a signed token containing the user id, role and expiry. The frontend keeps it in
  `localStorage` and sends it as `Authorization: Bearer …` on every request (`api.js`).
- **Role protection:** `require_role("owner")` is a FastAPI dependency. A student calling `POST /hostels` gets **403**,
  even if they bypass the frontend. The React `Guard` in `App.jsx` is only for a nicer experience.
- **Ownership:** `_owned_or_403()` in `routers/hostels.py` stops an owner editing someone else's hostel.
- **Photos:** `_sniff_image()` checks the file's first bytes (JPEG/PNG/WebP signatures), not just the file name.

### 4.4 Editing rooms (`_sync_rooms` in `routers/hostels.py`)
When an owner saves, we receive the full list of rooms. Rooms are matched **by name**: existing → update price/status,
new → add, missing → remove. That is why changing the twin price never touches the single room.

### 4.5 React concepts you may be asked about
- **Component:** a function that returns JSX (HTML-like), e.g. `Hero.jsx`.
- **`useState`:** a value that, when changed, re-draws the component (e.g. `rooms` in `HostelForm.jsx`).
- **`useEffect`:** code that runs after render, e.g. `Results.jsx` calls the API when the preferences change.
- **Context (`context.jsx`):** global state shared by all pages (user, compare list, preferences) so we don't pass props everywhere.
- **Router + Guard (`App.jsx`):** maps URLs to pages; `Guard role="owner"` redirects other roles.
- **Debounce in `Search.jsx`:** the name search waits 250 ms after the last keystroke before calling the API, so we don't send a request per letter.
- **Vite proxy (`vite.config.js`):** during development `/api` is forwarded to port 8000, which avoids CORS problems.

---

## 5. Questions he is likely to ask — and good answers

1. **Why FastAPI?** Fast to build, validates input automatically (Pydantic), and generates live API docs at `/docs`. It's the same stack we used for SmartKeja.
2. **Why PostgreSQL, not SQLite?** Real multi-user database that works on a server. In development it is one line in `.env`; the same code runs on both (I tested both).
3. **Why fuzzy logic instead of machine learning?** There is no training data for a new system (the cold-start problem), and fuzzy scoring is **explainable**: every result shows *why* it matched. ML would be a black box.
4. **How do you stop a student adding a hostel?** The backend checks the role in the JWT on every owner endpoint (403). The frontend hiding the button is only cosmetic.
5. **How are passwords stored?** Salted PBKDF2 hashes, never plain text.
6. **What is a JWT?** A signed token: the server can verify it wasn't tampered with without storing sessions. It expires after 12 hours.
7. **What happens when an owner changes a price?** `PUT /api/hostels/{id}` updates the room rows; students see it on their next request because there's no caching.
8. **Why one review per student?** A unique constraint on (hostel, student) in the database, so ratings can't be spammed; posting again updates the review.
9. **How do you handle fake or outdated listings?** Students can flag a listing; the owner sees the count on their dashboard. (Future: admin moderation.)
10. **What are the limitations?** Data is entered by owners (not independently verified); distance is typed in, not calculated from a map; no booking or payments; only USIU's surroundings.
11. **How did you test it?** 28 automated tests (scoring maths, security rules, room logic, API) on SQLite and PostgreSQL, plus a browser test of the full student and owner flow.
12. **How is this different from Hostel Finder / the Tanzanian portal?** Student controls the ranking, explains each match, supports room types, and has peer reviews for freshness, scoped to one campus.
13. **How would you scale it?** Move photos to cloud storage, add database indexes/caching, add pagination, deploy backend on Render and frontend on Vercel.
14. **What's the difference between 401 and 403?** 401 = not logged in / bad token. 403 = logged in but not allowed.

---

## 6. Practice tasks — do these BEFORE you present (15 minutes)

Do each one, see it change on screen, then undo it (Ctrl+Z).

1. **Colour:** in `styles.css` change `--blue: #2B3990` to `#B91C1C`. Everything turns red. Undo.
2. **Weights:** in `scoring.py` set price to `0.7` and the others small, e.g. `{"price": 0.7, "distance": 0.1, "amenities": 0.1, "rating": 0.1}`. Save, search again: the order of hostels changes. Undo.
3. **New amenity:** add `"Gym"` to both `AMENITIES` lists, edit a hostel as the owner, tick Gym, then see it on the student side.
4. **Slider:** in `Search.jsx` change `max="30000"` to `max="50000"`.
5. **Follow a request:** in `routers/hostels.py` inside `recommend()` add `print("recommend called", prefs)`. Search as a student and watch your uvicorn terminal print it. (Remove it afterwards.)
6. **See the data:** in DBeaver open `hostels` → Data tab, edit a price there, refresh the app, and the new price shows. Then explain: "the database is the single source of truth."
7. **API docs:** open http://localhost:8000/docs, click `POST /api/hostels/recommend` → *Try it out* → Execute. You can show the raw JSON with `score` and `reasons`.

## 7. Demo order (3–4 minutes)
1. Student logs in → search by name ("Roysambu") → open a hostel → show **Rooms & prices**.
2. Back to Search → choose **Twin sharing**, budget, amenities → **Find hostels** → open **Why this match?**
3. Tick two hostels → **Compare** → point at the highlighted best values.
4. Write a review. Log out.
5. Owner logs in → **Edit listing** → change the twin price and mark a room Full → log in as student again and show it changed.
6. Open DBeaver and show the same data in the tables.
