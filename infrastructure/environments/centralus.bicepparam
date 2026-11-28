using '../main.bicep'

param scopeName = 'contoso-prod'
param location = 'centralus'
param workspaceId = '/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-contoso-prod-platform/providers/Microsoft.OperationalInsights/workspaces/law-contoso-prod'
param softDeleteRetentionDays = 14
param disablePublicNetworkAccess = false
