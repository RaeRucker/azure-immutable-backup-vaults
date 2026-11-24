# Immutable Azure Backup Vaults

Bicep for Recovery Services vaults that can't be wiped by a compromised admin account, plus a set of VM backup policies organized by tier.

I've set up immutable vaults in production, one per region in each subscription. This repo is how I'd build that out as code. The names, regions and tier values here are examples.

## What it deploys

One vault per region, each with:

- Geo-redundant storage with Cross Region Restore turned on
- Immutability enabled but not locked
- Soft delete set to always on, with enhanced security
- Diagnostic logs sent to Log Analytics in resource-specific tables, which is what the backup reports and alerts read from
- A backup policy for each tier, generated from [`config/backup-tiers.json`](config/backup-tiers.json)

## Tiers

| Tier | What goes here | Schedule | Retention |
|---|---|---|---|
| Critical | Customer-facing, financial, identity | Every 6 hours | 30 days, 8 weeks, 24 months, 7 years |
| Business-Essential | Internal apps the business needs day to day | Daily | 30 days, 8 weeks, 12 months |
| Operational | File servers, jump boxes, tooling | Daily | 30 days, 4 weeks |
| Non-Production | Dev, test, sandbox | Daily | 14 days |

Every vault gets the same policy names, so one Azure Policy assignment per region can enroll VMs automatically based on a `BackupTier` tag. The [auto-enroll guide](docs/auto-enroll-with-azure-policy.md) walks through that in the portal.

RPO and RTO targets for each tier, and why critical systems also need replication, are in [recovery-objectives.md](docs/recovery-objectives.md).

## Locking immutability

The template never deploys a locked vault. Once a vault is locked you can't shorten its retention ever again, so a typo in a policy would be permanent.

The order I follow:

1. Deploy the vault unlocked.
2. Let backups run and do a test restore using the [restore validation runbook](runbooks/backup-restore-validation.md).
3. Lock it with [`Lock-VaultImmutability.ps1`](scripts/Lock-VaultImmutability.ps1). The script won't run without a reference to that restore test, asks for confirmation, and supports `-WhatIf`.

More on that call in [ADR 0001](docs/decisions/0001-immutability-locked-separately.md). Why it's one GRS vault per region is in [ADR 0002](docs/decisions/0002-one-vault-per-region-geo-redundant.md).

## Deploy

Fill in the workspace ID in each file under `infrastructure/environments`, then:

```bash
for region in eastus2 centralus; do
  az group create -n "rg-backup-$region" -l "$region"
  az deployment group what-if -g "rg-backup-$region" --template-file infrastructure/main.bicep \
    --parameters "infrastructure/environments/$region.bicepparam"
  az deployment group create -g "rg-backup-$region" --template-file infrastructure/main.bicep \
    --parameters "infrastructure/environments/$region.bicepparam"
done
```

You'll need Backup Contributor on the resource groups. Setting up auto-enrollment also needs Resource Policy Contributor.

## Tests

```powershell
Invoke-Pester ./tests -Output Detailed
```

The tests compile the Bicep and check that:

- each tier's schedule can actually meet its RPO
- a more critical tier never has shorter retention than a less critical one
- the vault has GRS, Cross Region Restore, immutability and soft delete set
- nothing in the template locks a vault
- the lock script requires confirmation and restore evidence

CI runs these plus the Bicep linter and a secret scan on every push.

## Cost

Most of the cost is backup storage, and GRS is roughly double LRS. Long yearly retention on the Critical tier is what grows the bill over time, so set it from a real requirement rather than guessing high.

If you're testing this in a lab, don't lock the vaults. An unlocked vault can be deleted after you stop protection and delete the backup data. Soft delete holds that data for another 14 days first.

## Limits

- I haven't deployed this exact template. Bicep type-checks the policy JSON, but Azure hasn't accepted it yet.
- Database backups for Azure SQL and PostgreSQL aren't in here. Those are configured on the database side.
