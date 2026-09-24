# `apps/ingestion`

Everything about *how* opportunities get fetched automatically. Kept
deliberately separate from `apps/opportunities` — adding a new source
later means adding one `FetchSource` row and (if it's a genuinely new
kind of source) one connector class. Nothing in `opportunities` changes.

## Files

| File | Purpose |
|---|---|
| `models.py` | `FetchSource` (config: name, connector type, URL, default category) and `FetchLog` (one row per run — status, counts, errors) |
| `connectors/base.py` | `BaseConnector` — the interface every connector implements: `fetch() -> list[dict]` |
| `connectors/rss_connector.py` | The one working example — parses an RSS feed with the standard library, no external feed-parsing dependency |
| `connectors/__init__.py` | `CONNECTOR_REGISTRY` — maps `FetchSource.connector_type` to its class |
| `services.py` | `fetch_source(source)` — runs one source, de-dupes by URL, creates `Opportunity` rows, writes the `FetchLog`. The **one** implementation, called from both the management command and the admin's "Fetch now" action |
| `admin.py` | Manage sources, trigger fetches on demand, browse run history (read-only — logs are never hand-edited) |
| `management/commands/fetch_opportunities.py` | `python manage.py fetch_opportunities` — the cron-scheduled path |
| `urls.py` | One admin-only endpoint (`/api/ingestion/logs/`) for a future ops dashboard — ingestion has no public API otherwise |

## How a fetched opportunity becomes visible

Same rules as a user submission — `fetch_source()` creates every new item
as `status=PENDING`, `source_type=FETCHED`. **It never auto-approves
anything.** A moderator or admin has to explicitly approve it (from the
same `/admin/` moderation queue used for user submissions, or the API's
`/approve/` action) before it goes live and the premium early-access
clock starts. Fetching and moderation are fully decoupled on purpose —
this is exactly the "manually verified" requirement.

## De-duplication

`fetch_source()` skips creating an item if an `Opportunity` with the same
`opportunity_url` already exists. This is intentionally simple (URL
equality, not fuzzy title matching) — good enough while there's one
connector type; revisit if a source's URLs turn out to be unstable
(e.g. session tokens in the URL) or a source has no URL at all.

## Running it

```bash
# One-off / manual:
python manage.py fetch_opportunities
python manage.py fetch_opportunities --source "Some Source Name"

# Scheduled — add a cron entry (or your host's scheduled-task equivalent):
0 * * * * cd /path/to/backend && venv/bin/python manage.py fetch_opportunities
```

There's no Celery/task queue here — a plain management command on a cron
schedule is enough at this scale, and it's what `services.fetch_source()`
being framework-agnostic (just Django ORM calls) makes trivial to run
either way.

## Adding a new source

1. If it's RSS/Atom, no new code — just add a `FetchSource` row from
   `/admin/` with `connector_type=rss` and the feed URL.
2. If it's a genuinely new kind of source (a JSON API, an HTML page with
   no feed), write one class implementing `BaseConnector.fetch()`,
   register it in `connectors/__init__.py`'s `CONNECTOR_REGISTRY`, and add
   the corresponding value to `FetchSource.ConnectorType`.

## Not yet built

- No real sources are configured yet — `RSSConnector` is tested against
  the interface, not against a specific real feed. Point it at an actual
  URL and check the first run's `FetchLog` before trusting it unattended.
- `requests` was added to `requirements.txt` for this app specifically —
  make sure it's installed (`pip install -r requirements.txt`) before
  running a fetch.
