# payment-lead-agent

Headless lead-generation agent that scans public job sources (Greenhouse, Lever, Hacker News
"Who is Hiring?"), scores postings with an LLM for payment-idempotency consulting potential,
and sends high-urgency leads to Telegram. Scheduled via GitHub Actions.

**Status:** under staged development. See the roadmap below.

## Roadmap

| Stage | Scope |
|---|---|
| 0 | Scaffold, tooling, config, logging, CI (this stage) |
| 1 | Domain models |
| 2 | Ingestion |
| 3 | LLM evaluator |
| 4 | Telegram notifier |
| 5 | Orchestration, dedup, metrics |
| 6 | Scheduled GitHub Actions workflow |
| 7 | Tuning and documentation |

## Local setup

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e . --no-deps
cp .env.example .env   # fill in secrets
pre-commit install
```

## Quality checks

```bash
ruff check . && ruff format --check .
mypy
pytest -m "not live"
```

## Workflow

Work happens on a branch per stage (`stage-N-...`), merged into `main` through a pull request
that passes CI. Never commit `.env`.
