# Repository Guidelines

## Project Structure & Module Organization
- Core Flask app lives in `app/`: `__init__.py` (app factory), `routes/` (blueprints), `services/` (crawler, analyzer, email, scheduler), `models/` (SQLAlchemy), `utils/` (config, logger, ElasticSearch client), and Jinja templates/static assets.
- Data and runtime artifacts: `data/` (SQLite), `logs/` (app/crawler/email/error logs), `flask_session/` and `instance/` for Flask session/config.
- Operations: `scripts/` for DB init, user creation, ES index/ILM setup, mail tests, and deploy helper; `docs/OPERATIONS.md` for production runbook.
- Tests reside in `tests/` (unit, integration, ILM/ES mapping, performance).

## Build, Test, and Development Commands
- Environment setup: `python -m venv venv && source venv/bin/activate` then `pip install -r requirements.txt`.
- Local run: set `.env` (copy from `.env.example`), initialize DB `python scripts/init_db.py init`, then `python run.py`.
- Docker stack: `docker-compose up -d` to start Flask + ElasticSearch, `docker-compose logs -f` to tail, `docker-compose down` to stop.
- ElasticSearch prep: `python scripts/setup_es_index.py create` and `python scripts/setup_ilm.py setup` (after ES is up).
- Testing: `pytest` for full suite, `pytest tests/test_integration.py -v` for pipeline checks, `pytest --cov=app --cov-report=html` for coverage.

## Coding Style & Naming Conventions
- Python 3.9+, PEP 8 with 4-space indents; prefer type hints and descriptive logging.
- Format with `black` (default settings) and lint with `flake8` before submitting.
- Modules/packages use `snake_case`; classes in `CapWords`; functions/vars in `snake_case`. Templates keep IDs/classes consistent with existing naming in `app/templates/`.

## Testing Guidelines
- Use `pytest`; name files `test_*.py` and mirror module names. Group fixtures per feature; avoid hitting live services—mock OpenAI/ElasticSearch where possible.
- Keep integration tests deterministic (seed data via `scripts/init_db.py` or factory functions). Update coverage reports when touching core services.

## Commit & Pull Request Guidelines
- Follow existing history style: lowercase type prefixes (`chore:`, `fix:`, `개선:`/`UI 개선:`) plus a concise summary in Korean or English.
- Commits should be focused and small; reference tickets/SRS items in body when relevant (e.g., `SRS 7.2.1`).
- PRs include: scope summary, testing commands/results, config or migration notes, and UI screenshots when templates change. Link related issues and note any ES/DB migrations.

## Security & Configuration Tips
- Never commit secrets; use `.env`/`.env.production` and keep keys (OpenAI, Gmail, Flask secret) out of git. Check `.gitignore` before adding files from `data/`, `logs/`, or session stores.
- When running tests locally, ensure ElasticSearch is available or mock clients to avoid destructive index changes.

## 에이전트 지침
- 모든 질의응답은 한국어로 작성하고, 필요 시 영어 식별자나 명령은 코드 블록으로만 표기한다.
