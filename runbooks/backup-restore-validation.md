# Runbook: Test a backup restore

A backup you haven't restored is only a guess. This runbook checks that a recovery point restores, that nothing is missing, and that the system works.

Run it every quarter for each tier, after any change to backup settings, and before you lock a vault. [`scripts/Lock-VaultImmutability.ps1`](../scripts/Lock-VaultImmutability.ps1) asks for the test ID from the record at the bottom of this page.

## What to test and how often

| Test | Critical | Business-Essential and Operational |
|---|---|---|
| Full VM restore to an isolated network | Every quarter | Every quarter, one VM per tier |
| File restore | Every quarter | Every 6 months |
| Cross Region Restore | Every 6 months | Every year |

Non-Production doesn't need regular restore tests. Those VMs are rebuilt, not restored.

## Permissions

| Who | Role | Where it's assigned | Why |
|---|---|---|---|
| You | Backup Operator | The vault | To start the restore |
| You | Virtual Machine Contributor | The VM that was backed up | Restores read settings from the original VM |
| You | Contributor | The resource group the test VM is restored into | To create the VM, its disks and its network card, and connect it to the test network |
| You | Storage Account Contributor | The staging storage account | Restores copy data through it |
| You, for Cross Region Restore | Backup Operator | The vault's subscription | Cross Region Restore needs it at subscription level |

## Before you start

1. Create a resource group for the test, like `rg-restore-test-eastus2`, in the vault's region.
2. Create a virtual network in it with no peering and no VPN, so the restored VM can't reach anything real. The restored VM keeps the same computer name and domain settings as the original, so it must not see the real network.
3. Create a Standard general-purpose v2 storage account in the same region for staging.

For Cross Region Restore, do the same in the paired region.

## Full VM restore

1. In the portal, open the vault and go to Protected items → Backup items → Azure Virtual Machine.
2. Click the VM, then Restore VM.
3. Under Restore point, click Select. Pick one that's at least a day old. That shows older points work, not just the newest one.
4. Under Restore configuration, pick Create new, then set Restore Type to Create new virtual machine.
5. Give it a VM name that isn't used anywhere in the subscription, like `<vmname>-rt`.
6. Pick the test resource group, the isolated network and its subnet.
7. Set Staging Location to the test storage account.
8. Click Restore and write down the time.
9. Go to Monitoring → Backup jobs. When the restore job shows Completed, write down the end time and the duration.

### Check it

| Check | How | It passes when |
|---|---|---|
| It boots | Help → Boot diagnostics, then sign in through Serial console or Bastion | You reach a sign-in prompt |
| No disks are missing | Disk Management on Windows, or `lsblk` on Linux | Every data disk is there |
| The data is recent | Compare the newest file or database row with the restore point time | Within one backup interval |
| The app works | Start the service. For SQL Server, run `DBCC CHECKDB`. | No errors |

### Clean up

Delete the restored VM, its disks, its network card and the files in the staging storage account. Don't leave any of it running. It costs money and has the same identity as the real server.

## Cross Region Restore

1. In the vault, go to Protected items → Backup items and switch the view to Secondary Region. This only shows up when Cross Region Restore is on, which `infrastructure/main.bicep` does.
2. Restore the VM the same way as above, using the test network and staging storage account in the paired region.
3. Check it the same way.
4. Write down how old the newest recovery point in the paired region was. That's how much data you'd really lose if the main region went down.

## Record

Copy this table into your ticket or test report.

| Field | Value |
|---|---|
| Test ID. Use this as `-RestoreTestReference` when locking. | |
| Vault, VM and restore point time | |
| Restore job duration | |
| Check results | |
| Problems found | |
