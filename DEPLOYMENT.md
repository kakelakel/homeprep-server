# HomePrep Server Deployment

HomePrep Server is designed to run on infrastructure controlled by the user.

The deployment model should remain consistent across Home Assistant and general self-hosting: one server product, one API and one data model.

## Supported deployment direction

Priority order:

1. Docker / Docker Compose
2. Native Windows installer
3. Home Assistant App/Add-on
4. General standalone deployment on NAS/home-server platforms

Docker remains the portable reference runtime. The native Windows package exists to make self-hosting approachable for users who should not need to understand Python, Node, Git, virtual environments or Docker.

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

## Native Windows

The intended Windows user experience is:

```text
HomePrep-Setup.exe
      ↓
Install
      ↓
HomePrep Server starts
      ↓
Browser opens
      ↓
Create local administrator
      ↓
HomePrep
```

The packaged application contains the Python runtime dependencies, API, Web UI and database migrations. End users should not need Python, Node, npm, Git or Docker.

Preparedness data is stored separately from the application binaries under `%ProgramData%\HomePrep` so an application reinstall/uninstall does not implicitly delete household data.

The first Windows package binds to `127.0.0.1` by default. LAN exposure must be an explicit later configuration choice rather than an accidental side effect of installation.

The initial installer starts HomePrep after setup and registers it to start when Windows users sign in. A true Windows service is a planned hardening step before declaring the native installer production-ready.

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

The same server codebase should work on systems such as:

- Windows PCs/home servers through the native package
- Linux servers
- mini PCs
- home labs
- NAS platforms with Docker/container support
- user-controlled VPS deployments

Platform-specific community packaging can be added later without changing the core server architecture.

## Networking

Local-network operation is a fully supported deployment mode, but network exposure must be explicit and authenticated.

HomePrep Server does not need to be Internet-accessible to function.

For remote access, the initial project direction is to let the server owner provide secure connectivity, for example:

- VPN
- Tailscale or similar private overlay network
- authenticated HTTPS reverse proxy

HomePrep should not encourage exposing a plain-HTTP service directly to the public Internet.

## HTTPS

The server may initially listen as HTTP inside a trusted local/container network while TLS termination is handled by the user's reverse proxy or secure overlay.

Native TLS support can be considered later if it materially improves safe deployment, but it should not duplicate mature reverse-proxy tooling without need.

Local username/password authentication protects application access, but plain HTTP does not encrypt credentials or data in transit. Any deployment made reachable beyond localhost should therefore use an appropriate trusted-network or HTTPS design.

## Persistent storage

All state required to restore a normal HomePrep Server should be kept under documented persistent storage paths.

The application container or executable itself should be replaceable/upgradable without losing household data.

Docker and appliance deployments use a persistent `/data` root. Native Windows uses `%ProgramData%\HomePrep` by default.

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
