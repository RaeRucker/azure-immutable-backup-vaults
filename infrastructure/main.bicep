// One deployment per region, at resource group scope. It creates:
//   - a Recovery Services vault with geo-redundant storage, Cross Region Restore,
//     immutability turned on but not locked, and always-on soft delete
//   - one Azure VM backup policy per tier from config/backup-tiers.json
//   - a diagnostic setting that sends backup logs to resource-specific tables in Log Analytics
//
// Deploy:
//   az deployment group create -g rg-backup-eastus2 --template-file infrastructure/main.bicep \
//     --parameters infrastructure/environments/eastus2.bicepparam

@description('Short name used in the vault name, for example the subscription or workload.')
@maxLength(20)
param scopeName string

@description('Region for the vault. A VM can only back up to a vault in its own region.')
param location string = resourceGroup().location

@description('Log Analytics workspace for backup diagnostics. Empty skips diagnostics.')
param workspaceId string = ''

@description('Disable public network access to the vault (requires private endpoints for backup traffic).')
param disablePublicNetworkAccess bool = false

@description('Vault name. Default is rsv-<scopeName>-<location>.')
param vaultName string = 'rsv-${scopeName}-${location}'

@description('Days a deleted backup is kept before it is gone for good.')
@minValue(14)
@maxValue(180)
param softDeleteRetentionDays int = 14

@description('Name of the diagnostic setting on the vault.')
param diagnosticSettingName string = 'diag-to-law'

@description('Vault log categories sent to Log Analytics. All of these write to resource-specific tables.')
param logCategories array = [
  'CoreAzureBackup'
  'AddonAzureBackupJobs'
  'AddonAzureBackupPolicy'
  'AddonAzureBackupStorage'
  'AddonAzureBackupProtectedInstance'
  'AzureBackupOperations'
]

@description('Tags on the vault.')
param tags object = {
  workload: 'backup'
  managedBy: 'bicep'
}

var tiers = loadJsonContent('../config/backup-tiers.json').tiers

// Schedule and retention times are full timestamps. Only the time of day is used.
func scheduleTime(hhmm string) string => '2026-01-04T${hhmm}:00Z'

resource vault 'Microsoft.RecoveryServices/vaults@2024-04-01' = {
  name: vaultName
  location: location
  tags: tags
  sku: {
    name: 'RS0'
    tier: 'Standard'
  }
  properties: {
    publicNetworkAccess: disablePublicNetworkAccess ? 'Disabled' : 'Enabled'
    redundancySettings: {
      // Can't be changed after the first backup is configured.
      standardTierStorageRedundancy: 'GeoRedundant'
      crossRegionRestore: 'Enabled'
    }
    securitySettings: {
      immutabilitySettings: {
        // Unlocked means immutability is on but can still be turned off.
        // Lock it with scripts/Lock-VaultImmutability.ps1 after a restore test passes.
        state: 'Unlocked'
      }
      softDeleteSettings: {
        // Always-on soft delete can't be turned off once set.
        softDeleteState: 'AlwaysON'
        softDeleteRetentionPeriodInDays: softDeleteRetentionDays
        enhancedSecurityState: 'Enabled'
      }
    }
  }
}

resource policies 'Microsoft.RecoveryServices/vaults/backupPolicies@2024-04-01' = [for t in tiers: {
  parent: vault
  name: t.policyName
  properties: {
    backupManagementType: 'AzureIaasVM'
    policyType: t.policyType
    instantRpRetentionRangeInDays: t.instantRestoreDays
    timeZone: 'UTC'
    schedulePolicy: t.frequency == 'Hourly' ? {
      schedulePolicyType: 'SimpleSchedulePolicyV2'
      scheduleRunFrequency: 'Hourly'
      hourlySchedule: {
        interval: t.everyHours
        scheduleWindowStartTime: scheduleTime(t.startTimeUtc)
        scheduleWindowDuration: t.windowHours
      }
    } : t.policyType == 'V2' ? {
      // Daily Enhanced policy. Needed for Trusted Launch VMs, which are the default for new VMs.
      schedulePolicyType: 'SimpleSchedulePolicyV2'
      scheduleRunFrequency: 'Daily'
      dailySchedule: {
        scheduleRunTimes: [
          scheduleTime(t.startTimeUtc)
        ]
      }
    } : {
      schedulePolicyType: 'SimpleSchedulePolicy'
      scheduleRunFrequency: 'Daily'
      scheduleRunTimes: [
        scheduleTime(t.startTimeUtc)
      ]
    }
    retentionPolicy: union(
      {
        retentionPolicyType: 'LongTermRetentionPolicy'
        dailySchedule: {
          retentionTimes: [
            scheduleTime(t.startTimeUtc)
          ]
          retentionDuration: {
            count: t.retention.days
            durationType: 'Days'
          }
        }
      },
      t.retention.weeks > 0 ? {
        weeklySchedule: {
          daysOfTheWeek: [
            'Sunday'
          ]
          retentionTimes: [
            scheduleTime(t.startTimeUtc)
          ]
          retentionDuration: {
            count: t.retention.weeks
            durationType: 'Weeks'
          }
        }
      } : {},
      t.retention.months > 0 ? {
        monthlySchedule: {
          retentionScheduleFormatType: 'Weekly'
          retentionScheduleWeekly: {
            daysOfTheWeek: [
              'Sunday'
            ]
            weeksOfTheMonth: [
              'First'
            ]
          }
          retentionTimes: [
            scheduleTime(t.startTimeUtc)
          ]
          retentionDuration: {
            count: t.retention.months
            durationType: 'Months'
          }
        }
      } : {},
      t.retention.years > 0 ? {
        yearlySchedule: {
          retentionScheduleFormatType: 'Weekly'
          monthsOfYear: [
            'January'
          ]
          retentionScheduleWeekly: {
            daysOfTheWeek: [
              'Sunday'
            ]
            weeksOfTheMonth: [
              'First'
            ]
          }
          retentionTimes: [
            scheduleTime(t.startTimeUtc)
          ]
          retentionDuration: {
            count: t.retention.years
            durationType: 'Years'
          }
        }
      } : {}
    )
  }
}]

resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (!empty(workspaceId)) {
  name: diagnosticSettingName
  scope: vault
  properties: {
    workspaceId: workspaceId
    logAnalyticsDestinationType: 'Dedicated'
    logs: [for category in logCategories: {
      category: category
      enabled: true
    }]
  }
}

output vaultName string = vault.name
output vaultId string = vault.id
output policyIds array = [for (t, i) in tiers: policies[i].id]
