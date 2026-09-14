# HomePrep Server Roadmap

HomePrep Server is the self-hosted backend for the HomePrep ecosystem. This roadmap describes direction and sequencing, not fixed release dates.

## Permanent product principle

**Your preparedness. Your server. Your data.**

Core private household preparedness data will not require centralized HomePrep-operated storage.

Self-hosted operation is a permanent architectural commitment. Future optional managed services may exist, but they must remain optional and must not remove the user's ability to run HomePrep on infrastructure they control.

> **Convenience may be centralized. Ownership must not be.**

## Current execution sequence

The current engineering order is deliberately:

1. complete and validate human access control (`owner` / `editor` / `viewer`) and Windows recovery/update foundations
2. perform a dedicated security and intrusion-resistance hardening pass
3. align HomePrep Web visually with the established HomePrep Home Assistant theme
4. expand Server/Web functionality to cover the mature Home Assistant standalone domains and workflows
5. then complete explicit HA → Server migration, synchronization proofs and Home Assistant App/Add-on packaging against that shared domain model

This sequence avoids rushing synchronization onto an incomplete or weakly hardened Server surface.

Home Assistant remains a trusted paired integration client with its own revocable credential. Human RBAC is for Web and future Android users; HA is not represented as an `owner`/`editor`/`viewer` household user.

## Phase 1 — Foundation

- Define server architecture and repository structure.
- Define shared HomePrep data contract and API versioning.
- Define human authentication, machine pairing and per-client access separately.
- Define backup/restore/migration principles.
- Establish Docker, Windows and future Home Assistant deployment paths.
- Establish CI and security boundaries.
- Keep core operation independent of HomePrep-operated infrastructure.

## Phase 2 — Server MVP and access control

Implemented/under active validation:

- FastAPI runtime and SQLite persistence
- Alembic migrations
- one Household per Server installation
- first Household + Inventory domain slice
- local Web authentication
- human roles: `owner`, `editor`, `viewer`
- owner-managed user lifecycle and roles
- separate revocable machine/integration credentials
- HA-oriented one-time pairing
- revision-safe writes/conflict handling
- minimal bundled Web application
- Docker and native Windows packaging
- native backup/restore/scheduling

Role intent:

- **Owner:** normal data + security/server administration
- **Editor:** normal preparedness data read/write
- **Viewer:** normal preparedness data read-only

Owner-only surfaces include user/role management, client/pairing administration, backup administration and first Household provisioning.

## Phase 3 — Security and intrusion-resistance hardening

Before expanding the Web surface substantially, evaluate and harden the deployment/security model. Planned review areas include:

- login throttling / brute-force resistance
- session lifetime, rotation and revocation policy
- CSRF protection for browser state-changing requests
- secure-cookie/HTTPS deployment behavior
- security headers and browser policy
- trusted proxy / forwarded-header behavior
- LAN versus Internet-exposure warnings and safe defaults
- API request/body limits where appropriate
- audit/security event logging without leaking secrets
- dependency and release-artifact supply-chain checks
- backup/restore/update privilege boundaries
- safe secret/token handling and redaction
- threat modeling for Windows, Docker and future HA App/Add-on deployments

Direct Internet exposure should not be implied safe merely because authentication exists. Initial remote-access guidance remains user-managed VPN/Tailscale or a correctly configured HTTPS reverse proxy.

## Phase 4 — Web visual alignment

Bring HomePrep Web into the established HomePrep visual language from the Home Assistant product while retaining a responsive standalone Web experience.

Goals include:

- shared HomePrep visual hierarchy and terminology
- familiar primary/status/attention/critical semantics
- mobile-first responsive behavior
- consistent cards, navigation and readiness presentation
- accessibility preserved while matching the HA HomePrep identity

This is visual/product alignment, not a requirement that Web mimic Home Assistant itself.

## Phase 5 — Shared HomePrep functionality parity

Use the mature Home Assistant standalone implementation as the domain/workflow reference rather than inventing a second HomePrep product.

Bring shared Server/Web support to:

- Inventory
- Containers
- Household Assets
- Tasks and recurring inspections
- Preparedness Plans
- Targets
- Guidance/profile concepts where they belong in shared data
- Shopping List and replacement workflows
- readiness/attention concepts
- household settings appropriate to shared Server state
- history/maintenance relationships needed by these domains

Preserve established domain rules such as Task scheduling authority, Container deletion semantics, stable IDs, revisions, schema versions and tombstones.

HA-specific Lovelace, notifications, automations and integration UX remain in Home Assistant rather than being cloned into Server.

## Phase 6 — Import and Home Assistant bridge

Once enough of the shared model exists:

- explicit import from existing HomePrep HA storage
- preview/validation before switching modes
- preserve IDs, relationships and valid sync metadata
- clear transformed/skipped/rejected reporting
- preserve Home Assistant-only mode
- rollback/retry path during beta
- optional Server configuration in the HA integration

## Phase 7 — Synchronization

- revision-based synchronization
- tombstone/deletion synchronization
- client checkpoints/cursors
- deterministic conflict handling
- sync diagnostics/client status
- mixed-version compatibility tests
- prove create/update/delete flows in both directions

Do not call synchronization stable until deletion, stale writes, offline/reconnect and upgrade cases are proven.

## Phase 8 — Home Assistant App/Add-on

Package the same HomePrep Server runtime for Home Assistant OS/Supervised:

- simple installation/onboarding
- persistent storage
- clear network model
- HA backup compatibility where useful
- HomePrep-native backup/restore remains available
- no external HomePrep account required

## Phase 9 — Backup, portability and offline resilience

Continue maturing the already implemented native recovery foundation:

- scheduled local backups and retention
- durable backup success/failure history
- tested cross-version and cross-deployment restore
- manual export/download
- optional external targets controlled by the user
- disaster-recovery documentation
- trusted update handoff with pre-upgrade backup

Portable migration should support compatible moves such as Windows ↔ Docker ↔ future HA Add-on without artificial lock-in.

Also provide offline/paper preparedness outputs:

- printable current Inventory/stock
- grouping by Container/storage location
- quantities and expiry/rotation details
- printable Plans/checklists
- optional useful images where they improve identification/action

The purpose is resilience when normal HomePrep/HA/network access is unavailable.

## Phase 10 — Complete Web application

As shared domains land, Web should become a complete standalone HomePrep client with:

- household/readiness overview
- responsive Inventory/Container/Asset maintenance workflows
- Tasks, Plans, Targets and Shopping workflows
- owner user/access administration
- client/device administration
- backup/status administration
- print/export UI
- visible Server identity/storage/connection state

## Phase 11 — Android readiness

- stabilize public user/client API
- local-network and user-provided remote endpoint support
- human login/roles against the same Server authorization model
- secure local credential/session storage
- server identity verification
- offline/cache behavior later
- notifications/events where appropriate
- no mandatory HomePrep relay

Android has its own product roadmap; printable/paper-output work is intentionally not an Android requirement.

## Deployment targets

First-class directions:

1. Docker / Docker Compose
2. native Windows standalone
3. Home Assistant App/Add-on using the same runtime
4. compatible NAS/general self-hosting where practical

## Storage direction

SQLite remains the initial database because HomePrep is primarily a modest single-household workload and should remain simple to operate and recover. Other databases may be considered only if real needs justify them.

## Non-negotiable architecture constraints

- No mandatory HomePrep cloud account for self-hosted operation.
- No mandatory central HomePrep database for core household data.
- No mandatory telemetry for core operation.
- No intentional lock-in preventing practical backup/restore/migration.
- No future Web/mobile client may silently move private household data away from the user's selected Server.
- Optional hosted services must coexist with self-hosting rather than replace it.
- Home Assistant standalone remains a complete valid HomePrep mode.

## Not an initial goal

HomePrep Server is not a general-purpose storage, messaging or social platform. Keep attack surface and product scope centered on HomePrep data/workflows.

## Related projects

- [`kakelakel/homeprep`](https://github.com/kakelakel/homeprep) — Home Assistant integration
- [`kakelakel/homeprep-android`](https://github.com/kakelakel/homeprep-android) — Android client
