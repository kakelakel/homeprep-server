# HomePrep Server Deployment

HomePrep Server is designed to run on infrastructure controlled by the user.

The deployment model should remain consistent across Home Assistant and general self-hosting: one server product, one API and one data model.

## Supported deployment direction

Priority order:

1. Docker / Docker Compose
2. Home Assistant App/Add-on
3. General standalone Docker deployment on NAS/home-server platforms

The first implementation target is Docker because it gives the project a portable reference runtime that can later be wrapped by Home Assistant packaging.

## Reference Docker deployment

The reference deployment should require only:

- a container runtime
- one persistent data volume
- a configured listen port

Conceptually:

```text
Host
└── HomePrep Server container
    ├── API
    ├── Web UI
    └── /data
        ├── homeprep.db
        ├── backups/
        ├── media/
        └── config/
```

A simple Compose deployment should be sufficient for a normal household installation.

## Home Assistant App/Add-on

HomePrep Server should later be packaged as a Home Assistant App/Add-on so HAOS/Supervised users can install their own shared HomePrep server without maintaining Docker manually.

The Add-on should run the same HomePrep Server application used by standalone deployments rather than a separate HA-specific backend.

Expected properties:

- persistent Add-on storage
- simple onboarding
- Home Assistant ingress for the Web UI where appropriate
- optional direct/network access for external clients where explicitly configured
- participation in Home Assistant backup where supported
- HomePrep-native backup/restore remains available independently

Installing HomePrep Server in Home Assistant must not automatically switch the existing HomePrep integration away from local storage.

## Standalone server/NAS

The same container should work on systems such as:

- Linux servers
- mini PCs
- home labs
- NAS platforms with Docker/container support
- user-controlled VPS deployments

Platform-specific community packaging can be added later without changing the core server architecture.

## Networking

Local-network operation is a fully supported deployment mode.

HomePrep Server does not need to be Internet-accessible to function.

For remote access, the initial project direction is to let the server owner provide secure connectivity, for example:

- VPN
- Tailscale or similar private overlay network
- authenticated HTTPS reverse proxy

HomePrep should not encourage exposing an unauthenticated plain-HTTP service directly to the public Internet.

## HTTPS

The server may initially listen as HTTP inside a trusted local/container network while TLS termination is handled by the user's reverse proxy or secure overlay.

Native TLS support can be considered later if it materially improves safe deployment, but it should not duplicate mature reverse-proxy tooling without need.

## Persistent storage

All state required to restore a normal HomePrep Server should be kept under documented persistent storage paths.

The application container itself should be replaceable/upgradable without losing household data.

The initial persistent root is conceptually `/data`.

## Configuration

Configuration should be explicit and portable.

Secrets must not be baked into container images or committed configuration files.

The bootstrap implementation should prefer a small number of documented environment/configuration values rather than a large configuration surface.

## Updates and migrations

Server upgrades may include database migrations.

The intended update flow is:

```text
backup/checkpoint
      ↓
start new Server version
      ↓
run required schema migrations
      ↓
health/readiness checks
      ↓
serve clients
```

Migration failures must stop the server from pretending it is healthy.

## Health checks

Container deployments should expose separate concepts for:

- process/liveness — `/healthz`
- application/database readiness — `/readyz`

This makes Docker, Home Assistant and future orchestration integrations easier to reason about.

## No hidden central dependency

A valid deployment must continue working when it cannot reach HomePrep-operated infrastructure.

Core runtime, database, Web UI, API and backup features must not require a HomePrep cloud account or hosted control plane.
