# OfferGo Enterprise Roadmap

## Product target

Build OfferGo into a public interview-prep product that supports:

- public access
- persistent user progress
- resume review and interview generation
- paid subscriptions
- stable online operation

## Recommended architecture evolution

### Phase 1: foundation hardening

- package backend code under `offergo_backend/`
- package core scripts under `offergo_scripts/`
- centralize runtime configuration
- isolate storage access behind replaceable abstractions
- keep current startup commands compatible

### Phase 2: service split

- deploy `web_mvp/` as a static frontend
- expose backend APIs from a dedicated service
- move question data loading from static JSON to API responses

### Phase 3: database adoption

- add Postgres
- migrate questions, jobs, visitor stats, and review records
- persist favorites/mastered progress server-side
- prepare for user accounts

### Phase 4: auth and billing

- user registration/login
- subscription plans
- payment integration
- quota limits for AI features

### Phase 5: operations

- background jobs for question ingestion
- monitoring and alerting
- admin dashboard
- content moderation and abuse control

## Current priority order

1. backend package and config cleanup
2. storage abstraction
3. frontend/backend split
4. Postgres integration
5. auth
6. billing

## Current anti-goals

- do not introduce too many frameworks before the data model is stable
- do not add payment before user and data persistence exist
- do not keep expanding features on top of file-only storage forever
