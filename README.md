# Name Profiler API

A REST API that accepts a name and returns a rich profile by aggregating data from three public APIs — gender prediction, age estimation, and nationality inference. Profiles are persisted in a PostgreSQL database and exposed through a set of CRUD endpoints.

---

## Live URL

> `https://your-deployed-url.com`

---

## Tech Stack

- **Python** + **FastAPI**
- **SQLAlchemy** (ORM)
- **PostgreSQL** (production) / SQLite (local fallback)
- **Pydantic** (request validation)
- **httpx** (async HTTP client)
- **uuid6** (UUID v7 generation)

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
git clone https://github.com/your-username/name-profiler.git
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

Create a `.env` file in the project root:

```env
SQLALCHEMY_DATABASE_URL=postgresql://username:password@localhost:5432/name_profiler
```

If no `.env` is provided, the app falls back to a local SQLite database (`sql_app.db`).

### 5. Start the server

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

---

## API Endpoints

### `POST /api/profiles`

Creates a new name profile by calling the three external APIs and storing the result.

If the name already exists in the database, the existing profile is returned without making new API calls.

**Request body:**
```json
{ "name": "ella" }
```

**Success — 201 Created:**
```json
{
  "status": "success",
  "data": {
    "id": "b3f9c1e2-7d4a-4c91-9c2a-1f0a8e5b6d12",
    "name": "ella",
    "gender": "female",
    "gender_probability": 0.99,
    "sample_size": 1234,
    "age": 46,
    "age_group": "adult",
    "country_id": "DK",
    "country_probability": 0.21,
    "created_at": "2026-04-16T10:00:00Z"
  }
}
```

**Already exists — 200 OK:**
```json
{
  "status": "success",
  "message": "Profile already exists",
  "data": { "...existing profile..." }
}
```

---

### `GET /api/profiles`

Returns all profiles. Supports optional query parameters for filtering.

**Query parameters (all optional, case-insensitive):**

| Parameter | Example |
|-----------|---------|
| `gender` | `?gender=male` |
| `country_id` | `?country_id=NG` |
| `age_group` | `?age_group=adult` |

Filters are combined with AND logic — e.g. `?gender=male&country_id=NG` returns only male profiles from Nigeria.

**Success — 200 OK:**
```json
{
  "status": "success",
  "count": 2,
  "data": [
    {
      "id": "id-1",
      "name": "emmanuel",
      "gender": "male",
      "age": 25,
      "age_group": "adult",
      "country_id": "NG"
    },
    {
      "id": "id-2",
      "name": "sarah",
      "gender": "female",
      "age": 28,
      "age_group": "adult",
      "country_id": "US"
    }
  ]
}
```

---

### `GET /api/profiles/{id}`

Returns a single profile by its UUID.

**Success — 200 OK:**
```json
{
  "status": "success",
  "data": {
    "id": "b3f9c1e2-7d4a-4c91-9c2a-1f0a8e5b6d12",
    "name": "emmanuel",
    "gender": "male",
    "gender_probability": 0.99,
    "sample_size": 1234,
    "age": 25,
    "age_group": "adult",
    "country_id": "NG",
    "country_probability": 0.85,
    "created_at": "2026-04-16T10:00:00Z"
  }
}
```

**Not found — 404:**
```json
{ "status": "error", "message": "Profile not found" }
```

---

### `DELETE /api/profiles/{id}`

Deletes a profile by its UUID.

**Success — 204 No Content**

**Not found — 404:**
```json
{ "status": "error", "message": "Profile with id {id} not found" }
```

---

## Error Responses

All errors follow this structure:

```json
{ "status": "error", "message": "<error message>" }
```

| Status Code | Cause |
|-------------|-------|
| `400` | Missing or empty name |
| `404` | Profile not found |
| `422` | Invalid request type |
| `502` | External API returned unusable data (null gender, null age, or no country data) |

---

## Age Group Classification

| Age Range | Group |
|-----------|-------|
| 0 – 12 | `child` |
| 13 – 19 | `teenager` |
| 20 – 59 | `adult` |
| 60+ | `senior` |
