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
- Household and Inventory APIs now require authenticated access, while health/readiness remain public.
- First-run Web setup creates the local administrator before any preparedness data is exposed.
- Authentication lifecycle tests covering setup, protected endpoints, logout, failed login and successful re-login.
- Native Windows packaging with a self-contained executable and Inno Setup installer.
- Native Windows Service mode so HomePrep Server starts automatically in the background without requiring an interactive user session.
- HomePrep Server Manager for Windows with service status, Web/API reachability, start/stop/restart controls, data-folder access and network settings.
- Standalone `config.json` support for user-managed bind address and port while explicit `HOMEPREP_*` environment variables retain precedence.
- Installer shortcuts resolve the configured port dynamically through HomePrep Server Manager instead of assuming port 8080.
- Regression coverage for the single-household server lifecycle.
- Stable API error envelope with machine-readable error codes and structured validation details.
- HomePrep Web Inventory editing for name, quantity, unit and category using revision-safe `PATCH` requests.
- Revocable per-client credentials with separate client identity, client type, access role, last-seen metadata and hashed bearer tokens.
- Initial client access roles: `full_access` and `read_only`.
- Owner-managed client listing, creation and revocation endpoints.
- One-time client pairing requests with a 10-minute expiry and single-use exchange into a permanent client credential.
- Pairing flow designed for Home Assistant first and reusable by future QR-based Android onboarding.
- Authenticated `GET /api/v1/context` endpoint returning server identity/version, client principal/role and active Household for post-pairing client verification.
- Client-credential tests covering full-access Home Assistant behavior, read-only clients, credential revocation and post-pairing context discovery.
- Portable backup format v1 containing `manifest.json` and a consistent SQLite snapshot created through SQLite's backup API.
- Backup manifest metadata including format version, Server version/identity, migration version, timestamp, Household metadata and included components.
- Owner-only backup administration API for creating and listing native Server backups.
- Backup archive validation including format checks and SQLite `PRAGMA integrity_check`.
- Offline restore primitive with automatic pre-restore safety backup and database replacement only after validation.
- Launcher commands for `--validate-backup` and `--restore-backup`.
- Integration tests that inspect backup contents and prove a backup → mutate → restore round trip, including the pre-restore safety snapshot.
- Portable backup scheduler with `off`, `daily` and `weekly` cadence plus configurable file retention.
- Windows Server Manager backup controls for **Back up now**, backup-folder access, schedule, retention and validated restore.
- Windows Server Manager **Check for updates** using the latest published GitHub Release as the stable update channel.

### Changed
- README and roadmap treat user-controlled infrastructure, local-network operation, portability, backup and no mandatory telemetry as architectural constraints rather than optional privacy features.
- HomePrep Server is explicitly defined as a capability layer rather than a replacement for Home Assistant standalone operation.
- Docker builds use a Web build stage and ship one self-contained HomePrep Server image.
- Native development defaults to a relative `data/` directory; Docker and appliance deployments can continue to override it with `HOMEPREP_DATA_DIR=/data`.
- Windows standalone installs keep persistent data and configuration under `%ProgramData%\HomePrep` and application binaries under Program Files.
- The MVP server enforces one active household per installation; attempts to create another return `409 Conflict`.
- HomePrep Web reflects the dedicated single-household model instead of exposing a household selector or an "add another household" flow.
- HomePrep Web reloads Inventory after failed revision-sensitive edits/deletes so stale clients do not continue showing an outdated resource version.
- Household and Inventory authorization accepts either an authenticated Web user or a valid non-revoked client credential; write endpoints reject read-only clients.
- Backup creation, validation, restore and scheduling live in Server core rather than a Windows-only implementation; Server Manager is an administration surface over the shared subsystem.
- Backup/restore requirements explicitly include a versioned portable migration format across supported deployments.
- Windows Service installation/startup waits for Service Control Manager registration before attempting start, avoiding registration-race failures on slower systems.
- Windows update handling now has a user-facing check path; automatic installer execution remains intentionally disabled until package authenticity, pre-upgrade backup and recovery behavior are fully proven.

### Planned next
- Finish real-Windows validation of the new Manager backup/schedule/restore/update controls.
- Add richer backup status/failure diagnostics rather than silently swallowing scheduler failures.
- Define signed release-asset/update handoff and pre-upgrade backup behavior before opt-in automatic updates.
- Begin the explicit Home Assistant import/bridge path now that pairing and native recovery foundations exist.
- Prove create/update/delete/tombstone round trips between Home Assistant, Server and Web before calling synchronization stable.
