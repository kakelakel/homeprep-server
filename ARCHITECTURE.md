# HomePrep Server Architecture

HomePrep Server is the optional self-hosted platform layer for HomePrep.

Its purpose is to add multi-client, multi-device, Web, backup and synchronization capabilities **without making HomePrep Server mandatory for Home Assistant users**.

> **Server mode adds capabilities. It does not remove autonomy.**

## Permanent operating modes

HomePrep is designed to support three operating modes.

### Mode A — Home Assistant only

The existing `kakelakel/homeprep` integration continues to store and manage HomePrep data locally inside Home Assistant.

No HomePrep Server is required.

### Mode B — Home Assistant + HomePrep Server

Home Assistant becomes one client of a user-owned HomePrep Server.

The Server provides the shared household data/API layer while Home Assistant keeps platform-specific features such as Lovelace, automations and Home Assistant notifications.

### Mode C — HomePrep Server without Home Assistant

HomePrep Server can run independently with HomePrep Web and, later, HomePrep Android.

Home Assistant is therefore a supported HomePrep client, not a mandatory runtime dependency of the broader platform.

## Deployment model

The same HomePrep Server application should be distributable in multiple forms:

1. Docker / Docker Compose reference deployment
2. Home Assistant App/Add-on
3. Standalone Docker deployment on a NAS, mini PC, home server or VPS controlled by the user

The goal is one server product and one data contract rather than separate server implementations for each platform.

## High-level architecture

```text
                 HomePrep Android
                        |
                        | HTTPS / JSON API
                        v
Home Assistant ---> HomePrep Server <--- HomePrep Web
                        |
                        v
                  Repository layer
                        |
                        v
                      SQLite
```

When Home Assistant is used in local-only mode, this path remains valid instead:

```text
Home Assistant
      |
   HomePrep
      |
HA local storage
```

## Initial technology stack

The initial implementation direction is:

- **Python** for the server runtime
- **FastAPI** for the HTTP API and OpenAPI contract
- **Pydantic** for API/schema validation
- **SQLAlchemy 2.x** for persistence mapping and transaction boundaries
- **Alembic** for database migrations
- **SQLite** as the initial database
- **TypeScript + React + Vite** for HomePrep Web
- Docker as the reference packaging format

The Web application should build to static assets that can be served by HomePrep Server in production, while remaining independently runnable during development.

## Application boundaries

The server should maintain explicit boundaries between:

- API/transport
- domain/service logic
- persistence/repositories
- database models/migrations
- authentication/client identity
- Web client
- backup/restore
- synchronization

Business rules should not live directly in HTTP route handlers or SQL queries.

A repository/service boundary is required from the beginning so SQLite remains an implementation detail rather than the definition of the HomePrep domain model.

## Proposed repository structure

```text
homeprep-server/
├── src/
│   └── homeprep_server/
│       ├── api/
│       ├── core/
│       ├── domain/
│       ├── repositories/
│       ├── services/
│       ├── database/
│       └── main.py
├── web/
├── migrations/
├── tests/
├── deploy/
├── docs/
├── Dockerfile
├── compose.yaml
└── pyproject.toml
```

The exact structure may evolve during bootstrap, but the boundaries above should remain clear.

## Storage model

SQLite is the initial server database because the expected workload is normally a single household with modest data volume.

Persistent runtime data should live under one mounted data directory, conceptually:

```text
/data/
├── homeprep.db
├── backups/
├── media/
└── config/
```

Media support is not required for the first Server MVP. The initial end-to-end proof should focus on structured HomePrep data.

## API model

The public application API is JSON over HTTP and versioned independently from database schema versions.

Initial API namespace:

```text
/api/v1/
```

FastAPI's OpenAPI description will act as the machine-readable client contract.

See [API-CONTRACT.md](API-CONTRACT.md).

## Identity and synchronization foundations

HomePrep Server should preserve the synchronization-oriented concepts already introduced in the Home Assistant implementation:

- stable UUID object IDs
- stable household identity
- created/updated timestamps
- integer revision
- schema version
- deletion tombstones

The first Server milestone does not need full offline synchronization, but its data model must not prevent it.

## Source of truth

HomePrep Server becomes the source of truth **only when a user explicitly enables Server mode**.

Existing Home Assistant installations must not silently transfer or migrate their HomePrep data.

A future migration flow should be explicit, validated and recoverable.

## Security boundary

HomePrep Server must work as a local-network-only service.

Remote access is controlled by the server owner. Initial releases should document safe approaches such as VPN or an authenticated HTTPS reverse proxy rather than automatically exposing the service to the Internet.

No HomePrep-operated account, relay or central database is required for core self-hosted operation.

## First vertical slice

The first useful implementation should deliberately stay small:

```text
Docker
  ↓
HomePrep Server
  ↓
health/version/server identity
  ↓
SQLite + migrations
  ↓
Household
  ↓
Inventory API
  ↓
minimal HomePrep Web Inventory UI
```

Only after this path works reliably should the remaining HomePrep domains be added.

## Related documents

- [DATA-OWNERSHIP.md](DATA-OWNERSHIP.md)
- [API-CONTRACT.md](API-CONTRACT.md)
- [DATA-MODEL.md](DATA-MODEL.md)
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [BACKUP-RESTORE.md](BACKUP-RESTORE.md)
- [ROADMAP.md](ROADMAP.md)
