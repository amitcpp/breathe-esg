# Tradeoffs

Honest accounting of what we chose, what we traded away, and why.

## 1. Synchronous parsing vs. Background jobs

**Chose**: Synchronous parsing in the request cycle.

**Traded away**: Ability to handle files > ~50K rows without request timeouts. No progress indicators during parsing.

**Why it's acceptable**: Prototype-scale files are < 10K rows. Parsing completes in < 5s. The path to async is clean: wrap `parser.process_file()` in a Celery task, return ingestion ID immediately, poll `/api/ingestion/history/{id}/` for status.

---

## 2. SQLite vs. PostgreSQL in development

**Chose**: SQLite for zero-config local development.

**Traded away**: `JSONField` query performance, `EXPLAIN ANALYZE` parity with production, concurrent write safety.

**Why it's acceptable**: We never do complex JSON path queries. All JSON fields are read-whole-object. SQLite handles our query patterns identically to PostgreSQL. Production uses PostgreSQL via `DATABASE_URL`.

---

## 3. No tenant middleware — manual queryset filtering

**Chose**: Each view manually filters by `request.user.tenant`.

**Traded away**: Guaranteed tenant isolation. A developer who forgets `.filter(tenant=...)` exposes cross-tenant data.

**Why it's acceptable**: The app has < 10 views. In production, we'd add a `TenantMiddleware` that injects `request.tenant` and a `TenantQuerySetMixin` that auto-filters. For the prototype, explicit filtering is readable and debuggable.

---

## 4. Emission factor matching by activity_type string

**Chose**: Simple string match: `EmissionFactor.objects.filter(activity_type='diesel').first()`.

**Traded away**: Sophisticated factor matching (region → country → global fallback chains, temporal validity checks, fuel grade specificity).

**Why it's acceptable**: For the prototype, we seed a flat set of factors that cover our sample data exactly. The model schema already supports `valid_from`/`valid_to` and `region` — we just don't implement the multi-level fallback logic yet.

---

## 5. No file storage — only parsed content persisted

**Chose**: Read the uploaded file, parse it, store rows as JSON in `RawRecord`. Don't persist the original file to disk/S3.

**Traded away**: Ability to re-download the exact original file. Ability to re-process files with updated parsing logic.

**Why it's acceptable**: The `file_hash` field enables duplicate detection. The `raw_data` JSON preserves all semantic content. In production, we'd add S3 storage for the original file and link it from `DataIngestion`.

---

## 6. No real-time updates — fetch on navigation

**Chose**: Each page fetches data on mount. No WebSockets, no SSE, no polling.

**Traded away**: Live updates when another analyst approves a record.

**Why it's acceptable**: ESG review is not real-time. Analysts review data in batches, not collaboratively on the same screen. A page refresh (or re-navigation) shows the latest state.

---

## 7. Flat RBAC — not permission-based

**Chose**: Three roles (admin, analyst, viewer) with implicit permissions.

**Traded away**: Fine-grained permissions (e.g., "can approve Scope 1 but not Scope 3"). No Django permission framework integration.

**Why it's acceptable**: The prototype has one user per tenant. The role field is there for future permission checks. Adding `@role_required('analyst')` decorators is trivial.

---

## 8. Client-side token storage in localStorage

**Chose**: Store JWT tokens in `localStorage`.

**Traded away**: XSS protection (localStorage is readable by any JS on the page). HttpOnly cookies would be safer.

**Why it's acceptable**: This is an internal tool behind authentication, not a public-facing app. In production, we'd switch to HttpOnly cookie-based JWT with CSRF protection.
