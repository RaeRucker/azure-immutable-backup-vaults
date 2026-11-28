# Recovery objectives

The numbers on this page are targets. They say what each tier is built for. Nothing here has been measured. Real numbers come from restore tests.

This page covers the backup side only. Replication and failover with Azure Site Recovery are in a separate repo, [azure-site-recovery-failover-testing](https://github.com/RaeRucker/azure-site-recovery-failover-testing).

## Terms

| Term | What it means | What sets it |
|---|---|---|
| RPO, recovery point objective | The most data you can afford to lose, counted back from the failure | How often backups run |
| RTO, recovery time objective | The longest a system can be down, from the moment you declare a problem to the system working again | How you recover it, and how much of that is automated |

RTO counts everything from spotting the problem to checking the system works again, not just the restore. The restore itself is usually the shortest part.

## Targets by tier

| Tier | RPO target | RTO target | How it's recovered from backup |
|---|---|---|---|
| Critical | 6 hours | 4 hours | Restore from the 6-hourly backup for corruption, deletion or ransomware. A regional outage needs Site Recovery to meet 4 hours. |
| Business-Essential | 24 hours | 24 hours | Restore in the same region, or Cross Region Restore in the paired region |
| Operational | 24 hours | 72 hours | Cross Region Restore, or rebuild the server and restore only the data |
| Non-Production | 24 hours | 1 week | Rebuild. Restore only if someone needs the data. |

The tiers, schedules and retention are in [`config/backup-tiers.json`](../config/backup-tiers.json). The tests check that each tier's RPO target isn't shorter than the time between its backups.

## What backup covers and what it doesn't

| Failure | Example | Can backup recover it? |
|---|---|---|
| Logical | Ransomware, an accidental delete, a bad data change | Yes. Restore a recovery point from before the damage. Replication can't help here because it copies the damage within minutes. |
| Regional | A region or zone outage | Yes, through Cross Region Restore, but slowly. For a tight RTO, use Site Recovery. |

Logical failures are why the vaults are immutable and soft delete is always on. An attacker with admin access can't delete the recovery points you'd need to recover from ransomware.

## Restoring in the paired region

- Geo-redundant storage copies backups to the region's Azure pair, for example East US 2 to Central US. Cross Region Restore restores there. Check the pair for your own regions.
- The copy in the paired region lags behind. Microsoft says the worst case for Azure VMs is 36 hours. That's longer than the 24 hour RPO targets, so after a regional outage you could lose more data than the target.
- Backup items can take up to 48 hours to show up in the paired region after Cross Region Restore is turned on.
- In a large outage, many people restore into the same paired region at once. Some VM sizes may not be available. Capacity reservations are the way around that, at a cost.
- What the restored VMs depend on, like domain controllers, DNS, Key Vault and the network, has to exist in the paired region already, or be recovered first.
