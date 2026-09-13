# HomePrep Data Ownership

## Your preparedness. Your server. Your data.

HomePrep treats control of preparedness data as a core architectural requirement, not as a temporary feature or marketing preference.

Preparedness data may describe a household's supplies, equipment, storage locations, maintenance status, emergency plans and weaknesses. HomePrep is therefore designed so that the household can retain control of the infrastructure that stores this information.

## Permanent project commitment

HomePrep's core household-preparedness functionality will **not require centralized HomePrep-operated storage**.

Self-hosted and local operation is a permanent project commitment. Future features, commercial services or optional hosted offerings must not remove the user's ability to operate HomePrep using infrastructure they control.

A future optional managed service may exist, but it must remain optional. It must not become the only supported storage path for core HomePrep data.

## What this means for HomePrep Server

- The user chooses where HomePrep Server runs.
- The user controls the database and persistent storage.
- No HomePrep account is required for a self-hosted household.
- Local-network-only operation is supported.
- Remote access is controlled by the server owner.
- Backups and exports must remain usable without a HomePrep-operated service.
- Open, documented data and API contracts should prevent intentional lock-in.
- Clients must make the connected server visible rather than hiding where data is stored.
- Telemetry must not be required for core operation.

## Data portability

HomePrep Server should provide practical backup, restore and export mechanisms. A household should be able to move its HomePrep installation to another machine without losing ownership of its preparedness history.

Where practical, stored data formats and schemas should be documented well enough for technically capable users to inspect and recover their own data.

## Optional services

HomePrep may eventually provide optional services that make setup, remote connectivity or hosting easier. Such services must be opt-in and must not weaken the self-hosted path.

The architectural rule is simple:

> Convenience may be centralized. Ownership must not be.

## Security responsibility

Self-hosting gives users control, but it also means deployment security matters. HomePrep Server will aim to provide secure defaults, documented upgrade paths, authentication, backup guidance and safe deployment patterns. Users remain responsible for securing the infrastructure and remote access they operate.

## Scope

This commitment applies to core private household preparedness data. Public community features or other future online services, if ever introduced, would be separate from the private household data plane and require their own explicit privacy and security model.
