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
- Runtime configuration through `HOMEPREP_*` environment variables.
- Initial SQLite/SQLAlchemy engine foundation.
- Initial Alembic migration environment.
- Dockerfile and Docker Compose reference deployment with persistent `/data` storage and health check.
- Pytest system endpoint tests and Ruff lint configuration.
- GitHub Actions CI for lint/tests and Docker image build.

### Changed
- README and roadmap now treat user-controlled infrastructure, local-network operation, portability, backup and no mandatory telemetry as architectural constraints rather than optional privacy features.
- HomePrep Server is explicitly defined as a capability layer rather than a replacement for Home Assistant standalone operation.

### Planned next
- Make readiness verify the real database connection.
- Add the first database migration.
- Implement Household persistence and server identity.
- Implement the first Inventory vertical slice.
- Add a minimal Web/diagnostics client after the API/persistence path is proven.
