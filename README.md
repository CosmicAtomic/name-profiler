# Name Profiler API

A REST API that accepts a name and returns a rich demographic profile by aggregating data from three public APIs — gender prediction, age estimation, and nationality inference. Profiles are persisted in a PostgreSQL database and exposed through a set of authenticated endpoints that support filtering, sorting, pagination, natural language search, and CSV export.

---

## Live URL

> `https://name-profiler-production.up.railway.app/`

---

## Tech Stack

- **Python** + **FastAPI**
- **SQLAlchemy** (ORM)
- **PostgreSQL** (production) / SQLite (local fallback)
- **Pydantic** (request validation)
- **httpx** (async HTTP client)
- **PyJWT** (token encoding and verification)
- **uuid6** (UUID v7 generation)
- **pycountry** (country name and code lookup)

---

## System Architecture

The application is split into focused modules, each with a single responsibility:

```
main.py              — App entry point: registers routers, middleware, and exception handlers
database.py          — SQLAlchemy engine, session factory, and get_db dependency
models.py            — ORM table definitions (Profile, User, Refresh_Token)
schemas.py           — Pydantic request/response models
services.py          — External API calls (Genderize, Agify, Nationalize) and helper functions
utils.py             — Response formatters and pagination link builder
query_parser.py      — Rule-based natural language query parser
auth.py              — JWT utilities, get_current_user dependency, require_role guard
profile_routes.py    — All /api/profiles endpoints
auth_routes.py       — All /auth endpoints (OAuth, token refresh, logout, /me)
seed.py              — Database seeding script
```

**Request lifecycle (protected route):**

```
Client Request
    → X-API-Version header check (check_api_version)
    → Authorization header parsed (get_current_user)
    → JWT verified, user fetched from DB
    → Role checked if required (require_role)
    → Route handler executes
    → JSONResponse returned
```

**Data flow for profile creation:**

```
POST /api/profiles
    → Genderize.io  → gender + probability
    → Agify.io      → age
    → Nationalize.io → country list → highest probability country selected
    → age classified into group (child / teenager / adult / senior)
    → country code resolved to full name via pycountry
    → Profile saved to DB with UUID v7
```

---

## External APIs Used

| API | Purpose | Endpoint |
|-----|---------|----------|
| [Genderize.io](https://genderize.io) | Predicts gender from name | `https://api.genderize.io?name={name}` |
| [Agify.io](https://agify.io) | Predicts age from name | `https://api.agify.io?name={name}` |
| [Nationalize.io](https://nationalize.io) | Predicts nationality from name | `https://api.nationalize.io?name={name}` |

---

## Running Locally

### 1. Clone the repository

```bash
git clone https://github.com/CosmicAtomic/name-profiler.git
cd name-profiler
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # Mac/Linux
.venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Copy `.env.example` to `.env` and fill in your values:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/name_profiler
GITHUB_CLIENT_ID=your_github_oauth_app_client_id
GITHUB_CLIENT_SECRET=your_github_oauth_app_client_secret
JWT_SECRET_KEY=some_long_random_string
```

If `DATABASE_URL` is not set, the app falls back to a local SQLite database (`sql_app.db`).

### 5. Start the server

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

---

## CLI Usage

All protected endpoints require two headers on every request:

```
X-API-Version: 1
Authorization: Bearer <access_token>
```

**Authenticate and get tokens:**
```bash
# Visit in browser — redirects to GitHub
GET /auth/github
```

**Use the access token:**
```bash
curl -H "X-API-Version: 1" \
     -H "Authorization: Bearer <access_token>" \
     https://name-profiler-production.up.railway.app/api/profiles
```

**Refresh an expired access token:**
```bash
curl -X POST https://name-profiler-production.up.railway.app/auth/refresh \
     -H "Content-Type: application/json" \
     -d '{"refresh_token": "<refresh_token>"}'
```

**Logout:**
```bash
curl -X POST https://name-profiler-production.up.railway.app/auth/logout \
     -H "Content-Type: application/json" \
     -d '{"refresh_token": "<refresh_token>"}'
```

**Get current user info:**
```bash
curl -H "X-API-Version: 1" \
     -H "Authorization: Bearer <access_token>" \
     https://name-profiler-production.up.railway.app/auth/me
```

**Export profiles as CSV:**
```bash
curl -H "X-API-Version: 1" \
     -H "Authorization: Bearer <access_token>" \
     "https://name-profiler-production.up.railway.app/api/profiles/export?gender=female&age_group=adult" \
     -o profiles.csv
```

---

## Seeding the Database

```bash
DATABASE_URL=your_database_url python seed.py
```

The script loads 2026 profiles from `seed_profiles.json`. It checks existing names before inserting, so it is safe to run multiple times.

---

## Authentication Flow

Authentication is handled via GitHub OAuth. No passwords are stored.

```
1. Client visits GET /auth/github
      → Server generates a random state token and PKCE code verifier
      → Both are stored in memory keyed by state
      → Client is redirected to GitHub's authorization page

2. GitHub redirects back to GET /auth/github/callback?code=...&state=...
      → Server validates the state matches a known pending request
      → Server exchanges the code + code_verifier for a GitHub access token
      → Server calls GET https://api.github.com/user to fetch profile data

3. User lookup / creation
      → If github_id exists in users table: update last_login_at
      → If not: create new user with role = "analyst"

4. Token issuance
      → Access token generated (JWT, 3 min expiry)
      → Refresh token generated (JWT, 5 min expiry), stored in refresh_tokens table
      → Both returned to client (JSON or redirect with tokens in query params)
```

**Redirect flow** (for frontend clients):

```
GET /auth/github?redirect_to=http://yourfrontend.com/callback
```

After login, the server redirects to:
```
http://yourfrontend.com/callback?access_token=...&refresh_token=...&username=...
```

---

## Related Repositories

- **CLI Tool:** [insighta-cli](https://github.com/CosmicAtomic/insighta-cli) — Terminal interface for all API operations
- **Web Portal:** [insighta-web](https://github.com/CosmicAtomic/insighta-web) — Browser-based dashboard at https://insighta-lab.netlify.app/

Both clients authenticate through this backend via GitHub OAuth and consume the same API endpoints.

---

## Token Handling Approach

The API uses two JWTs per session — a short-lived access token and a longer-lived refresh token.

**Access token:**
- Signed with `HS256` using `JWT_SECRET_KEY`
- Payload: `{ user_id, role, exp, iat }`
- Expires in **3 minutes**
- Sent in the `Authorization: Bearer <token>` header on every request
- Never stored in the database

**Refresh token:**
- Signed with `HS256` using the same key
- Payload: `{ user_id, exp, iat }`
- Expires in **5 minutes**
- Stored in the `refresh_tokens` table with an `is_used` flag
- One-time use — marked `is_used = True` immediately on use

**Token refresh flow:**
1. Client sends `POST /auth/refresh` with the refresh token in the request body
2. Server verifies the JWT signature and expiry
3. Server checks the token exists in the DB and `is_used = False`
4. Old token is marked used, new access + refresh tokens are issued and stored
5. Client replaces both tokens

**Logout:**
- Client sends `POST /auth/logout` with the refresh token
- Server marks it `is_used = True`
- The access token is stateless so it remains valid until it naturally expires (max 3 minutes)

---

## Role Enforcement Logic

Every user is assigned one of two roles at account creation:

| Role | Assigned | Permissions |
|------|----------|-------------|
| `analyst` | Default for all new GitHub logins | Read-only access — can list, search, filter, export, and view profiles |
| `admin` | Manually assigned in the database | Full access — all analyst permissions plus create and delete profiles |

**How it works in code:**

All `/api/profiles` routes require the `X-API-Version: 1` header and a valid JWT (`check_api_version` runs as a router-level dependency before any route handler).

Individual routes then layer their own auth:

```
GET  /api/profiles          → get_current_user  (analyst or admin)
GET  /api/profiles/export   → get_current_user  (analyst or admin)
GET  /api/profiles/search   → get_current_user  (analyst or admin)
GET  /api/profiles/{id}     → get_current_user  (analyst or admin)
POST /api/profiles          → require_role("admin")
DELETE /api/profiles/{id}   → require_role("admin")
```

`get_current_user` extracts the Bearer token, verifies it, fetches the user from the database, and confirms `is_active = True`. `require_role` wraps `get_current_user` and additionally checks that `user.role` matches the required role — returning 403 if it does not.

---

## API Endpoints

### Auth

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/auth/github` | None | Initiates GitHub OAuth login |
| `GET` | `/auth/github/callback` | None | GitHub OAuth callback |
| `POST` | `/auth/refresh` | None | Exchange refresh token for new tokens |
| `POST` | `/auth/logout` | None | Invalidate a refresh token |
| `GET` | `/auth/me` | Bearer token | Get current user info |

### Profiles

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/profiles` | Admin | Create a new profile |
| `GET` | `/api/profiles` | Any user | List profiles with filtering, sorting, pagination |
| `GET` | `/api/profiles/export` | Any user | Export filtered profiles as CSV |
| `GET` | `/api/profiles/search` | Any user | Natural language search |
| `GET` | `/api/profiles/{id}` | Any user | Get a single profile by ID |
| `DELETE` | `/api/profiles/{id}` | Admin | Delete a profile |

All profile endpoints require the `X-API-Version: 1` header.

---

### `GET /api/profiles` — Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `gender` | string | `male` or `female` |
| `country_id` | string | ISO 3166-1 alpha-2 code (e.g. `NG`) |
| `age_group` | string | `child`, `teenager`, `adult`, or `senior` |
| `min_age` | integer | Minimum age (inclusive) |
| `max_age` | integer | Maximum age (inclusive) |
| `min_gender_probability` | float | Minimum gender confidence score |
| `min_country_probability` | float | Minimum country confidence score |
| `sort_by` | string | `age`, `created_at`, or `gender_probability` |
| `order` | string | `asc` or `desc` (default: `asc`) |
| `page` | integer | Page number (default: 1) |
| `limit` | integer | Results per page (default: 10, max: 50) |

**Response envelope:**
```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 120,
  "total_pages": 12,
  "links": {
    "self": "/api/profiles?page=1&limit=10",
    "next": "/api/profiles?page=2&limit=10",
    "prev": null
  },
  "data": [ "...profiles..." ]
}
```

---

## Age Group Classification

| Age Range | Group |
|-----------|-------|
| 0 – 12 | `child` |
| 13 – 19 | `teenager` |
| 20 – 59 | `adult` |
| 60+ | `senior` |

---

## Natural Language Search — Parsing Approach

The `/api/profiles/search` endpoint uses a **rule-based keyword scanner** — no AI or LLM involved. The query is inspected for known keywords and patterns, which map to structured database filters.

### Order of Operations

1. Lowercase the entire query
2. Split into words for word-level matching
3. Detect gender keywords
4. Detect age group keywords
5. Handle `young` (maps to age range, not age group)
6. Detect age comparison phrases against the full query string
7. Detect country via the word `from`
8. Return filters dict — if empty, return `None` → 400 error

### Supported Keywords

**Gender:**

| Keyword | Maps to |
|---------|---------|
| `male`, `males`, `men`, `man` | `gender = "male"` |
| `female`, `females`, `women`, `woman` | `gender = "female"` |

If both genders appear in the same query, the gender filter is skipped. The female check runs before male because "female" contains "male".

**Age groups:**

| Keyword | Maps to |
|---------|---------|
| `child`, `children` | `age_group = "child"` |
| `teen`, `teens`, `teenager`, `teenagers` | `age_group = "teenager"` |
| `adult`, `adults` | `age_group = "adult"` |
| `senior`, `seniors`, `elderly`, `old` | `age_group = "senior"` |

**"young":** Maps to `min_age = 16, max_age = 24`. Only applied if no other age group keyword matched — "young adults" resolves to `adult`.

**Age comparisons:**

| Pattern | Maps to |
|---------|---------|
| `older than N`, `above N`, `over N` | `min_age = N` |
| `younger than N`, `below N`, `under N` | `max_age = N` |

**Country:** Looks for `from` in the query and resolves the next word using pycountry fuzzy search to a 2-letter country code.

### Limitations

- **No typo correction** for gender/age keywords — "femal" or "adut" won't match
- **No negation** — "not from Nigeria" won't work
- **Multi-word country names fail** — "from United States" only reads "United", not "United States"
- **No number ranges** — "between 20 and 30" is not supported; use `min_age` + `max_age` query params instead
- **One country at a time** — "from Nigeria or Ghana" ignores Ghana
- **Conflicting filters** — "children older than 50" applies both `age_group = child` and `min_age = 50` simultaneously, which produces no results
- **Unrecognized queries return 400** — if no keyword is matched at all, the endpoint returns an error rather than returning all profiles

---

## Error Responses

```json
{ "status": "error", "message": "<description>" }
```

| Status Code | Cause |
|-------------|-------|
| `400` | Missing/empty name, uninterpretable search query, missing API version header |
| `401` | Missing, expired, or invalid token |
| `403` | Authenticated but insufficient role, or inactive account |
| `404` | Profile not found |
| `422` | Invalid query parameter type or value |
| `502` | External API (Genderize/Agify/Nationalize) returned unusable data |
