# Immutable Azure Backup Vaults

Bicep that builds Recovery Services vaults a compromised admin account can't wipe, plus a set of VM backup policies organized by tier.

I've set up immutable vaults in production, one per region in each subscription. This repo is how I'd build that out as code. The names, regions and tier values here are examples.

## What it does

It creates one vault per region. Each vault gets:

- Geo-redundant storage, so a copy of every backup lives in the paired region
- Cross Region Restore, so you can restore in that paired region if the main one goes down
- Immutability turned on but not locked, so recovery points can't be deleted early
- Soft delete set to always on, so deleted backups are kept for 14 more days
- Logs sent to Log Analytics for backup reports and alerts
- One backup policy per tier, built from [`config/backup-tiers.json`](config/backup-tiers.json)

## Tiers

| Tier | What goes here | Schedule | Retention |
|---|---|---|---|
| Critical | Customer-facing, financial, identity | Every 6 hours | 30 days, 8 weeks, 24 months, 7 years |
| Business-Essential | Internal apps the business needs day to day | Daily | 30 days, 8 weeks, 12 months |
| Operational | File servers, jump boxes, tooling | Daily | 30 days, 4 weeks |
| Non-Production | Dev, test, sandbox | Daily | 14 days |

To change a schedule or retention, edit `config/backup-tiers.json` and deploy again. Every vault gets the same policy names, so tagging a VM with `BackupTier = Critical` is all it takes to enroll it once auto-enrollment is set up.

## Permissions

| Who | Role | Where it's assigned | Why |
|---|---|---|---|
| You, to deploy | Contributor | The resource group for each vault | To create the vault and its policies |
| You, to deploy | Log Analytics Contributor | The Log Analytics workspace | So the vault can send logs to it |
| You, to set up auto-enrollment | Resource Policy Contributor | Each subscription | To assign the backup policy in Azure Policy |
| You, to set up auto-enrollment | Owner or User Access Administrator | Each subscription | Azure Policy creates an identity that needs roles to enroll VMs |
| You, to tag VMs | Tag Contributor or Contributor | The VMs or their resource groups | To add the `BackupTier` tag |
| You, to run a test restore | Backup Operator | The vault | To start a restore |
| You, to run a test restore | Virtual Machine Contributor and Network Contributor | The resource group the test VM is restored into | To create the restored VM and attach it to the isolated network |
| You, to lock immutability | Contributor or Backup Contributor | The vault | To change the vault's immutability setting |

## Setup

### Step 1. Get the files into Cloud Shell

1. Sign in to the Azure portal.
2. Click the **Cloud Shell** icon in the top bar. It looks like `>_`.
3. Pick **Bash** if it asks.
4. Run:

   ```bash
   git clone https://github.com/RaeRucker/azure-immutable-backup-vaults
   cd azure-immutable-backup-vaults
   ```

### Step 2. Fill in your settings

There's one settings file per region in `infrastructure/environments`.

1. Run `code infrastructure/environments/eastus2.bicepparam` to open it in the Cloud Shell editor.
2. Set `scopeName` to a short name for the subscription or workload. It ends up in the vault name, like `rsv-<scopeName>-eastus2`.
3. Set `workspaceId` to your Log Analytics workspace resource ID. Find it on the workspace under **Overview → JSON View**. It starts with `/subscriptions/`.
4. Press Ctrl+S to save, then Ctrl+Q to close.
5. Do the same for `centralus.bicepparam`. If you use different regions, rename the files and change `location` inside them.

### Step 3. Preview, then deploy

```bash
for region in eastus2 centralus; do
  az group create -n "rg-backup-$region" -l "$region"
  az deployment group what-if -g "rg-backup-$region" --template-file infrastructure/main.bicep \
    --parameters "infrastructure/environments/$region.bicepparam"
done
```

`what-if` only shows what would be created. Read through it. If it looks right, run the same loop again with `create` instead of `what-if`:

```bash
for region in eastus2 centralus; do
  az deployment group create -g "rg-backup-$region" --template-file infrastructure/main.bicep \
    --parameters "infrastructure/environments/$region.bicepparam"
done
```

### Step 4. Check the vault

1. In the portal, search **Recovery Services vaults** and open the new vault.
2. **Properties**: Backup storage redundancy should say Geo-redundant and Cross Region Restore should say Enabled.
3. **Properties → Immutable vault**: should say Enabled, not locked.
4. **Properties → Security settings**: soft delete should be Always on.
5. **Manage → Backup policies**: you should see four policies, one per tier.

### Step 5. Tag your VMs

1. Open a VM and go to **Tags**.
2. Add the name `BackupTier` with one of these values: `Critical`, `Business-Essential`, `Operational` or `Non-Production`.
3. Click **Apply**.

### Step 6. Turn on auto-enrollment

Follow the [auto-enroll guide](docs/auto-enroll-with-azure-policy.md). It walks through assigning the Azure Policy in the portal so every tagged VM gets backed up by the right policy without anyone clicking Enable backup.

### Step 7. Test a restore

Wait until each tier has a few days of backups, then follow the [restore validation runbook](runbooks/backup-restore-validation.md). Do not skip this. You need a working restore before step 8.

### Step 8. Lock immutability

> This can't be undone. Once a vault is locked, nobody can shorten its retention, ever. If a policy has a typo, you're paying for it for years. Don't lock vaults in a lab.

1. Open Cloud Shell and pick **PowerShell** this time.
2. Go to the repo folder with `cd azure-immutable-backup-vaults`.
3. Dry run first. `-WhatIf` shows what would happen without changing anything:

   ```powershell
   ./scripts/Lock-VaultImmutability.ps1 -ResourceGroupName rg-backup-eastus2 -VaultName rsv-<scopeName>-eastus2 -RestoreTestReference <ticket number of your restore test> -WhatIf
   ```

4. Run it again without `-WhatIf` and answer the two confirmation prompts.

The script refuses to lock a vault that isn't geo-redundant, isn't already immutable, or has nothing protected yet. After locking, it writes who locked it, when, and the restore test ticket into the vault's tags.

## If something goes wrong

| What you see | What to check |
|---|---|
| Deployment fails with AuthorizationFailed | You're missing Contributor on the resource group or Log Analytics Contributor on the workspace |
| Deployment fails on the diagnostic setting | Check `workspaceId`. It has to be the full resource ID, not just the workspace name |
| Storage redundancy can't be changed | It locks once the first backup runs. Delete and recreate the vault if it's still empty |
| A tagged VM isn't getting backed up | The policy only checks every so often. Run a remediation task under **Policy → Remediation**, or check the tag spelling |
| The lock script refuses | Read the warning. It tells you which check failed |

## More detail

- [Recovery objectives](docs/recovery-objectives.md) has the RPO and RTO targets per tier and what each one means
- [Why lock separately](docs/decisions/0001-immutability-locked-separately.md)
- [Why one geo-redundant vault per region](docs/decisions/0002-one-vault-per-region-geo-redundant.md)

## Tests

CI runs these on every push. To run them yourself you need PowerShell 7, Pester and the Bicep CLI.

```powershell
Invoke-Pester ./tests -Output Detailed
```

They compile the Bicep and check that:

- each tier's schedule can actually meet its RPO
- a more critical tier never keeps backups for less time than a less critical one
- the vault has geo-redundancy, Cross Region Restore, immutability and soft delete set
- nothing in the template locks a vault
- the lock script requires confirmation and a restore test reference

## Cost

Most of the cost is backup storage, and geo-redundant storage costs about twice as much as local. Long yearly retention on the Critical tier is what grows the bill over time, so base it on a real requirement.

An unlocked vault can be deleted once you stop protection and delete the backup data. Soft delete holds that data for another 14 days before it's really gone.

## Limits

- I haven't deployed this exact template. Bicep checks the policy JSON, but Azure hasn't accepted it yet.
- Database backups for Azure SQL and PostgreSQL aren't covered here. Those are set up on the database side.
