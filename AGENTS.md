# weezdom-cli

## Project

`weezdom-cli` is the terminal client for Weezdom.ai knowledge graphs: search, entities, content, graph admin, and ontology documents. It does not write entities or facts; that stays on the MCP and REST APIs.

## Tech stack and layout

- Python `>=3.10`. Package `weezdom-cli`. Script `weezdom` → `weezdom_cli.cli:main` (`pyproject.toml`).
- Runtime: `click`, `httpx`, `rich`, `pyyaml`. Tests: `pytest`, `pytest-asyncio`, `respx`, `pytest-mock`.
- `src/weezdom_cli/cli.py` — Click commands. `client.py` — HTTP. `config.py` — `~/.weezdom/config.yaml`. `output.py` — table, json, text. `ontology_authoring.py` — draft import, save, publish.
- `tests/` — command tests, `test_integration_contract.py` (HTTP contract), `test_live_smoke.py` (opt-in live API).
- `requirements-lock.txt` — exact pins CI installs. `.github/workflows/test.yml` — tests. `.github/workflows/publish.yml` — PyPI on tags.
- `.claude/skills/weezdom-kg/` — how agents use Weezdom. Update it only when a user-facing command, auth rule, or ontology semantics change.

## Build, typecheck, lint, test

This repo has no typechecker and no linter. Do not add mypy, ruff, or a workflow for an unrelated change.

Match CI (`.github/workflows/test.yml`):

```bash
pip install -r requirements-lock.txt
pip install -e . --no-deps
pytest tests/ -v
```

CI runs that pytest on Python 3.10, 3.11, and 3.12. `requires-python` is `>=3.10`.

`python -m build` runs only in `publish.yml` on `v*` tags. Do not build a wheel to verify a normal change.

`pytest tests/ -v` skips `tests/test_live_smoke.py` unless `RUN_LIVE=1`.

## Coding style

No formatter is configured. Match the surrounding file.

- Query and admin commands: copy the nearest command in `src/weezdom_cli/cli.py` (start with `search`). Call the API through `WeezdomClient` and `run_async`.
- User-facing HTTP errors: `ClickExit` / `click_exit` in `src/weezdom_cli/client.py`. Do not leak raw `httpx` errors.
- Ontology import, save, and publish: copy `ontology_import` and `src/weezdom_cli/ontology_authoring.py`. Validation exits 2 via `AuthoringError`.
- `--format json` stays machine-readable on stdout. Table and text go through `src/weezdom_cli/output.py`.
- Tests: `tests/test_commands_query.py` (`CliRunner`, `respx`, `mock_config`) and `tests/test_integration_contract.py` (method, path, headers, body).

## Prefer the smallest possible change

Fix the task in the fewest lines. Do not refactor neighbors, rename public commands, or bump unrelated dependencies.

## Always run the relevant tests

A change is not done until the tests that cover it pass.

- The file you changed, for example `pytest tests/test_commands_query.py -v`. Command files: `test_commands_query.py`, `test_commands_graph.py`, `test_commands_content.py`, `test_commands_workspace.py`, `test_commands_ontology.py`, `test_commands_ontology_author.py`.
- HTTP shape: `pytest tests/test_integration_contract.py -v`
- Before a PR, the CI command: `pytest tests/ -v`

Done means it works against the running service. If the change sends or parses API traffic, mocks are not enough. Run the live smoke against the Weezdom **staging** API:

```bash
RUN_LIVE=1 WEEZDOM_BASE_URL=<staging-api-url> WEEZDOM_API_KEY=<wdm-key> pytest tests/test_live_smoke.py -v -s
```

`test_live_smoke.py` defaults `WEEZDOM_BASE_URL` to production (`https://weezdomai-production.up.railway.app`). Set the staging URL. Never print the key or a shell line with the key expanded. If no staging key is available, say so in the PR. Do not point the test at production to make it pass.

## Pull requests

- Branch: `<type>/<short-kebab-summary>` (`fix/search-empty-body`). Renovate keeps `renovate/*`. Cloud agents whose runtime requires a `cursor/` branch still use Conventional Commits.
- Commits: Conventional Commits, as in `chore(deps): update dependency pytest to v9.2.0`. One purpose per PR.
- PR description: what changed, why, and the exact test commands plus results. Say whether staging verification ran.
- Target `main`. PRs are squash-merged once CI passes on Python 3.10, 3.11, and 3.12.

## Do not modify

- `.github/workflows/publish.yml` — `v*` tags only, `environment: release` (manual approval), PyPI publish. That job pins Python 3.15 for the release.
- `requirements-lock.txt` by hand. Regenerate it (`.cursor/rules/dependencies.mdc`).
- `.secrets.baseline` unless the task is a reviewed secret-scan allowlist update.
- `~/.weezdom/` — local credentials, not source.

## Architecture

- Auth header is `X-API-Key` (`wdm_...`). Do not send `Authorization: Bearer` for these keys. Graph-scoped calls also send `X-Graph-Id` from `active_graph_id` (`src/weezdom_cli/client.py`).
- Config is `~/.weezdom/config.yaml`, directory `0700`, file `0600` (`src/weezdom_cli/config.py`). `api_url` must start with `https://`. Default URL is `https://weezdomai-production.up.railway.app`.
- Set keys with `weezdom auth login` (hidden prompt). New commands must not accept an API key argument. `config show` and `auth status` mask the key (`src/weezdom_cli/cli.py`).
- `WEEZDOM_API_KEY` and `WEEZDOM_BASE_URL` override the stored login for ontology authoring (`resolve_credentials` in `ontology_authoring.py`).
- Deep JSON (`import`, `save`, `publish`) writes an `ontology_versions` document. Import and save are drafts. Publish makes a draft the live version and does not materialise (no FalkorDB, Weaviate, or `graph_publish`). Those calls do not send `X-Graph-Id`. Autonomous build is `suggest`, `create`, `build`, `score`, `improve`. Authoring needs an unscoped personal admin or editor key. Viewer, Hermes, and workspace reader keys get 403.
- The CLI does not create entities or facts.

## Dependencies

Exact pins. CI installs `requirements-lock.txt`, then `pip install -e . --no-deps`. When you add or change a dependency, set `==` in `pyproject.toml` and regenerate the lock. Leave an existing `>=` floor unchanged unless you are changing that package. Do not hand-bump unrelated packages; Renovate does that.

## Secrets

Never commit or print secrets, `.env` files, `*.key`, `*.pem`, or API keys. Tests use fake keys (`tests/conftest.py`). Logs and PR text get the masked form only.

## Where work happens

Use Cursor cloud agents. Do not clone this repo onto a personal computer, and do not ask anyone to.
