# HomePrep Server Data Model

HomePrep Server stores structured household-preparedness data. It is not intended to be a general-purpose document or file database.

The first implementation should preserve the concepts already proven in HomePrep for Home Assistant while moving them behind a server-owned API and persistence layer.

## Common metadata

Synchronizable HomePrep objects should use a shared metadata model where practical:

- `id` — stable UUID
- `household_id` — stable household UUID
- `created_at` — server timestamp
- `updated_at` — server timestamp
- `revision` — monotonically increasing object revision
- `schema_version` — object/schema compatibility marker
- `deleted_at` — nullable deletion/tombstone timestamp

These fields exist so data can later move safely between Home Assistant, Web, Android and Server without inventing platform-specific identities.

## Household

The Household is the ownership/scope boundary for preparedness data.

The initial server may operate as a single-household installation, but records should remain household-scoped so the domain model does not need to be rewritten later.

Expected household data includes only what HomePrep actually needs, for example:

- stable household ID
- optional display name
- locale/country settings where relevant to guidance
- preparedness planning settings
- created/updated metadata

HomePrep should avoid collecting unrelated personal-profile information simply because a database is available.

## Inventory — first implementation domain

Inventory represents stored supplies and movable preparedness equipment.

The first Server implementation should support the core fields already used by HomePrep, including:

- stable metadata
- name
- category
- item type
- quantity
- unit
- expiry date
- last check date
- next check date
- notes
- optional Container relationship when Containers are introduced

Image/media fields may be added later. Media is not required to prove the first structured-data Server path.

## Containers

Containers represent where supplies are stored or what belongs together, for example bags, crates, cabinets, vehicle storage and water-storage containers.

Expected relationships:

```text
Household
  └── Containers
        └── Inventory items
```

Deleting a Container must not imply deleting the Inventory stored in it. The relationship should be cleared or reassigned according to domain rules.

## Assets

Assets represent important fixed or semi-permanent preparedness points in the household, such as:

- water shutoffs
- valves
- drains
- leak sensors
- pumps
- smoke alarms
- extinguishers
- electrical panels
- generators

Assets may contain operational instructions and recurring check information but are distinct from consumable Inventory.

## Tasks

Tasks represent preparedness work and recurring checks.

Linked recurring Tasks remain the scheduling authority for Inventory, Container and Asset inspections. Resource-level next-check fields are projections/convenience values synchronized from the linked Task schedule rather than competing scheduling systems.

## Plans

Plans represent emergency procedures and scenario checklists.

Plan checklist items may link to real HomePrep resources such as Inventory, Containers and Assets. Those links should use stable IDs rather than copying entire resource records into the Plan.

## Targets

Targets describe what a household considers ready, separate from general guidance.

Targets remain editable household data. Public/official guidance may help create Targets, but changing guidance must not silently rewrite a household's personal Targets.

## Shopping List

Shopping entries represent replenishment/replacement needs.

Entries may be manual or generated from known HomePrep conditions such as expired Inventory. Automatic entries should retain source identity so duplicate replacement entries can be avoided.

## Guidance

Guidance is conceptually different from private household state.

Country-specific/general recommendation definitions may remain application/reference data rather than database records unless a later use case justifies server persistence.

## Relationships and deletion

Relationships should use stable object IDs and explicit foreign-key/domain rules.

Deletion behavior must be defined per domain. For synchronizable data, the normal approach is a tombstone rather than immediately losing all evidence that an object existed.

Tombstone retention and long-offline-client recovery will be defined as synchronization work matures.

## Revisions

The Server owns resource revisions.

A successful mutation increments the resource revision within the same transaction as the data change. Clients should never invent a higher server revision themselves.

This makes revision-based optimistic concurrency and later incremental synchronization predictable.

## Database implementation

The initial persistence implementation is SQLite through SQLAlchemy, with Alembic managing schema migrations.

The domain and API contracts should not expose SQLAlchemy-specific implementation details. A clean repository/service boundary allows persistence details to evolve without redefining HomePrep itself.
