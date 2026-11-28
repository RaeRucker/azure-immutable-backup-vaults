// Gives one policy assignment's managed identity a role on the vault's resource group.
targetScope = 'resourceGroup'

@description('Object ID of the policy assignment\'s managed identity.')
param principalId string

@description('Full ID of the role to give.')
param roleDefinitionId string

@description('ID of the policy assignment. Only used to make the role assignment name unique.')
param assignmentId string

resource role 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, assignmentId, roleDefinitionId)
  properties: {
    roleDefinitionId: roleDefinitionId
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
