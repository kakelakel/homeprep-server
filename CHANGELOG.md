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

### Changed
- README and roadmap now treat user-controlled infrastructure, local-network operation, portability, backup and no mandatory telemetry as architectural constraints rather than optional privacy features.
- HomePrep Server is explicitly defined as a capability layer rather than a replacement for Home Assistant standalone operation.

### Planned next
- Bootstrap the Python/FastAPI project structure and test environment.
- Add Docker/Compose reference development environment.
- Add `/healthz`, `/readyz` and server/version identity.
- Add SQLite persistence and Alembic migrations.
- Implement the first Household + Inventory vertical slice.
- Add a minimal Web/diagnostics client after the API/persistence path is proven.
