# HomePrep Server Backup and Restore

Backup and restore are part of HomePrep's data-ownership model.

A self-hosted system is only meaningfully user-owned if the household can recover it, move it and verify that its backups are usable.

## Goals

HomePrep Server provides or is designed to provide:

- manual backup
- scheduled backup
- configurable retention
- integrity validation
- explicit restore
- portability between compatible HomePrep Server installations
- backup operation independent of HomePrep-operated services
- a versioned portable migration/export package
- platform-neutral behavior across Windows, Docker, Home Assistant App/Add-on and other compatible Server deployments

Backup creation, validation, restore primitives and scheduling belong to **HomePrep Server core**, not to a Windows-only implementation. Platform management surfaces such as **HomePrep Server Manager** configure and invoke the shared subsystem.

## Current implementation

The initial native backup/restore proof is implemented for SQLite Server installations.

A backup is a ZIP archive named approximately:

```text
homeprep-backup-YYYYMMDDTHHMMSSZ.zip
```

The archive currently contains:

```text
manifest.json
homeprep.db
```

The database snapshot is created through SQLite's supported backup API rather than by blindly copying a live database file.

Current backup format version:

```text
1
```

The current manifest records:

- backup format version
- product identity
- HomePrep Server version
- Server instance ID
- UTC backup timestamp
- database engine
- Alembic migration version where available
- active Household ID/name where configured
- included components

The first implementation intentionally keeps the package simple while establishing stable validation and portability semantics before additional domains/media are added.

## Current backup administration

The Server exposes owner-only API operations:

```text
GET  /api/v1/backups
POST /api/v1/backups
```

Windows Server Manager currently exposes:

- **Back up now**
- latest local backup display
- **Open backup folder**
- schedule: `Off`, `Daily`, `Weekly`
- retention as number of normal backup archives to keep
- **Restore backup…** with package validation and explicit confirmation

The schedule runs in the HomePrep Server process using the same core backup code rather than Windows Task Scheduler. This is deliberate groundwork for equivalent behavior in Docker and the future Home Assistant App/Add-on.

## Backup validation

Before restore, HomePrep validates the archive rather than trusting a ZIP by filename.

Current validation checks include:

1. archive can be opened
2. required `manifest.json` and `homeprep.db` components exist
3. the product marker identifies a HomePrep Server backup
4. the backup format version is supported
5. the database engine is supported
6. the extracted SQLite snapshot passes `PRAGMA integrity_check`

Validation returns structured metadata including source Server version, backup timestamp, Household identity/name and migration version where available.

Future versions may add checksums/signatures and deeper relationship/schema validation as the portable format expands.

## Restore behavior

Restore is an explicit administrative action.

The implemented SQLite restore primitive:

1. validates the archive
2. locates the configured SQLite database
3. creates a **pre-restore safety backup** when current data exists
4. extracts the candidate database to temporary storage
5. resets active SQLAlchemy database state
6. stages the candidate as a replacement file
7. replaces the configured database only after validation/staging
8. resets database state again

The standalone launcher exposes offline administrative commands:

```text
HomePrepServer.exe --validate-backup <path>
HomePrepServer.exe --restore-backup <path>
```

Windows Server Manager wraps this in a safer UI flow:

```text
select backup
    ↓
validate
    ↓
show source metadata + confirm
    ↓
stop Windows Service if running
    ↓
restore with pre-restore safety backup
    ↓
restart service if it was previously running
    ↓
normal startup applies forward Alembic migrations
```

The Manager attempts to restart the Windows Service even if the restore command fails after the service has been stopped, so an operational failure does not intentionally leave the service down.

A failed validation never proceeds to destructive replacement.

## Restore testing

The automated test suite proves more than archive creation.

Current restore regression coverage performs:

```text
create Household + Inventory
      ↓
create backup
      ↓
mutate Inventory after backup
      ↓
restore old backup
      ↓
verify old Inventory state returned
      ↓
open pre-restore safety backup
      ↓
verify it contains the newer pre-restore state
```

The backup test also opens the archive directly, verifies manifest contents, extracts `homeprep.db` and queries the snapshot with SQLite.

Restore testing is part of the feature, not an optional operational exercise.

## Scheduling and retention

The current simple scheduling model supports:

- `off`
- `daily`
- `weekly`

The Server periodically checks whether a backup is due based on the latest recognized archive. After a scheduled backup, it prunes the oldest normal backup archives beyond the configured retention count.

Windows standalone currently stores these values in `config.json`:

```json
{
  "backup_schedule": "daily",
  "backup_retention": 14
}
```

Retention applies only to normal `homeprep-backup-*.zip` archives. Pre-restore safety backups are stored separately so routine retention does not silently remove the immediate rollback checkpoint for a restore operation.

A future scheduler pass should add durable last-run/failure diagnostics rather than merely preventing scheduler failures from crashing the Server.

## Portable migration format

The same backup package is intended to become the normal Server-to-Server portability path.

A user should be able to move a compatible HomePrep installation without contacting HomePrep or obtaining a cloud migration token:

```text
Old HomePrep Server
       ↓
portable backup/export
       ↓
New HomePrep Server
       ↓
validate → restore/import → forward migrate → integrity check
```

Target compatibility examples:

```text
Windows → Docker
Docker → Home Assistant App/Add-on
Home Assistant App/Add-on → Windows
Old machine → replacement machine
```

As Server domains expand, the portable package must preserve where applicable:

- Household identity
- stable object IDs
- relationships between objects
- created/updated timestamps
- revisions
- schema versions
- tombstones/deletion metadata
- supported local media
- Inventory, Containers, Assets, Tasks, Plans, Targets and Shopping data

The format must not redefine the domain model per platform.

## Credentials and secrets

The current SQLite snapshot necessarily contains the Server's stored authentication records, but HomePrep stores session/client tokens as hashes rather than plaintext credentials.

Portable migration policy for credentials must remain deliberate. Domain-data portability and installation-local security state are different concerns; future export modes may choose to invalidate or exclude selected authentication state when moving to another machine.

Do not claim that every credential is portable merely because its hashed database record exists in a snapshot.

## Updates and pre-upgrade safety

Standalone update handling and backup should cooperate.

Windows Server Manager now includes **Check for updates**, using the latest published GitHub Release as the stable release channel. This first version compares installed/latest versions and can open the release page; it does not silently download or execute an installer.

Before enabling a one-click or unattended update path, HomePrep should prove:

- trustworthy/signed release assets
- package authenticity verification
- pre-upgrade verified backup/checkpoint
- preservation of persistent data/configuration
- schema migration failure handling
- safe service restart
- recovery/rollback behavior

Automatic updates should be opt-in only after those properties are real, not aspirational.

## Home Assistant backups

A future Home Assistant App/Add-on deployment should participate in Home Assistant's backup system where supported.

That integration is useful, but it does not replace HomePrep-native backup and restore. Users running HomePrep Server outside Home Assistant must receive equivalent recovery capability.

## External backup destinations

The first implementation stores backups locally under the persistent data directory.

Later optional destinations may include user-controlled storage such as:

- NAS/SMB
- WebDAV
- S3-compatible object storage

External targets should be added only when local backup/restore is robust and the external credential/storage behavior can be implemented securely and predictably.

## Encryption

Backup encryption is an important future design decision, especially for copies stored outside the user's primary server.

The current implementation does **not** claim application-level encrypted backups. Users may initially rely on encryption provided by their destination/storage infrastructure.

Do not describe backups as encrypted unless HomePrep itself actually provides and verifies that encryption.
