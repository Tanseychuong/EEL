# `apps/opportunities`

The core domain: categories, listings, moderation, premium early access,
and saved bookmarks. Both user-submitted and auto-fetched opportunities
are rows in the same `Opportunity` table — `source_type` tells them apart,
but there's one moderation queue and one visibility rule regardless of
where a listing came from.

## Files

| File | Purpose |
|---|---|
| `models.py` | `OpportunityCategory`, `Opportunity`, `SavedOpportunity` |
| `admin.py` | The moderation queue itself — filter by `status=pending`, select rows, bulk **Approve**/**Reject** |
| `permissions.py` | `IsOwnerOrReadOnly`, `CanVerifyOpportunity` |
| `serializers.py` | `OpportunitySerializer` (read), `OpportunityCreateSerializer` (write), `OpportunityRejectSerializer`, `SavedOpportunitySerializer` |
| `services.py` | `submit_opportunity`, `approve_opportunity`, `reject_opportunity`, `list_visible_opportunities` — the one place each of these actions happens, called from both `views.py` and (approve/reject) `admin.py`'s bulk actions |
| `urls.py` | DRF router — see endpoint table below |

## Where moderator privilege actually lives

`Opportunity.Meta.permissions` defines `can_verify_opportunity`. It is **not**
a field on `User` — it's a Django permission, granted to a `Moderators`
group from `/admin/` (see `docs/accounts.md` for the exact steps). Both
`CanVerifyOpportunity` (the DRF permission class) and the admin's bulk
actions check this same permission, so there's one rule, checked in two
places that both need it — not two implementations of the rule.

## Premium early access, concretely

`Opportunity.approve()` sets two timestamps: `published_at` (now) and
`free_access_at` (`published_at` + `EARLY_ACCESS_HOURS`, default 48 —
configurable in `.env`). `Opportunity.visible_to(user)` is a **queryset**
method (not a Python-side filter) — it does the premium/free split as a
`WHERE` clause, so it stays index-backed as the table grows. Every list
endpoint goes through `services.list_visible_opportunities()`, which calls
this — there's no second place that duplicates the visibility logic.

## Endpoints

All under `/api/opportunities/` (router-generated + custom `@action`s):

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/` | any | list — visibility rule + optional `?category=<slug>` applied |
| POST | `/` | logged in | submit a new opportunity (always starts `PENDING`) |
| GET | `/<id>/` | any* | retrieve — visible opportunities, or your own regardless of status |
| PATCH/DELETE | `/<id>/` | owner only | only while still `PENDING` |
| GET | `/categories/` | any | active categories, for filter dropdowns |
| GET | `/pending/` | moderator/admin | the moderation queue, API-side (admin panel's bulk actions cover this too — this is for a future custom moderator UI) |
| POST | `/<id>/approve/` | moderator/admin | approve — sets `published_at`/`free_access_at` |
| POST | `/<id>/reject/` | moderator/admin | body: `{"reason": "..."}` |
| POST | `/<id>/save/` | logged in | bookmark |
| DELETE | `/<id>/unsave/` | logged in | remove bookmark |
| GET | `/saved/` | logged in | your bookmarked opportunities |

*`retrieve` is intentionally more permissive than `list` — a submitter can check the status of their own pending opportunity by ID even though it won't show up in the general list yet.

## `fetch_source` — the forward reference to `ingestion`

`Opportunity.fetch_source` is a nullable FK to `ingestion.FetchSource`,
set only when `source_type=FETCHED`. It's nullable specifically so this
app doesn't need to know anything about how ingestion works internally —
just which source a listing came from, when there is one.

## Not yet built

- No API endpoint for admins to create/edit categories (intentionally — that's a `/admin/` job, at least for now)
- `services.py` doesn't yet enforce "can't submit a duplicate of an existing pending/approved opportunity" — worth adding once real usage shows whether that's actually a problem
