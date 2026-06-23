# OfferGo Project Structure

## Current structure

```text
offergo_backend/        Python backend package
  config.py             Runtime settings
  storage.py            File/memory storage adapters (replaceable later)
offergo_scripts/        Core Python script package
web_mvp/                Static frontend assets
  data/                 Aggregated JSON data used by the MVP UI
question_bank/          Source question bank materials and processed outputs
resume_review_server.py Compatibility entrypoint for local startup
build_mvp_data.py       Compatibility wrapper for question aggregation
extract_questions.py    Compatibility wrapper for single-article extraction
批量跑种子源.py            Batch source runner
批量爬取详情页正文.py         Batch article fetcher
批量提炼题库.py            Batch extractor for grouped pages
爬取跳转目录网址.py          Directory link collector
prompt_templates.json   Prompt templates for resume review and interview generation
seed_sources.json       Seed URL configuration
render.yaml             Render deployment config
Procfile                Procfile-based startup config
ENTERPRISE_ROADMAP.md   Product and engineering evolution plan
DATABASE_SETUP.md       Database usage and migration notes
```

## Development conventions

- `offergo_backend/`: backend code only
- `web_mvp/`: frontend code and static data only
- `question_bank/`: raw and processed content assets
- root wrappers: keep current commands compatible first, then migrate gradually

## Recommended next refactors

1. Add a `scripts/` package and move root data scripts behind compatibility wrappers.
2. Add a `config/` directory for prompt, seed, and environment-related configuration.
3. Replace JSON/file persistence with Postgres for visitor stats, question records, and user progress.
4. Split frontend deployment from backend API deployment.
