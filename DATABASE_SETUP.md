# OfferGo Database Setup

## Current state

OfferGo now supports two storage modes for runtime stats:

- `file` (default): visitor stats stored in `.runtime/visitor_stats.json`
- `sqlite`: visitor stats stored in `.runtime/offergo.db`

Questions can now be imported into SQLite for the next migration phase.
Favorites / mastered progress can also be persisted in SQLite and is keyed by anonymous visitor cookie for now.

## Environment variables

- `OFFERGO_STORAGE_MODE=file|sqlite`
- `OFFERGO_DB_PATH=/path/to/offergo.db`
- `RESUME_REVIEW_HOST`
- `RESUME_REVIEW_PORT`

## Initialize / import questions

```powershell
python .\import_questions_to_db.py
```

This imports `web_mvp/data/questions.json` into `.runtime/offergo.db`.

## Run server with SQLite visitor stats

```powershell
$env:OFFERGO_STORAGE_MODE="sqlite"
python .\resume_review_server.py
```

## Current progress APIs

- `GET /api/user-progress`
- `POST /api/user-progress`
- `POST /api/user-progress/sync`

These currently persist anonymous visitor learning progress by cookie and are designed to be upgraded later to account-based progress.

## Next migration targets

1. Add question read API backed by SQLite
2. Add account-based progress on top of anonymous visitor progress
3. Add users and subscriptions
4. Replace SQLite with Postgres in production
