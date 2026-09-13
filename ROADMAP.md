# HomePrep Server Roadmap

HomePrep Server is the self-hosted backend for the HomePrep ecosystem. This roadmap describes direction and sequencing, not fixed release dates.

## Permanent product principle

**Your preparedness. Your server. Your data.**

Core private household preparedness data will not require centralized HomePrep-operated storage.

Self-hosted operation is a permanent architectural commitment. Future optional managed services may exist, but they must remain optional and must not remove the user's ability to run HomePrep on infrastructure they control.

> **Convenience may be centralized. Ownership must not be.**

Every future architecture decision should be checked against this principle. See [DATA-OWNERSHIP.md](DATA-OWNERSHIP.md).

## Phase 1 — Foundation

- Define the server architecture and repository structure.
- Define the first shared HomePrep data contract.
- Define API versioning and client compatibility rules.
- Define authentication, pairing and per-client access.
- Define backup/restore and migration principles.
- Define deployment targets for Docker and Home Assistant.
- Establish development, test and CI workflows.
- Define security boundaries and safe defaults for local and remote deployments.
- Ensure core operation has no dependency on HomePrep-operated infrastructure.

## Phase 2 — Server MVP

- Start the API service.
- Add SQLite persistence.
- Add household-scoped storage.
- Implement core entities:
  - Inventory
  - Containers
  - Assets
  - Tasks
  - Plans
  - Targets
  - Shopping List
- Add schema migrations.
- Add basic authentication and client registration.
- Add a minimal HomePrep Web interface.
- Add health/status endpoints and basic diagnostics.
- Keep local-network-only deployment fully functional.

## Phase 3 — Import and Home Assistant bridge

- Add an import path from existing HomePrep Home Assistant storage.
- Add optional HomePrep Server configuration to the Home Assistant integration.
- Preserve Home Assistant-only mode.
- Verify create/update/delete flows in both directions.
- Verify recurring checks, task relationships and linked entities across the server boundary.
- Keep migration reversible through practical export/backup paths.

## Phase 4 — Synchronization

- Add revision-based synchronization.
- Add tombstone/deletion synchronization.
- Add client checkpoints/cursors.
- Add deterministic conflict handling.
- Add sync diagnostics and client status visibility.
- Validate mixed-version clients and upgrade paths.
- Ensure clients can identify exactly which server they are synchronized with.

## Phase 5 — Home Assistant App/Add-on

- Package HomePrep Server for Home Assistant OS/Supervised.
- Provide simple installation and onboarding.
- Integrate persistent storage correctly with Home Assistant.
- Support Home Assistant backup workflows where applicable.
- Add HomePrep-native backup and restore independent of Home Assistant backups.
- Avoid any requirement for an external HomePrep account during installation or operation.

## Phase 6 — Backup and resilience

- Scheduled local backups.
- Configurable retention.
- Manual export/download.
- Tested restore workflows.
- Optional external backup targets controlled by the user.
- Backup integrity checks and clear recovery status.
- Document disaster recovery and migration between hosts.

## Phase 7 — Web application

- Expand HomePrep Web from diagnostics/admin UI into a complete client.
- Responsive inventory and maintenance workflows.
- Household overview and readiness views.
- Plans, targets, tasks and shopping workflows.
- Client/device management.
- Backup/restore controls.
- Make server identity, storage and connection state visible rather than abstracting ownership away.

## Phase 8 — Android readiness

- Stabilize the public client API used by HomePrep Android.
- Add secure pairing tokens/QR-based onboarding.
- Support local-network and user-provided remote endpoints.
- Document server requirements for mobile access.
- Add notification/event interfaces where appropriate.
- Do not make a HomePrep-operated relay mandatory for normal Android use.

## Deployment targets

Priority order:

1. Docker / Docker Compose
2. Home Assistant App/Add-on
3. General standalone Docker deployment on NAS/home servers

Additional packaging can follow based on real demand.

## Storage direction

SQLite is the initial database target because HomePrep Server primarily serves one household and should be easy to operate, inspect and back up. Additional database backends may be considered later if real use cases require them.

Regardless of backend, the database remains part of the user's deployment rather than becoming a mandatory central HomePrep datastore.

## Non-negotiable architecture constraints

- No mandatory HomePrep cloud account for self-hosted operation.
- No mandatory central HomePrep database for core household data.
- No mandatory telemetry for core operation.
- No intentional lock-in that prevents practical backup, restore or migration.
- No future mobile/web client may silently move private household data away from the server selected by the user.
- Optional hosted services must coexist with the self-hosted path rather than replace it.

## Not a goal for the initial server

The first releases are not intended to become a general-purpose storage, messaging or social platform. The server should remain focused on HomePrep data and workflows.

## Related projects

- [`kakelakel/homeprep`](https://github.com/kakelakel/homeprep) — Home Assistant integration
- [`kakelakel/homeprep-android`](https://github.com/kakelakel/homeprep-android) — Android client
