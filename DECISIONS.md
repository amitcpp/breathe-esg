# Decisions Log

## 1. SQLite for prototype, PostgreSQL for production

**Decision**: Use SQLite in development, PostgreSQL in production (via `dj-database-url`).

**Why**: SQLite eliminates the "install Postgres before you can run the app" friction. The `dj-database-url` pattern lets us switch with one env var. No ORM-level changes needed because we avoided raw SQL and SQLite-incompatible features (e.g., no `ArrayField`). JSON fields work on SQLite 3.38+ (Python 3.10+ bundles this).

**Risk**: JSON field queries behave slightly differently across backends. Mitigated by keeping JSON queries simple (presence checks, not deep path queries).

---

## 2. Shared-database multi-tenancy (not schema-per-tenant)

**Decision**: One database, `tenant_id` FK on every model.

**Why**: Schema-per-tenant is cleaner but adds migration complexity and connection management overhead. For a prototype with < 10 tenants, the simpler approach wins. Every queryset is filtered by `request.user.tenant` — this is the discipline cost.

**Risk**: A missing `.filter(tenant=...)` leaks data across tenants. In production, we'd add a middleware or queryset mixin to enforce this. For the prototype, views handle it manually.

---

## 3. Storing raw data as JSON, not re-serialized CSV

**Decision**: `RawRecord.raw_data` stores the parsed CSV row as a JSON dict, not the original CSV line.

**Why**: Re-serializing back to CSV introduces quoting ambiguity. A JSON dict preserves column names, handles null/empty distinctions cleanly, and makes the detail panel trivial to render. The original file is still identifiable via `DataIngestion.file_hash`.

**Tradeoff**: We lose the ability to reconstruct the exact byte sequence of the original file. Acceptable because we preserve all *semantic* content, which is what auditors actually review.

---

## 4. German number parsing as a first-class concern

**Decision**: Built a custom parser (`parse_german_decimal`) instead of relying on locale settings.

**Why**: SAP exports from German-locale instances use dots for thousands and commas for decimals (`1.234,56`). Python's `locale` module is global state and not thread-safe. An explicit parser is deterministic, testable, and handles mixed-format files (some columns German, some US).

---

## 5. Haversine + 9% uplift for flight distances

**Decision**: Calculate great-circle distance with Haversine formula, then apply DEFRA's 9% uplift factor.

**Why**: Travel platforms rarely export distance directly. They export origin/destination IATA codes. DEFRA explicitly recommends the 9% uplift to account for non-direct routing, holding patterns, and ATC-mandated diversions. We store the airport coordinates and do the math ourselves.

**Alternative considered**: Precomputed distance tables. Rejected because they're static and don't handle the long tail of airport pairs.

---

## 6. JWT authentication (not session-based)

**Decision**: SimpleJWT for authentication.

**Why**: The frontend is a React SPA communicating via REST API. JWT is the standard pattern — no CSRF tokens needed for API calls, works cleanly with `Authorization: Bearer` headers, and token refresh keeps sessions alive without server-side session storage.

---

## 7. Emission factors as a database table, not config

**Decision**: `EmissionFactor` is a full Django model, not a YAML/JSON config file.

**Why**: Factors change annually (DEFRA updates every June). Storing them in the database means we can version them (`valid_from`, `valid_to`), let admins update them through the admin panel, and maintain factor-level audit trails. A config file would require redeployment for factor updates.

---

## 8. Flags as a JSON array, not a separate table

**Decision**: `EmissionRecord.flags` is a JSON array on the record, not a separate `Flag` model with a FK.

**Why**: Flags are write-once (set during parsing) and read-many (displayed in the detail panel). A separate table would add N+1 queries or require prefetching for every list view. JSON keeps flags co-located with the record they describe. We never need to query "all records with flag type X" — we query by `review_status=flagged` instead.

---

## 9. No Celery — synchronous parsing

**Decision**: Parse files synchronously in the upload request.

**Why**: For the prototype's file sizes (< 10MB, < 10K rows), parsing completes in under 5 seconds. Adding Celery would mean adding Redis, a worker process, task state management, and WebSocket/polling for completion notification. That's a lot of infrastructure for a demo. The architecture supports async later — just move `parser.process_file()` into a Celery task and return the ingestion ID immediately.

---

## 10. React without a state management library

**Decision**: React with `useState`/`useEffect` and a thin `api.js` service layer.

**Why**: The app has three pages with independent data needs. There's no complex cross-page state synchronization. Redux/Zustand would add boilerplate without solving a real problem at this scale. Each page fetches its own data on mount.
