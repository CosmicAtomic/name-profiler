# Name Profiler API

A REST API that accepts a name and returns a rich demographic profile by aggregating data from three public APIs — gender prediction, age estimation, and nationality inference. Profiles are persisted in a PostgreSQL database and exposed through a set of endpoints that support filtering, sorting, pagination, and natural language search.

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
- **uuid6** (UUID v7 generation)
- **pycountry** (country name and code lookup)

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

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/name_profiler
```

If no `.env` is provided, the app falls back to a local SQLite database (`sql_app.db`).

### 5. Start the server

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

---

## Seeding the Database

A seed script is included to pre-populate the database with 2026 demographic profiles. It skips any names that already exist, so it is safe to run multiple times.

```bash
python seed.py
```

The seed data is loaded from `seed_profiles.json`. Make sure your `DATABASE_URL` environment variable points to the correct database before running.

---

## Age Group Classification

Ages are bucketed into four groups at profile creation time using the following ranges:

| Age Range | Group |
|-----------|-------|
| 0 – 12 | `child` |
| 13 – 19 | `teenager` |
| 20 – 59 | `adult` |
| 60+ | `senior` |

---

## API Endpoints

### `POST /api/profiles`

Creates a new name profile by calling the three external APIs and storing the result. If the name already exists in the database, the existing profile is returned immediately without making any API calls.

**Request body:**
```json
{ "name": "ella" }
```

**Success — 201 Created:**
```json
{
  "status": "success",
  "data": {
    "id": "019600a2-d3b7-7a4e-9c1f-2f8d3e6b1a05",
    "name": "ella",
    "gender": "female",
    "gender_probability": 0.98,
    "age": 34,
    "age_group": "adult",
    "country_id": "DK",
    "country_name": "Denmark",
    "country_probability": 0.21,
    "created_at": "2026-04-22T10:00:00Z"
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

Returns a paginated list of profiles. Supports filtering, sorting, and pagination via query parameters. All filters are combined with AND logic.

**Query parameters (all optional):**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `gender` | string | Filter by gender | `?gender=male` |
| `country_id` | string | Filter by 2-letter country code | `?country_id=NG` |
| `age_group` | string | Filter by age group | `?age_group=adult` |
| `min_age` | integer | Minimum age (inclusive) | `?min_age=20` |
| `max_age` | integer | Maximum age (inclusive) | `?max_age=40` |
| `min_gender_probability` | float | Minimum gender confidence | `?min_gender_probability=0.9` |
| `min_country_probability` | float | Minimum country confidence | `?min_country_probability=0.5` |
| `sort_by` | string | Sort field: `age`, `created_at`, `gender_probability` | `?sort_by=age` |
| `order` | string | Sort direction: `asc` or `desc` | `?order=desc` |
| `page` | integer | Page number (default: 1) | `?page=2` |
| `limit` | integer | Results per page (default: 10, max: 50) | `?limit=20` |

**Success — 200 OK:**
```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 42,
  "data": [
    {
      "id": "019600a2-d3b7-7a4e-9c1f-2f8d3e6b1a05",
      "name": "emmanuel",
      "gender": "male",
      "gender_probability": 0.99,
      "age": 25,
      "age_group": "adult",
      "country_id": "NG",
      "country_name": "Nigeria",
      "country_probability": 0.85,
      "created_at": "2026-04-22T10:00:00Z"
    }
  ]
}
```

---

### `GET /api/profiles/search`

Searches profiles using a natural language query string. The query is parsed into structured filters which are then applied to the database.

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Natural language search query |
| `page` | integer | Page number (default: 1) |
| `limit` | integer | Results per page (default: 10, max: 50) |

**Example requests:**
```
GET /api/profiles/search?q=adult males from Nigeria
GET /api/profiles/search?q=women older than 30
GET /api/profiles/search?q=young females
GET /api/profiles/search?q=senior men from Japan
```

**Success — 200 OK:**
```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 7,
  "data": [ "...matching profiles..." ]
}
```

**Uninterpretable query — 400 Bad Request:**
```json
{ "status": "error", "message": "Unable to interpret query" }
```

---

### `GET /api/profiles/{id}`

Returns a single profile by its UUID.

**Success — 200 OK:**
```json
{
  "status": "success",
  "data": {
    "id": "019600a2-d3b7-7a4e-9c1f-2f8d3e6b1a05",
    "name": "sarah",
    "gender": "female",
    "gender_probability": 0.97,
    "age": 28,
    "age_group": "adult",
    "country_id": "US",
    "country_name": "United States",
    "country_probability": 0.62,
    "created_at": "2026-04-22T10:00:00Z"
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
{ "status": "error", "message": "Profile not found" }
```

---

## Error Responses

All errors follow this structure:

```json
{ "status": "error", "message": "<description>" }
```

| Status Code | Cause |
|-------------|-------|
| `400` | Missing or empty name / empty search query / uninterpretable search query |
| `404` | Profile not found |
| `422` | Invalid query parameter type (e.g. passing a string for `min_age`) or invalid value for `sort_by`/`order` |
| `502` | External API returned unusable data (null gender, null age, or empty country list) |

---

## Natural Language Search — Parsing Approach

The `/api/profiles/search` endpoint uses a **rule-based keyword scanner** — no AI or LLM is involved. The query string is inspected for known keywords and patterns, which are then mapped to database filter conditions.

### Order of Operations

1. **Normalize** — the entire query is lowercased so `Female`, `FEMALE`, and `female` are all treated identically
2. **Split into words** — the query is split on whitespace to enable word-level matching
3. **Detect gender keywords** — scan words against known gender keyword sets
4. **Detect age group keywords** — scan words against age group keyword sets
5. **Handle "young"** — if no age group was found and "young" is present, apply an age range filter instead
6. **Detect age comparison phrases** — scan the full query string (not word-by-word) for phrases like "older than 30"
7. **Detect country** — look for the word "from" and attempt to resolve the following word as a country name
8. **Return filters** — the collected filters dict is returned; if empty (nothing was recognized), `None` is returned and the endpoint responds with 400

### Supported Keywords

**Gender:**

| Keyword | Maps to |
|---------|---------|
| `male`, `males`, `men`, `man` | `gender = "male"` |
| `female`, `females`, `women`, `woman` | `gender = "female"` |

If both male and female keywords appear in the same query (e.g. "men and women"), the gender filter is skipped entirely rather than picking one arbitrarily.

The female check is performed before the male check because the word "female" contains the substring "male" — checking male first would incorrectly match "females".

**Age groups:**

| Keyword | Maps to |
|---------|---------|
| `child`, `children` | `age_group = "child"` |
| `teen`, `teens`, `teenager`, `teenagers` | `age_group = "teenager"` |
| `adult`, `adults` | `age_group = "adult"` |
| `senior`, `seniors`, `elderly`, `old` | `age_group = "senior"` |

Only the first matched age group is applied — additional age group keywords in the same query are ignored.

**"young" keyword:**

`young` is not a named age group in the database. Instead, it maps to an age range filter of `min_age = 16, max_age = 24`. This only applies if no other age group keyword was detected — so "young adults" will use `age_group = "adult"` (adult wins), while "young females" will use the `16–24` age range.

**Age comparisons:**

| Phrase | Example | Maps to |
|--------|---------|---------|
| `older than` | `older than 30` | `min_age = 30` |
| `above` | `above 25` | `min_age = 25` |
| `over` | `over 18` | `min_age = 18` |
| `younger than` | `younger than 20` | `max_age = 20` |
| `below` | `below 15` | `max_age = 15` |
| `under` | `under 30` | `max_age = 30` |

Multi-word phrases (`older than`, `younger than`) are checked before single-word ones (`above`, `over`, `below`, `under`) to avoid partial matches. Numbers are extracted using a regex that captures the digit(s) immediately following the phrase.

**Country:**

The parser looks for the word `from` in the query and treats the word immediately after it as a country name. It uses `pycountry`'s fuzzy search to resolve common spelling variants (e.g. `Nigeria`, `Nigerian`-adjacent spellings). If a match is found, the country's ISO 3166-1 alpha-2 code (e.g. `NG`) is used as the filter.

---

## Natural Language Search — Limitations

The rule-based parser is intentionally simple. It covers common query patterns well, but has several known gaps:

**Typo handling:** The fuzzy search in `pycountry` handles some near-misses (e.g. "Nigerria"), but significant misspellings will fail silently — no country filter will be applied rather than returning an error. For all other keywords (gender, age group), there is no typo tolerance at all. "femle" or "adut" will not be recognized.

**Negation:** The parser has no concept of NOT. Queries like "not from Nigeria", "non-adults", or "males except seniors" will not work as expected. The negation word is ignored and the remaining keywords may still match unintentionally.

**Complex sentences:** The parser does not understand sentence structure or grammar. It only looks for known keywords, so elaborate phrasings like "give me all the female profiles that are quite young" may partially work (female + young recognized) but longer or more nuanced phrasing will produce incorrect or empty filters.

**"from" followed by multi-word country names:** The parser only grabs the single word immediately after "from". This means "from United States" will attempt to match "United" as a country (which may fail or match unintended results). Use single-word country names where possible, e.g. "from Nigeria", "from Japan", "from Denmark".

**Number ranges:** Queries like "between 20 and 30" or "ages 25 to 40" are not supported. Only single-sided comparisons work (`older than 30`, `under 25`). For range queries, use the `GET /api/profiles` endpoint with `min_age` and `max_age` parameters directly.

**Multiple countries:** Only one country can be filtered at a time. "from Nigeria or Ghana" will attempt to resolve "nigeria" as the country and ignore the rest.

**Combining age group and age comparison:** If both an age group keyword and an age comparison phrase appear (e.g. "adults older than 35"), both filters are applied independently. This can produce contradictory results if the ranges don't overlap (e.g. "children older than 50" would apply `age_group = child` AND `min_age = 50` simultaneously).

**Unknown keywords:** Any word not in the supported keyword sets is silently ignored. If a query contains no recognizable keywords at all, the endpoint returns a 400 error with `"Unable to interpret query"`.
