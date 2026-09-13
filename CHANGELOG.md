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
- First local authentication layer with one-time owner setup, login, logout and current-user API.
- Password hashing using Argon2 through `pwdlib`; plaintext passwords are never stored.
- Opaque random Web sessions stored server-side as SHA-256 token hashes and delivered in HttpOnly SameSite cookies.
- Household and Inventory APIs now require an authenticated session, while health/readiness remain public.
- First-run Web setup creates the local administrator before any preparedness data is exposed.
- Authentication lifecycle tests covering setup, protected endpoints, logout, failed login and successful re-login.
- Native Windows packaging with a self-contained executable and Inno Setup installer.
- Native Windows Service mode so HomePrep Server starts automatically in the background without requiring an interactive user session.
- HomePrep Server Manager for Windows with service status, Web/API reachability, start/stop/restart controls, data-folder access and network settings.
- Standalone `config.json` support for user-managed bind address and port while explicit `HOMEPREP_*` environment variables retain precedence.
- Installer shortcuts now resolve the configured port dynamically through HomePrep Server Manager instead of assuming port 8080.
- Regression coverage for the single-household server lifecycle.
- Stable API error envelope with machine-readable error codes and structured validation details.
- HomePrep Web Inventory editing for name, quantity, unit and category using revision-safe `PATCH` requests.

### Changed
- README and roadmap now treat user-controlled infrastructure, local-network operation, portability, backup and no mandatory telemetry as architectural constraints rather than optional privacy features.
- HomePrep Server is explicitly defined as a capability layer rather than a replacement for Home Assistant standalone operation.
- Docker builds now use a Web build stage and ship one self-contained HomePrep Server image.
- Native development now defaults to a relative `data/` directory; Docker and appliance deployments can continue to override it with `HOMEPREP_DATA_DIR=/data`.
- Windows standalone installs keep persistent data and configuration under `%ProgramData%\HomePrep` and keep application binaries under Program Files.
- The MVP server now enforces one active household per installation; attempts to create another return `409 Conflict`.
- HomePrep Web now reflects the dedicated single-household model instead of exposing a household selector or an "add another household" flow.
- HomePrep Web now reloads Inventory after failed revision-sensitive edits/deletes so stale clients do not continue showing an outdated resource version.

### Planned next
- Validate the Windows Service + Server Manager flow on real hardware, including reboot persistence and custom-port changes.
- Extend the standalone manager concept to future standalone platform installers where appropriate.
- Add richer diagnostics around server/client state.
- Define and implement per-client/device pairing and revocation.
- Prove native backup/restore for the SQLite-based Server.
- Begin the explicit Home Assistant import/bridge path after the standalone install/auth flow is proven.
