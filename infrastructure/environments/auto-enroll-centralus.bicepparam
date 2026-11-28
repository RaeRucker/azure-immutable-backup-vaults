using '../auto-enroll.bicep'

param location = 'centralus'
param vaultResourceGroupName = 'rg-backup-centralus'
param vaultName = 'rsv-contoso-centralus'
param effect = 'DeployIfNotExists'
