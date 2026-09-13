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

### Changed
- README and roadmap now treat user-controlled infrastructure, local-network operation, portability, backup and no mandatory telemetry as architectural constraints rather than optional privacy features.

### Planned next
- Architecture and API contract documentation.
- Security/deployment baseline.
- Initial Docker development environment.
- SQLite-backed server skeleton.
- Minimal Web/diagnostics interface.
