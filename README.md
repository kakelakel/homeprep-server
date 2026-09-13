# HomePrep Server

**Your preparedness. Your server. Your data.**

HomePrep Server is the self-hosted data and API layer for the HomePrep ecosystem. It is designed for people who want HomePrep data to remain under their own control while still being able to use multiple clients such as Home Assistant, a web interface and the HomePrep Android app.

HomePrep Server is currently in the architecture/bootstrap phase and is not yet ready for production use.

## Why HomePrep Server exists

Preparedness data can reveal a great deal about a household: what supplies exist, where important equipment is located, which plans are prepared and where gaps remain. HomePrep therefore treats user control of data as a product principle rather than an optional privacy feature.

The server is intended to provide a common self-hosted source of truth without requiring a central HomePrep account or a HomePrep-operated cloud database.

## Planned clients

HomePrep Server is intended to support:

- **HomePrep for Home Assistant** — the existing Home Assistant integration, with an optional Server mode in addition to local-only operation.
- **HomePrep Web** — a browser interface served by HomePrep Server.
- **HomePrep Android** — a mobile client that connects to the user's own HomePrep Server.

Home Assistant will remain usable without HomePrep Server. The server is an optional expansion path, not a requirement for the existing integration.

## Deployment goals

The first deployment targets are:

1. **Docker / Docker Compose** — the reference deployment for development and self-hosting.
2. **Home Assistant App/Add-on** — a packaged deployment for Home Assistant OS/Supervised users.
3. **Standalone self-hosting** — the same server stack on a NAS, mini PC, home server or VPS controlled by the user.

The initial storage target is SQLite for a simple single-household deployment. The architecture should leave room for additional database backends later if there is a real need.

## Planned server responsibilities

HomePrep Server will progressively provide:

- a versioned API for HomePrep clients
- household-scoped HomePrep data storage
- authentication and client/device pairing
- synchronization metadata and conflict handling
- a web interface
- backup and restore
- media storage where explicitly supported
- import/migration from existing HomePrep Home Assistant data

## Data ownership principles

HomePrep Server is being designed around these principles:

- self-hosted by default
- no HomePrep cloud account required
- no central HomePrep database required
- local network use supported
- remote access controlled by the server owner
- structured HomePrep data rather than general-purpose file storage
- data portability and backup built into the product
- clients should be replaceable without trapping the household's data

## Planned operating modes

HomePrep is intended to support three broad modes over time:

### Home Assistant only
The existing HomePrep integration keeps its local Home Assistant storage and works without HomePrep Server.

### Home Assistant + HomePrep Server
Home Assistant becomes one client of the household's self-hosted HomePrep Server. This enables additional clients while preserving Home Assistant integration, Lovelace cards and Home Assistant notifications.

### HomePrep Server without Home Assistant
A household can run HomePrep Server together with HomePrep Web and HomePrep Android without requiring Home Assistant.

## Relationship to other repositories

- [`kakelakel/homeprep`](https://github.com/kakelakel/homeprep) — Home Assistant integration
- [`kakelakel/homeprep-server`](https://github.com/kakelakel/homeprep-server) — self-hosted server, API and web application
- [`kakelakel/homeprep-android`](https://github.com/kakelakel/homeprep-android) — Android client

Each repository has its own roadmap and release lifecycle while sharing common HomePrep concepts and data contracts.

## Current status

The current phase is **foundation and architecture**. The first milestone is to establish a stable server contract, development environment and minimal end-to-end path before expanding functionality.

See [ROADMAP.md](ROADMAP.md) for the current plan and [CHANGELOG.md](CHANGELOG.md) for project updates.

## License

HomePrep Server is released under the license included in this repository. See [LICENSE](LICENSE).
