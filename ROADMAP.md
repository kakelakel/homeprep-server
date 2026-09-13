# HomePrep Server Roadmap

HomePrep Server is the self-hosted backend for the HomePrep ecosystem. This roadmap describes direction and sequencing, not fixed release dates.

## Product principle

**Your preparedness. Your server. Your data.**

The server should make HomePrep usable across multiple clients without making a central HomePrep-operated cloud service a requirement.

## Phase 1 — Foundation

- Define the server architecture and repository structure.
- Define the first shared HomePrep data contract.
- Define API versioning and client compatibility rules.
- Define authentication, pairing and per-client access.
- Define backup/restore and migration principles.
- Define deployment targets for Docker and Home Assistant.
- Establish development, test and CI workflows.

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

## Phase 3 — Import and Home Assistant bridge

- Add an import path from existing HomePrep Home Assistant storage.
- Add optional HomePrep Server configuration to the Home Assistant integration.
- Preserve Home Assistant-only mode.
- Verify create/update/delete flows in both directions.
- Verify recurring checks, task relationships and linked entities across the server boundary.

## Phase 4 — Synchronization

- Add revision-based synchronization.
- Add tombstone/deletion synchronization.
- Add client checkpoints/cursors.
- Add deterministic conflict handling.
- Add sync diagnostics and client status visibility.
- Validate mixed-version clients and upgrade paths.

## Phase 5 — Home Assistant App/Add-on

- Package HomePrep Server for Home Assistant OS/Supervised.
- Provide simple installation and onboarding.
- Integrate persistent storage correctly with Home Assistant.
- Support Home Assistant backup workflows where applicable.
- Add HomePrep-native backup and restore independent of Home Assistant backups.

## Phase 6 — Backup and resilience

- Scheduled local backups.
- Configurable retention.
- Manual export/download.
- Tested restore workflows.
- Optional external backup targets where practical.
- Backup integrity checks and clear recovery status.

## Phase 7 — Web application

- Expand HomePrep Web from diagnostics/admin UI into a complete client.
- Responsive inventory and maintenance workflows.
- Household overview and readiness views.
- Plans, targets, tasks and shopping workflows.
- Client/device management.
- Backup/restore controls.

## Phase 8 — Android readiness

- Stabilize the public client API used by HomePrep Android.
- Add secure pairing tokens/QR-based onboarding.
- Support local-network and user-provided remote endpoints.
- Document server requirements for mobile access.
- Add notification/event interfaces where appropriate.

## Deployment targets

Priority order:

1. Docker / Docker Compose
2. Home Assistant App/Add-on
3. General standalone Docker deployment on NAS/home servers

Additional packaging can follow based on real demand.

## Storage direction

SQLite is the initial database target because HomePrep Server primarily serves one household and should be easy to operate and back up. Additional database backends may be considered later if real use cases require them.

## Not a goal for the initial server

The first releases are not intended to become a general-purpose storage, messaging or social platform. The server should remain focused on HomePrep data and workflows.

## Related projects

- [`kakelakel/homeprep`](https://github.com/kakelakel/homeprep) — Home Assistant integration
- [`kakelakel/homeprep-android`](https://github.com/kakelakel/homeprep-android) — Android client
