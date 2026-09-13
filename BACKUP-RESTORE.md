# HomePrep Server Backup and Restore

Backup and restore are part of HomePrep's data-ownership model.

A self-hosted system is only meaningfully user-owned if the household can recover it, move it and verify that its backups are usable.

## Goals

HomePrep Server should provide:

- manual backup
- scheduled backup
- configurable retention
- integrity validation
- documented restore
- portability between compatible HomePrep Server installations
- backup operation independent of HomePrep-operated services
- a versioned portable migration/export package
- platform-neutral behavior across Windows, Docker, Home Assistant App/Add-on and other compatible Server deployments

Backup scheduling and archive creation belong to **HomePrep Server core**, not to a Windows-only implementation. Platform management surfaces such as **HomePrep Server Manager** should configure and invoke the same Server backup subsystem.

## Windows Server Manager

The Windows standalone Manager is expected to become the primary local administration surface for backup/recovery on that platform.

Planned Manager capabilities include:

- **Back up now**
- backup destination/status display
- scheduled backup enable/disable
- backup frequency/cadence
- retention configuration
- recent backup history and failure state
- explicit restore/import flow
- open backup folder

The Manager should not implement its own independent database-copy logic. It should call shared Server backup APIs/services so the same backup format and validation rules apply everywhere.

## Initial backup scope

The initial structured-data Server should back up everything required to recreate the household's HomePrep state.

Conceptually this includes:

```text
manifest.json
structured-data snapshot
configuration metadata required for restore
media/        # when Server media support is introduced
```

The internal backup implementation may use a consistent SQLite snapshot, but the **portable format must not be defined merely as "copy this Windows SQLite file"**. The package needs a documented/versioned manifest and clear compatibility semantics.

Secrets/credentials require careful handling and may have separate export/recovery rules rather than being blindly copied into portable archives.

## SQLite backups

The Server must not assume that copying a live SQLite database file is always a safe backup procedure.

HomePrep should use a SQLite-supported consistent snapshot/backup mechanism or an equivalent controlled transaction/checkpoint process.

Backups should be created by HomePrep itself while the database is in a known consistent state.

## Backup / migration manifest

A portable HomePrep backup should include a small manifest containing information such as:

- backup format version
- HomePrep Server version
- API/data schema compatibility version
- database schema/migration version
- server instance identifier where useful
- household identifier
- backup timestamp
- included components
- checksum/integrity information where practical

The manifest must not contain credentials unnecessarily.

The format must be forward-migratable. A newer compatible Server should be able to inspect an older package, determine whether it can restore/import it, perform required forward migrations and report the result clearly.

## Portable migration format

HomePrep needs a sane path for moving all household data between installations and deployment types.

The portable package should preserve, where applicable:

- Household identity
- stable object IDs
- relationships between objects
- created/updated timestamps
- revisions
- schema versions
- tombstones/deletion metadata
- supported local media
- domain data from Inventory, Containers, Assets, Tasks, Plans, Targets and Shopping as those Server domains are implemented

The format must deliberately distinguish **household/domain data** from **installation-local secrets and credentials**. Device tokens, Web sessions and other secrets should not be blindly transplanted to another machine merely because domain data is moved.

A future HA → Server import may use a normalized interchange representation closely related to this portable format, but the importer must explicitly validate source schema/version and report what was imported, transformed, skipped or rejected.

## Retention

Scheduled backup retention should be configurable.

A reasonable simple model may support daily/weekly/monthly retention without forcing users to manage raw backup files manually.

Exact defaults should be selected after the backup format is implemented and tested.

Retention policy should be implemented in Server core so all deployment types behave consistently.

## Restore behavior

Restore must be an explicit administrative action.

The restore flow should:

1. validate the backup package/manifest
2. verify format/schema compatibility
3. verify package integrity
4. preserve or checkpoint the current state before destructive replacement where practical
5. restore/import structured data and supported files
6. run required forward migrations if the source schema is older
7. validate database integrity and key object relationships
8. start normal service only when the restored state is ready
9. provide a clear restore report

A failed restore must not silently leave the server reporting a healthy state with partially restored data.

## Moving to another server

A user should be able to move a HomePrep installation to new infrastructure without contacting HomePrep or obtaining a cloud migration token.

The intended portability story is:

```text
Old HomePrep Server
       ↓
portable backup/export
       ↓
New HomePrep Server
       ↓
validate → restore/import → migrate → integrity check
```

This must work between compatible deployment types, for example:

```text
Windows → Docker
Docker → Home Assistant App/Add-on
Home Assistant App/Add-on → Windows
Old machine → replacement machine
```

without redefining the household data model per platform.

## Updates and pre-upgrade safety

Standalone update handling and backup should cooperate.

Before an update that includes data/schema migrations which could make downgrade difficult, HomePrep should create or require a recent verified backup/checkpoint. An unattended update path must not be enabled until package authenticity, data preservation and failure recovery are proven.

The Windows Server Manager should eventually provide **Check for updates** and a safe installer/update handoff, while Server core remains responsible for migration and data integrity behavior.

## Home Assistant backups

A future Home Assistant App/Add-on deployment should participate in Home Assistant's backup system where supported.

That integration is useful, but it does not replace HomePrep-native backup and restore.

Users running HomePrep Server outside Home Assistant must receive equivalent recovery capability.

## External backup destinations

The first release can store backups locally under the persistent data directory.

Later optional destinations may include user-controlled storage such as:

- NAS/SMB
- WebDAV
- S3-compatible object storage

External targets should be added only when they can be implemented securely and predictably.

## Encryption

Backup encryption is an important future design decision, especially for copies stored outside the user's primary server.

The initial implementation must not claim encrypted backups unless HomePrep itself actually provides and verifies that encryption. Users may initially rely on encryption provided by their destination/storage infrastructure.

## Testing

A backup feature is not complete merely because archives can be created.

Automated tests should prove at minimum:

```text
create known data
      ↓
backup/export
      ↓
restore/import into clean compatible instance
      ↓
validate records, relationships, revisions and tombstones
```

Cross-version tests should also prove that supported older backup-format/schema versions can be migrated forward.

Restore testing is part of the feature, not an optional operational exercise.
