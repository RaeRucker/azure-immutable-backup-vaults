<#
.SYNOPSIS
    Locks immutability on Recovery Services vaults. This can't be undone.
.DESCRIPTION
    A locked vault can never be unlocked, and backup retention can't be reduced for
    as long as the vault exists. So locking is its own step, and it needs proof first.

      - -RestoreTestReference is required. It's the ticket or report ID of a passed
        restore test for this vault. See runbooks/backup-restore-validation.md.
      - The vault must already have immutability turned on but not locked, use
        geo-redundant storage, and have at least one protected Azure VM.
      - You're asked to confirm twice. -WhatIf shows what would happen.

    After locking, the script writes who locked the vault, when, and the restore test
    reference into tags on the vault. The tag names are parameters.
.EXAMPLE
    ./scripts/Lock-VaultImmutability.ps1 -ResourceGroupName rg-backup-eastus2 -VaultName rsv-contoso-eastus2 -RestoreTestReference CHG-2026-0412 -WhatIf
.NOTES
    Needs the Az.RecoveryServices module. Needs Contributor on the vault, or Backup
    Contributor plus Tag Contributor.
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory)] [string] $ResourceGroupName,
    [Parameter(Mandatory)] [string[]] $VaultName,

    [Parameter(Mandatory)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$')]
    [string] $RestoreTestReference,

    [string] $LockedByTagName = 'immutabilityLockedBy',
    [string] $LockedOnTagName = 'immutabilityLockedOn',
    [string] $EvidenceTagName = 'immutabilityEvidence',

    [switch] $Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not (Get-Module -ListAvailable -Name Az.RecoveryServices)) { throw 'Install-Module Az.RecoveryServices' }
if (-not (Get-AzContext)) { throw 'Run Connect-AzAccount first.' }

foreach ($name in $VaultName) {
    $vault = Get-AzRecoveryServicesVault -ResourceGroupName $ResourceGroupName -Name $name
    $state = $vault.Properties.ImmutabilitySettings.ImmutabilityState
    $redundancy = (Get-AzRecoveryServicesBackupProperty -Vault $vault).BackupStorageRedundancy
    $items = @(Get-AzRecoveryServicesBackupItem -VaultId $vault.ID -BackupManagementType AzureVM -WorkloadType AzureVM)

    $problems = @()
    if ($state -eq 'Locked') { Write-Output "$name is already locked. Nothing to do."; continue }
    if ($state -ne 'Unlocked') { $problems += "immutability is '$state' (must be Unlocked first)" }
    if ($redundancy -ne 'GeoRedundant') { $problems += "storage redundancy is '$redundancy' (expected GeoRedundant)" }
    if ($items.Count -eq 0) { $problems += 'no protected items (lock after protection and a restore test)' }
    if ($problems) { Write-Warning "Refusing to lock ${name}: $($problems -join '; ')"; continue }

    $message = "LOCK immutability on $name ($($items.Count) protected items). This can never be undone, and retention can never be reduced. Evidence: $RestoreTestReference"
    if ($PSCmdlet.ShouldProcess($name, 'Lock vault immutability (irreversible)') -and ($Force -or $PSCmdlet.ShouldContinue($message, 'Irreversible change'))) {
        $null = Update-AzRecoveryServicesVault -ResourceGroupName $ResourceGroupName -Name $name -ImmutabilityState Locked
        $tags = @{
            $LockedByTagName = (Get-AzContext).Account.Id
            $LockedOnTagName = (Get-Date -Format 'yyyy-MM-dd')
            $EvidenceTagName = $RestoreTestReference
        }
        $null = Update-AzTag -ResourceId $vault.ID -Tag $tags -Operation Merge
        Write-Output "$name locked. Evidence $RestoreTestReference recorded in vault tags."
    }
}
