# Modernization Plan

## Phase 0 – Baseline & Safety Net
- Snapshot current behavior: catalogue configs, secrets, storage layout, docker scripts, launch configs.
- Audit existing tests (count, coverage gaps), identify missing integration/security suites.
- Tests: `./run_tests.sh` as baseline; capture duration, failures, coverage summary. Store log for later comparison.
- Extend `run_tests.sh` with `--suite` / `--pattern` flags (no execution yet) to allow focused suites while keeping the wrapper as the single entry point.

## Phase 1 – Unified Configuration & Startup Discipline
- Introduce typed settings module powering all entrypoints, scripts, launch configs.
- Enforce explicit JWT/secret requirements, eliminate silent fallbacks, standardize startup/shutdown helpers.
- Update Docker orchestration to consume the same settings and add health checks.
- Tests before: `./run_tests.sh --suite smoke`; after: `./run_tests.sh --suite unit --suite integration`.

## Phase 2 – Security Hardening (JWT, Groups, Isolation)
- Require explicit secrets with fingerprint verification and rotation workflow.
- Enforce group isolation in storage, add security middleware (CORS, rate limiting, auth scope checks), scrub secrets from logs.
- Tests before: `./run_tests.sh --suite auth`; after: `./run_tests.sh --suite auth` and `./run_tests.sh --suite security`.

## Phase 3 – Storage & Registry Architecture
- Separate blob storage from metadata persistence, add transactional writes, explicit exception hierarchy, integrity utilities.
- Introduce handler/theme registries managed via dependency injection.
- Tests before: `./run_tests.sh --suite storage`; after: `./run_tests.sh --suite storage` and `./run_tests.sh --suite integration --pattern "storage|render"`.

## Phase 4 – Validation, Async, and Error Handling
- Adopt shared Pydantic models, schema versioning, structured error middleware, fully async handlers with type hints.
- Tests before: `./run_tests.sh --suite handlers`; after: `./run_tests.sh --suite handlers` and `./run_tests.sh --suite async`.

## Phase 5 – Testing & CI Expansion
- Grow automated suite beyond 300 tests (unit, contract, integration, end-to-end), enhance `run_tests.sh` for suites/coverage and CI integration.
- Tests before: `./run_tests.sh --suite fast`; after: `./run_tests.sh --suite all --coverage` and `./run_tests.sh --suite e2e`.

## Phase 6 – Documentation, Operations & Verification
- Consolidate documentation (architecture, security, ops, developer guide), update launch configs, publish migration guide.
- Final verification: `./run_tests.sh --suite all --coverage` plus manual smoke checks (MCPO ↔ OpenWebUI, REST render, storage purge).

## Success Criteria Checklist
- Unified settings consumed everywhere.
- Auth fails fast without explicit secret; cross-service key fingerprints match.
- Storage abstractions emit consistent errors; corruption recovery in place.
- Shared validation models, async/typed codebase, structured logging.
- Server scripts and launch configs validated automatically.
- >300 automated tests, all green in CI using `run_tests.sh`.
- Documentation consolidated with clear ops/security/runbook coverage.
- Each phase completed via Analysis → Planning → Implementation → Verification → Documentation workflow.
