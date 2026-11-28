using '../main.bicep'

param scopeName = 'contoso'
param location = 'centralus'
param workspaceId = '/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-contoso-platform/providers/Microsoft.OperationalInsights/workspaces/law-contoso'
param softDeleteRetentionDays = 14
param disablePublicNetworkAccess = false
