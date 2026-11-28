using '../auto-enroll.bicep'

param location = 'eastus2'
param vaultResourceGroupName = 'rg-backup-eastus2'
param vaultName = 'rsv-contoso-prod-eastus2'
param effect = 'DeployIfNotExists'
