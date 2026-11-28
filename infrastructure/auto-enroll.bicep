// Auto-enroll for one region, at subscription scope. It creates:
//   - one Azure Policy assignment per tier, using the built-in policy
//     "Configure backup on virtual machines with a given tag to an existing
//      recovery services vault in the same location"
//   - each assignment sends VMs in this region with BackupTier = <tier>
//     to that tier's backup policy in this region's vault
//   - the roles each assignment's managed identity needs to turn on backup
//
// Deploy after main.bicep has created the vault in the same region:
//   az deployment sub create -l eastus2 --template-file infrastructure/auto-enroll.bicep \
//     --parameters infrastructure/environments/auto-enroll-eastus2.bicepparam

targetScope = 'subscription'

@description('Region this deployment covers. Only VMs in this region are enrolled, into the vault in this region.')
param location string

@description('Resource group that holds this region\'s vault.')
param vaultResourceGroupName string

@description('Name of this region\'s vault, created by main.bicep.')
param vaultName string

@description('DeployIfNotExists turns backup on. AuditIfNotExists only reports VMs that would be enrolled.')
@allowed([
  'DeployIfNotExists'
  'AuditIfNotExists'
  'Disabled'
])
param effect string = 'DeployIfNotExists'

@description('Start of each assignment name. The tier and region are added, like backup-critical-eastus2.')
@maxLength(20)
param assignmentPrefix string = 'backup'

var config = loadJsonContent('../config/backup-tiers.json')
var tagName = config.tagName
var tiers = config.tiers

// Built-in policy: Configure backup on virtual machines with a given tag to an
// existing recovery services vault in the same location.
var builtInPolicyId = tenantResourceId('Microsoft.Authorization/policyDefinitions', '345fa903-145c-4fe1-8bcd-93ec2adccde8')

// Roles the built-in policy asks for.
var virtualMachineContributor = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '9980e02c-c2be-4d73-94e8-173b1dc7cf3c')
var backupContributor = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e467623-bb1f-42f4-a55d-6e525e11384b')

resource assignments 'Microsoft.Authorization/policyAssignments@2024-04-01' = [for t in tiers: {
  name: toLower('${assignmentPrefix}-${t.name}-${location}')
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: 'Back up ${t.name} VMs in ${location}'
    description: 'VMs in ${location} tagged ${tagName} = ${t.name} are backed up by ${t.policyName} in ${vaultName}.'
    policyDefinitionId: builtInPolicyId
    parameters: {
      vaultLocation: {
        value: location
      }
      inclusionTagName: {
        value: tagName
      }
      inclusionTagValue: {
        value: [
          t.name
        ]
      }
      backupPolicyId: {
        value: resourceId(subscription().subscriptionId, vaultResourceGroupName, 'Microsoft.RecoveryServices/vaults/backupPolicies', vaultName, t.policyName)
      }
      effect: {
        value: effect
      }
    }
  }
}]

// Virtual Machine Contributor on the subscription, so the identity can turn on backup for any tagged VM.
resource vmRoles 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for (t, i) in tiers: {
  name: guid(subscription().id, assignments[i].id, virtualMachineContributor)
  properties: {
    roleDefinitionId: virtualMachineContributor
    principalId: assignments[i].identity.principalId
    principalType: 'ServicePrincipal'
  }
}]

// Backup Contributor on the vault's resource group only.
module vaultRoles 'modules/vault-role.bicep' = [for (t, i) in tiers: {
  name: 'vault-role-${toLower(t.name)}-${location}'
  scope: resourceGroup(vaultResourceGroupName)
  params: {
    principalId: assignments[i].identity.principalId
    roleDefinitionId: backupContributor
    assignmentId: assignments[i].id
  }
}]

output assignmentNames array = [for (t, i) in tiers: assignments[i].name]
