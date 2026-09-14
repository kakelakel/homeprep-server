# HomePrep Server API Contract

This document defines the initial public API direction for HomePrep Server.

The contract is intentionally conservative: HomePrep clients should be able to identify the server and their authenticated context, understand which API version they are using, and avoid silently overwriting newer data.

## Protocol

The initial client API uses HTTP/HTTPS, JSON, UTF-8, REST-style resources and FastAPI-generated OpenAPI under:

```text
/api/v1/
```

API version and stored object `schema_version` are separate concepts.

## Time and identifiers

- Object IDs use UUIDs.
- Timestamps are serialized as ISO 8601/RFC 3339 values.
- Stored server timestamps are UTC.
- Date-only preparedness fields remain date values.

## Common resource metadata

Synchronizable HomePrep resources should converge on common metadata such as stable IDs, `household_id`, created/updated timestamps, integer `revision`, `schema_version` and `deleted_at` tombstone state.

The server owns revision increments and authoritative server timestamps.

## Optimistic concurrency

Writes should not silently overwrite newer resources. Update/delete requests include the revision the client believes it is modifying; stale revisions return `409 Conflict`. HomePrep Web uses this behavior for Inventory editing and deletion.

## Deletion

Synchronizable HomePrep objects should use tombstones/soft deletion where required by the sync model. Normal APIs hide deleted objects unless a sync-oriented endpoint explicitly requests deletion state.

## System and client-context endpoints

```text
GET /healthz
GET /readyz
GET /api/v1/system/info
GET /api/v1/context
```

`system/info` exposes non-sensitive product/Server/API identity. `/api/v1/context` is an authenticated post-pairing sanity check containing Server identity/version, principal identity and the active Household when configured.

## Current domain endpoints

The first implemented domain slice is Household + Inventory. The MVP Server enforces one active Household per installation.

```text
GET    /api/v1/households
POST   /api/v1/households
GET    /api/v1/households/{id}
GET    /api/v1/inventory?household_id={id}
POST   /api/v1/inventory
GET    /api/v1/inventory/{id}
PATCH  /api/v1/inventory/{id}
DELETE /api/v1/inventory/{id}?expected_revision={revision}
```

Household provisioning is an owner administration operation. After provisioning, authenticated users and paired clients may read the Household according to their normal access path.

## Error responses

API errors use a stable JSON envelope:

```json
{
  "error": {
    "code": "conflict",
    "message": "Revision mismatch: expected 2, current 3"
  }
}
```

Validation errors include structured details. Common codes include `bad_request`, `authentication_required`, `forbidden`, `not_found`, `conflict`, `validation_error` and `request_error`. Feature-specific codes include `write_access_required`, `owner_required`, `last_owner_required`, `username_exists` and `invalid_pairing_token`.

## Authentication: humans and integrations are separate

HomePrep Server deliberately separates **human accounts** from **machine/integration credentials**.

Human accounts are intended for HomePrep Web and future Android sign-in. Machine credentials are intended for trusted integrations such as Home Assistant. A Home Assistant installation is not modeled as a household user and does not receive an `owner`/`editor`/`viewer` human role.

### Human Web/Android roles

Current human roles are:

- `owner` — full household data access plus security/administration
- `editor` — may read and modify normal preparedness/domain data, but not administer security/server access
- `viewer` — read-only access to preparedness/domain data

Owner-only administration currently includes:

- user and role management
- client credential administration
- creation of pairing requests
- native backup administration
- initial Household provisioning

The Server protects against removing the last active owner.

User administration endpoints are:

```text
GET   /api/v1/users
POST  /api/v1/users
PATCH /api/v1/users/{id}
```

Owners can create users, change roles, reset passwords and disable/re-enable accounts. Disabling an account or resetting its password revokes its existing Web sessions.

Human Web authentication uses local accounts, Argon2 password hashing, opaque server-side sessions, HttpOnly SameSite cookies and logout/session revocation.

### Home Assistant and other machine credentials

Machine/integration clients use separate bearer credentials:

```text
GET  /api/v1/clients
POST /api/v1/clients
POST /api/v1/clients/{id}/revoke
```

Client administration is owner-only. A newly created credential receives its plaintext token once; only a SHA-256 hash is stored server-side. Revoked credentials are rejected.

Current machine access profiles remain deliberately simple:

- `full_access` — may read/write protected domain resources
- `read_only` — may read protected domain resources but writes return `403 write_access_required`

These machine profiles are not the human RBAC roles. In particular, Home Assistant can use a revocable `full_access` integration credential without being an `owner` user.

## Pairing

The first pairing flow is:

```text
Owner Web session
      ↓
POST /api/v1/pairing
      ↓
short-lived single-use pairing token
      ↓
client POST /api/v1/pairing/exchange
      ↓
permanent revocable client credential
      ↓
GET /api/v1/context
```

Pairing requests expire after 10 minutes. Pairing tokens are stored as hashes and are single-use. Pairing creation is owner-only; exchange is intentionally unauthenticated because possession of the short-lived token is the bootstrap credential.

The contract is designed first for the Home Assistant config flow. Future Android user authentication should use human accounts/roles; device onboarding may reuse appropriate pairing primitives without conflating device identity with user authority.

## Backup administration API

```text
GET  /api/v1/backups
POST /api/v1/backups
```

Backup administration is owner-only. Machine credentials do not receive backup administration rights merely because they can write household data.

The portable backup format and offline restore behavior are documented in `BACKUP-RESTORE.md`.

## Compatibility

During early `0.x` development, the API may evolve. Changes should remain deliberate and documented. The Server exposes version information so incompatible clients can fail clearly rather than silently corrupting data.

## OpenAPI

Generated OpenAPI is intended to become the machine-readable source for Web, Android, future Home Assistant Server-mode integration tests and compatibility validation.
