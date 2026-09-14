# HomePrep Server Changelog

All notable user-facing and project-level changes to HomePrep Server will be documented here.

## Unreleased

### Added
- Initial HomePrep Server repository and public project definition.
- Self-hosted-first product direction: **Your preparedness. Your server. Your data.**
- Permanent data-ownership commitment and optional-server architecture.
- Python/FastAPI/Pydantic/SQLAlchemy/Alembic/SQLite Server stack.
- React/TypeScript/Vite Web client bundled into Server distributions.
- `/healthz`, `/readyz`, `/api/v1/system/info` and stable per-installation Server identity.
- Household + Inventory persistent domain slice with revision-safe writes, `409 Conflict` and Inventory tombstones.
- Containers, Household Assets, Tasks/recurring inspections, Plans, Targets, Guidance and readiness APIs matching the established HomePrep domain direction.
- Stable normalized API error envelope with machine-readable codes and validation details.
- Local human authentication with one-time owner setup, Argon2 passwords and opaque HttpOnly server-side sessions.
- Human RBAC for Web and future Android users with `owner`, `editor` and `viewer` roles.
- Owner-only user administration API for listing/creating users, changing roles, resetting passwords and disabling/re-enabling accounts.
- Last-active-owner protection so a Server cannot accidentally remove its final administrator.
- Session revocation when a user is disabled or has their password reset.
- Role-aware Web behavior: owners administer users, editors may modify preparedness data and viewers receive a read-only preparedness experience.
- Separate revocable machine/integration credentials with `full_access` / `read_only`, client type, last-seen state and token hashing.
- Owner-managed client listing, issuance and revocation.
- HA-oriented one-time pairing with 10-minute expiry, single-use exchange and `/api/v1/context` verification.
- Canonical Inventory taxonomy API at `/api/v1/taxonomy/inventory`, mirroring HA categories, item types, units and category form metadata.
- HA ↔ Server schema-contract regression coverage for Inventory, Containers, Assets, Tasks, Plans and Targets so accidental field loss is caught before migration/sync work ships.
- Household profile responses expose the HA-compatible stable `id` while retaining `household_id` for existing Server clients.
- Docker reference deployment and CI for Python/API, Web and Docker.
- Native Windows installer, Windows Service and HomePrep Server Manager.
- Windows Manager controls for service lifecycle, port, Local/LAN bind, data folder and Windows Services.
- Portable backup format v1 (`manifest.json` + consistent SQLite snapshot), validation and offline restore.
- Pre-restore safety backups and backup → mutate → restore regression coverage.
- Daily/Weekly/Off backup scheduler with retention.
- Windows Manager backup/schedule/retention/restore controls.
- Windows Manager **Check for updates** using GitHub Releases.
- Canonical HomePrep icon/logo branding in Web, Windows executables and the Windows installer wizard.
- Printable/offline preparedness exports are now an explicit roadmap requirement for Server/Web resilience.

### Changed
- Inventory storage/API now carries the HA v4 shared field contract, including item type, expiry/check lifecycle data, notes, Container association, image metadata, revisions/schema version and tombstone metadata.
- Web Inventory creation now consumes the canonical Server taxonomy instead of a small hard-coded subset and supports category, item type, full unit vocabulary, expiry, last/next check, notes and Container assignment.
- Human accounts and machine/integration identities are explicitly separate authorization concepts. Home Assistant is a paired integration client, not an `owner`/`editor`/`viewer` human user.
- `owner` can administer users, client credentials/pairing, backups and initial Household provisioning.
- `editor` can read/write normal preparedness/domain data but cannot administer security/access surfaces.
- `viewer` can read normal preparedness/domain data but write requests are rejected with `403 write_access_required`.
- Client/pairing administration and native backup administration are owner-only.
- Household creation is owner-only during the single-Household Server bootstrap; normal authenticated reads remain available to authorized users/integrations.
- HomePrep Web exposes role/account state and hides mutation controls for viewers.
- Windows restore reporting distinguishes the actual database restore result from a later service-restart failure: a successful restore is no longer reported as failed merely because automatic restart did not complete.
- If Manager stops a previously running HomePrep service for restore, it now attempts to start that service again even when the restore command itself fails, avoiding a silently stopped Server after a failed recovery attempt.
- Backup creation/validation explicitly closes/reset database state so Windows temp-file cleanup does not produce false failure dialogs.
- HomePrep Server remains a capability layer rather than a replacement for Home Assistant standalone operation.
- MVP remains one active Household per Server installation.
- Backup/restore stays Server-core functionality, with Manager acting as administration UI rather than a separate implementation.
- Update discovery remains user-facing only; unattended installer execution is deferred until authenticity, pre-upgrade backup and recovery behavior are proven.

### Current execution order
- Complete real-Windows validation of the current branded parity/recovery build.
- Continue the dedicated security/intrusion-resistance hardening pass (rate limits, CSRF/session/cookie policy, security headers, proxy/HTTPS behavior, audit/security events, request limits, supply-chain/release hardening).
- Continue shared functionality parity where Server/Web still trails mature HA standalone workflows, especially Shopping/replacement lifecycle and migration-specific contracts.
- Then complete explicit HA → Server import/migration and synchronization proof against the shared model.
- Package the same Server runtime as a Home Assistant App/Add-on after client/server behavior is proven.
