# Backend Layering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce backend coupling by isolating JSON storage, moving essay-specific data flows behind a repository/service boundary, and replacing route-to-app imports with Flask Blueprints without changing public API behavior.

**Architecture:** `backend/data.py` remains a compatibility facade over a small `JsonStore`. Essay routes and SSG consume `EssayRepository`/`EssayService` for essay metadata, password state, public projections, and HTML synchronization. Each route module owns a Blueprint; `backend/app.py` only creates the app, installs guards, and registers blueprints.

**Tech Stack:** Python 3, Flask, pytest, JSON files, existing Fernet/PBKDF2 encryption.

## Global Constraints

- Preserve all existing `/api/*` paths, methods, status codes, and JSON shapes.
- Preserve password encryption, public metadata visibility, and no-password-leak guarantees.
- Keep the zero-dependency application architecture; do not add a repository framework.
- Keep photo, music, and unrelated data changes out of this refactor.
- Run `pytest -q`, `node --check` for all JavaScript, and `git diff --check` after each migration batch.

### Task 1: Isolate JSON storage

**Files:**
- Create: `backend/storage/__init__.py`
- Create: `backend/storage/json_store.py`
- Modify: `backend/data.py`
- Test: `tests/test_storage.py`

- [x] Add tests for missing-file defaults, malformed JSON errors, and atomic replacement.
- [x] Implement `JsonStore.read()` and `JsonStore.write()` with the existing JSON behavior.
- [x] Make `load_json()` and `atomic_write_json()` delegate to the store so existing imports keep working.
- [x] Run `pytest tests/test_storage.py tests/test_ssg.py -q`.

### Task 2: Add essay repository/service seams

**Files:**
- Create: `backend/essay_repository.py`
- Create: `backend/essay_service.py`
- Modify: `backend/routes/essays.py`
- Modify: `backend/ssg.py`
- Test: `tests/test_routes.py`, `tests/test_ssg.py`

- [x] Add repository methods for listing, finding, saving essays, and public projections.
- [x] Add service methods for admin projections and public projections.
- [x] Migrate essay route read/write paths and public-feed generation to the seams.
- [x] Keep existing helper functions as compatibility wrappers until all callers migrate.
- [x] Run the full essay route and SSG test groups.

### Task 3: Convert route modules to Blueprints

**Files:**
- Modify: `backend/app.py`
- Modify: `backend/auth.py`
- Modify: `backend/routes/__init__.py`
- Modify: `backend/routes/*.py`
- Test: `tests/test_routes.py`, `tests/test_coverage.py`

- [x] Replace each route module's `from backend.app import app` with a module-owned Blueprint.
- [x] Register all Blueprints from one explicit `register_blueprints(app)` function.
- [x] Preserve route names used by tests and existing clients.
- [x] Remove side-effect route imports from `backend/app.py`.
- [x] Run the full test suite and inspect Flask's URL map for all expected routes.

### Task 4: Verify and review

- [x] Run `pytest -q` and JavaScript syntax checks.
- [x] Run `git diff --check`.
- [x] Confirm no route module imports `app`.
- [x] Confirm graph/report no longer shows the app-to-route import triangle.
- [x] Review the diff for unnecessary wrappers or API drift.
