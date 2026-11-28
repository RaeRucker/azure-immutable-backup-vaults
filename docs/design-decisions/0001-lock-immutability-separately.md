# Design decision 1: Deploy vaults unlocked and lock them as a separate step

Status: in use

## The problem

An immutable vault stops anyone from deleting recovery points before they expire. That protects backups from ransomware and from an admin account that's been taken over.

Once immutability is locked, it can't be turned off and retention can't be shortened for as long as the vault exists. A retention mistake made before the lock becomes a cost you pay for years.

## What I chose

The Bicep deploys each vault with immutability turned on but not locked, and soft delete set to always on.

Locking is done later by [`scripts/Lock-VaultImmutability.ps1`](../../scripts/Lock-VaultImmutability.ps1). The script needs the reference of a passed restore test. It checks that the vault is geo-redundant and has protected VMs, asks you to confirm twice, and writes who locked it, when, and the restore test reference into the vault's tags.

## What this means

Between deploy and lock, an admin could still turn immutability off. That gap is acceptable because always-on soft delete still keeps deleted backups for the soft delete period, and the gap should be short.

Anyone can see from the vault's own tags who locked it and which restore test it was based on.
