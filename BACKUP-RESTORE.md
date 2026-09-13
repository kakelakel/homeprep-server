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

## Initial backup scope

The initial structured-data Server should back up everything required to recreate the household's HomePrep state.

Conceptually this includes:

```text
homeprep.db
configuration metadata required for restore
backup manifest
media/        # when Server media support is introduced
```

Secrets/credentials require careful handling and may have separate export/recovery rules rather than being blindly copied into portable archives.

## SQLite backups

The Server must not assume that copying a live SQLite database file is always a safe backup procedure.

HomePrep should use a SQLite-supported consistent snapshot/backup mechanism or an equivalent controlled transaction/checkpoint process.

Backups should be created by HomePrep itself while the database is in a known consistent state.

## Backup manifest

A portable HomePrep backup should include a small manifest containing information such as:

- HomePrep Server version
- database schema/migration version
- backup format version
- server instance identifier where useful
- household identifier
- backup timestamp
- included components

The manifest must not contain credentials unnecessarily.

## Retention

Scheduled backup retention should eventually be configurable.

A reasonable simple model may support daily/weekly/monthly retention without forcing users to manage raw backup files manually.

Exact defaults should be selected after the backup format is implemented and tested.

## Restore behavior

Restore must be an explicit administrative action.

The restore flow should:

1. validate the backup package/manifest
2. verify compatibility
3. preserve or checkpoint the current state before destructive replacement where practical
4. restore the database and supported files
5. run required forward migrations if the backup schema is older
6. validate database integrity
7. start normal service only when the restored state is ready

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
restore + compatibility migration
```

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

Automated tests should eventually prove:

```text
create known data
      ↓
backup
      ↓
restore into clean test instance
      ↓
validate records, relationships and revisions
```

Restore testing is part of the feature, not an optional operational exercise.
