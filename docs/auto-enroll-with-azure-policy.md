# Auto-enroll VMs into the right backup tier with Azure Policy

With this set up, a VM tagged `BackupTier = Critical` gets backed up by the Critical policy in its region's vault without anyone clicking Enable backup. The same goes for the other tiers.

## How it fits together

```text
VM tagged BackupTier = Business-Essential
          │
          ▼
Azure Policy assignment, one per tier per region
  "Configure backup on virtual machines with a given tag
   to an existing recovery services vault in the same location"
          │
          ▼
VM backed up in rsv-<scopeName>-<region> by pol-vm-business-essential-daily
```

The built-in policy works on one region at a time, and the vault has to be in the same subscription and region as the VMs. So you need one assignment for each tier in each region. With four tiers and two regions, that's eight assignments per subscription.

## Permissions

| Who | Role | Where it's assigned | Why |
|---|---|---|---|
| You | Resource Policy Contributor | The subscription | To create the policy assignments |
| You | Owner, User Access Administrator, or Role Based Access Control Administrator | The subscription | To give the assignment's managed identity its roles |
| The assignment's managed identity | Virtual Machine Contributor and Backup Contributor | The subscription | To turn on backup for each tagged VM |

A managed identity is an account Azure creates for the policy assignment, so it can make changes without a stored password. When you create the assignment in the portal, it gives the identity both roles for you. If you deploy assignments with code, you have to assign the roles yourself.

## Step 1. Tag the VMs

| Tag name | Values |
|---|---|
| `BackupTier` | `Critical`, `Business-Essential`, `Operational` or `Non-Production` |

Spelling and case matter. A VM without the tag is never enrolled, so step 4 shows how to find untagged VMs.

If you want every new VM to have the tag, you can also assign the built-in policy Require a tag on resources. If you set tiers per resource group instead, use Inherit a tag from the resource group if missing.

## Step 2. Assign the policy

1. In the Azure portal, open Policy → Authoring → Definitions.
2. Set the Category filter to Backup.
3. Open Configure backup on virtual machines with a given tag to an existing recovery services vault in the same location.
4. Click Assign.
5. On Basics, set Scope to the subscription. Name the assignment `backup-<tier>-<region>`, like `backup-critical-eastus2`.
6. On Parameters, untick Only show parameters that need input or review if you need to see them all, then set:
   - Location: the region, like `eastus2`
   - Inclusion Tag Name: `BackupTier`
   - Inclusion Tag Values: `["Critical"]`
   - Backup Policy: `pol-vm-critical-6h` from that region's vault
7. On Remediation, tick Create a remediation task so VMs that are already tagged get enrolled too. Leave Create a Managed Identity ticked and pick the same region for it.
8. Click Review + create, then Create.

Repeat for every tier and region. Microsoft suggests keeping each assignment under about 200 VMs, or backups can take hours to start.

## Step 3. Leave out what shouldn't be backed up this way

Only tagged VMs are enrolled, so the simplest way to leave something out is to not tag it. If you use a policy that copies tags down from the resource group, some VMs may pick up a tag you didn't mean them to have. Use a policy exemption for those.

| What | Why leave it out | How |
|---|---|---|
| AKS node resource groups, the ones that start with `MC_` | Nodes are rebuilt by AKS. Back up the cluster with AKS backup instead. | Exemption on the `MC_` resource groups, category Waiver |
| Databricks managed resource groups | Azure manages these | Exemption |
| Build agents and scale set instances | They're rebuilt from images | Don't tag them |

To add an exemption, open the assignment under Policy → Authoring → Assignments and click Create exemption. Exemptions show in compliance reports with a reason, so anyone can see an exclusion was on purpose.

## Step 4. Check coverage

Policy → Compliance shows tagged VMs that still aren't backed up.

To find VMs with no tier tag, open Resource Graph Explorer in the portal and run:

```kusto
resources
| where type =~ 'microsoft.compute/virtualmachines'
| where isempty(tags.BackupTier)
| where resourceGroup !startswith 'mc_'
| project subscriptionId, resourceGroup, name, location
```

To find VMs that aren't backed up at all:

```kusto
resources
| where type =~ 'microsoft.compute/virtualmachines'
| extend vmId = tolower(id)
| join kind=leftouter (
    recoveryservicesresources
    | where type =~ 'microsoft.recoveryservices/vaults/backupfabrics/protectioncontainers/protecteditems'
    | where properties.backupManagementType == 'AzureIaasVM'
    | extend vmId = tolower(tostring(properties.sourceResourceId))
    | project vmId, protectedBy = tostring(properties.policyName)
  ) on vmId
| where isempty(protectedBy)
| project subscriptionId, resourceGroup, name, location, tier = tostring(tags.BackupTier)
```

To save either result, click Download as CSV.

## If something goes wrong

| What you see | What to check |
|---|---|
| A tagged VM isn't enrolled after a day | Check the tag spelling, then run a remediation task under Policy → Remediation |
| The remediation task fails | Open it and check the error. Usually the managed identity is missing one of its two roles, or the VM is in a different region than the vault |
| Backup Policy shows no choices | The vault isn't in the region you set under Location, or the vault has no Azure VM policies yet |
