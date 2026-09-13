# HomePrep Server Changelog

All notable user-facing and project-level changes to HomePrep Server will be documented here.

## Unreleased

### Added
- Initial HomePrep Server repository and public project definition.
- Self-hosted-first product direction: **Your preparedness. Your server. Your data.**
- Permanent data-ownership commitment documented in `DATA-OWNERSHIP.md`.
- Explicit rule that core private household preparedness data will not require centralized HomePrep-operated storage.
- Explicit requirement that any future managed/hosted service remain optional and coexist with self-hosting.
- Initial roadmap covering Docker, Home Assistant App/Add-on, Web, synchronization, backup/restore and Android readiness.
- Separation between the existing Home Assistant integration and the new optional server layer.
- `ARCHITECTURE.md` defining the three permanent operating modes and the first Server vertical slice.
- `API-CONTRACT.md` defining the initial versioned REST/JSON API direction, common metadata and optimistic concurrency rules.
- `DATA-MODEL.md` documenting the shared HomePrep object model and first Household/Inventory implementation scope.
- `DEPLOYMENT.md` documenting Docker-first deployment, Home Assistant App/Add-on packaging and standalone self-hosting.
- `BACKUP-RESTORE.md` documenting native backup, restore, portability and recovery principles.
- Initial implementation stack selected: Python, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic and SQLite.
- Initial Web direction selected: TypeScript, React and Vite, built into the Server distribution for production.
- First runnable FastAPI application skeleton.
- `/healthz`, `/readyz` and `/api/v1/system/info` system endpoints.
- Stable per-installation `server_id` persisted in the user-controlled data directory.
- Database-aware readiness checks.
- Runtime configuration through `HOMEPREP_*` environment variables.
- SQLite/SQLAlchemy engine and session foundation.
- Alembic migration environment plus the first schema migration.
- First persistent `Household` model and API, including household listing for local clients.
- First persistent `Inventory` model and CRUD API.
- Inventory revision checks with `409 Conflict` for stale writes.
- Soft-delete/tombstone behavior for Inventory records.
- First HomePrep Web client using React, TypeScript and Vite.
- Web dashboard showing server status, active household and live Inventory data.
- Web flows for creating households, adding Inventory items and soft-deleting Inventory items.
- HomePrep Web is bundled into the production Server image and served by FastAPI.
- Vite development proxy for running Web and API separately during development.
- Dedicated Web build job in GitHub Actions CI.
- Docker startup applies database migrations before starting the API.
- Dockerfile and Docker Compose reference deployment with persistent `/data` storage and health check.
- Pytest coverage for system endpoints and the first Household/Inventory create, list, update, conflict and delete flow.
- GitHub Actions CI for lint, migration smoke test, tests, Web build and Docker image build.

### Changed
- README and roadmap now treat user-controlled infrastructure, local-network operation, portability, backup and no mandatory telemetry as architectural constraints rather than optional privacy features.
- HomePrep Server is explicitly defined as a capability layer rather than a replacement for Home Assistant standalone operation.
- Docker builds now use a Web build stage and ship one self-contained HomePrep Server image.

### Planned next
- Harden Household lifecycle and bootstrap behavior for a single-household server.
- Add clearer API error envelopes and validation behavior.
- Add Web edit/update flows and richer diagnostics.
- Prove a full Docker runtime smoke test with the bundled Web client.
- Then begin the explicit Home Assistant import/bridge path rather than expanding every domain at once.
