# EEL — Opportunity Portal: Implementation Plan

## 1. Where things actually stand (checked against the GitHub repo)

| File | Status |
|---|---|
| `backend/app/models.py` | ✅ pushed, matches the opportunity-portal schema |
| `backend/app/extensions.py` | ✅ pushed |
| `backend/config.py` | ✅ pushed |
| `backend/manage.py`, `wsgi.py`, `requirements.txt`, `seed.py` | ✅ pushed |
| `backend/app/__init__.py` | ❌ still the empty scaffold placeholder |
| `backend/app/cli.py` | ❌ not in the repo yet |
| `backend/.env.example` | ❌ not in the repo yet |
| `backend/app/blueprints/auth/*` | empty placeholders (as expected — not built yet) |
| `backend/app/blueprints/content/`, `backend/app/blueprints/progress/` | still exist from the pre-pivot scaffold — leftover, need renaming/removing |
| `backend/app/blueprints/opportunities/` | doesn't exist yet |
| `backend/app/blueprints/admin/*` | empty placeholder |

**Immediate blocker:** `app/__init__.py`'s factory imports `app.blueprints.opportunities.routes` and `app.cli` — neither exists yet, so the app won't start until the rename below happens and `cli.py` is added. This has to happen before any route code is written.

## 2. User access levels

Four tiers, from least to most privileged. Every endpoint's behavior should be defined in terms of these, not ad hoc per-route checks:

| Tier | Can do |
|---|---|
| **Anonymous** | View the public marketing site only. No opportunity data. |
| **Free user** (registered) | Browse approved opportunities *after* the early-access window; submit new opportunities (goes to pending); save/unsave opportunities; manage own profile |
| **Premium user** | Everything Free can do, plus: see approved opportunities immediately (no early-access wait) |
| **Admin** | Everything, plus: approve/reject pending opportunities; manage categories; manage users (view, grant/revoke premium, promote to admin) |

This maps directly onto `models.py` already: `User.role` (USER/ADMIN) and `User.is_premium_active()` are the two checks every protected endpoint needs — nothing else to invent.

**Implementation mechanism:** a `permissions.py` module (new — see structure below) with decorators `@login_required`, `@admin_required`, and a `visible_opportunities_for(user)` query helper (already stubbed as `Opportunity.visible_query_for()` in models.py) — so the access rule is enforced once, not re-implemented per route.

## 3. Restructured file layout

```
backend/
├── app/
│   ├── __init__.py            # factory (needs pushing)
│   ├── extensions.py          # ✅ done
│   ├── models.py              # ✅ done
│   ├── cli.py                 # needs pushing
│   ├── permissions.py         # NEW — role/premium decorators, shared across blueprints
│   ├── pagination.py          # NEW — one helper: paginate(query, schema) -> dict, used by every list endpoint
│   │
│   ├── blueprints/
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py          # /register /login /refresh /me
│   │   │   └── schemas.py         # marshmallow: RegisterSchema, LoginSchema
│   │   │
│   │   ├── opportunities/         # RENAME from content/ — public-facing CRUD + browsing
│   │   │   ├── __init__.py
│   │   │   ├── routes.py          # GET list (role-aware), GET one, POST submit, PATCH own-pending, DELETE own-pending
│   │   │   ├── schemas.py         # OpportunitySchema, OpportunityCreateSchema
│   │   │   └── services.py        # NEW — business logic (visibility rules, submission validation) kept out of routes.py
│   │   │
│   │   ├── saved/                 # NEW — split out of the old progress/ folder
│   │   │   ├── __init__.py
│   │   │   └── routes.py          # POST/DELETE save, GET my-saved
│   │   │
│   │   └── admin/
│   │       ├── __init__.py
│   │       ├── routes.py          # moderation queue, approve/reject, category CRUD, user mgmt
│   │       └── schemas.py
│   │
├── migrations/                # Flask-Migrate (run `flask db init` once __init__.py is live)
├── tests/
│   ├── conftest.py             # NEW — app fixture using TestingConfig + sqlite
│   ├── test_auth.py
│   ├── test_opportunities.py
│   └── test_admin.py
├── config.py                   # ✅ done
├── manage.py                   # ✅ done
├── wsgi.py                     # ✅ done
├── seed.py                     # ✅ done
├── requirements.txt            # ✅ done (add pytest, pytest-flask for the tests/ folder)
└── .env.example                # needs pushing
```

**What's changing and why:**
- `content/` → `opportunities/`, `progress/` retired in favor of a smaller `saved/` blueprint (bookmarking is the only thing `progress` ever needed to do post-pivot — no reason to keep the old name or the extra surface area).
- `services.py` inside `opportunities/` — route handlers should stay thin (parse request → call service → serialize response). Business logic like "is this submission complete enough to go to review" or "apply the visibility filter" lives in one testable place instead of being copy-pasted across route functions as the API grows.
- `permissions.py` and `pagination.py` at the `app/` level (not inside one blueprint) because every blueprint needs both.
- `tests/` — not present in the original scaffold at all. Worth having from the start given moderation + tiered access is exactly the kind of logic that silently breaks when one blueprint changes and nobody notices it affected another.

## 4. Build order

Each phase is small enough to commit and check independently — matching how we've been working.

**Phase 0 — Unblock the app**
1. Push `app/__init__.py`, `app/cli.py`, `.env.example` (already written, just need committing)
2. `git mv backend/app/blueprints/content backend/app/blueprints/opportunities`
3. `git mv backend/app/blueprints/progress backend/app/blueprints/saved` (or delete and recreate — either works)
4. Confirm `flask run` boots without import errors (it'll 404 everywhere until routes exist, but it should *start*)

**Phase 1 — Auth**
- `POST /api/auth/register`, `POST /api/auth/login` (issues JWT access + refresh), `POST /api/auth/refresh`, `GET /api/auth/me`
- `permissions.py`: `@login_required`, `@admin_required`
- This has to come first — nothing else is testable without a logged-in user

**Phase 2 — Opportunities (read + submit)**
- `GET /api/opportunities` — paginated, applies `Opportunity.visible_query_for(current_user)`, filterable by category
- `GET /api/opportunities/<id>` — single item, same visibility check
- `POST /api/opportunities` — any logged-in user submits (status defaults to PENDING)
- `PATCH/DELETE /api/opportunities/<id>` — only the original poster, only while still PENDING

**Phase 3 — Saved opportunities**
- `POST/DELETE /api/opportunities/<id>/save`, `GET /api/saved` — small, but exercises the many-to-many relationship end to end

**Phase 4 — Admin**
- `GET /api/admin/opportunities/pending` — the moderation queue
- `POST /api/admin/opportunities/<id>/approve`, `POST /api/admin/opportunities/<id>/reject`
- `GET/POST /api/admin/categories` — category management
- `GET /api/admin/users`, `POST /api/admin/users/<id>/grant-premium` — the API equivalent of the `grant-premium` CLI command, for when there's a real admin UI instead of a terminal

**Phase 5 — Frontend wiring**
- Only after the API is stable: `apiClient.js`, `AuthContext.jsx`, then the learner-facing routes (`Dashboard`, `ModuleView` → repurposed as opportunity browsing/detail views), then the admin routes

## 5. Scalability notes (beyond what's already in `models.py`/`config.py`)

- **Pagination is mandatory, not optional**, on every list endpoint from day one — `config.DEFAULT_PAGE_SIZE`/`MAX_PAGE_SIZE` already exist; `pagination.py` should be the only place that turns a query into a page.
- **Category list is a good caching candidate** — it changes rarely (admin-managed) but gets read on every opportunity list/submit. Flask-Caching with a short TTL (or invalidated on admin category writes) avoids a repeated join for data that's effectively static.
- **Rate limiting is already wired (`Flask-Limiter`)** — apply it specifically to `POST /api/opportunities` (submission spam) and `POST /api/auth/login` (credential stuffing) once those routes exist.
- **Redis, not memory, for rate-limit storage and any caching**, the moment you run more than one backend process (`RATELIMIT_STORAGE_URI` in `.env` is already set up for this swap).
- **Full-text search** on opportunity title/description isn't in the schema yet — if search becomes a real feature, Postgres's built-in `tsvector` (via a generated column + GIN index) is the low-effort option before reaching for Elasticsearch.

---
*Next concrete step: Phase 0 — push the three missing files and do the blueprint rename, so the app can actually boot.*
