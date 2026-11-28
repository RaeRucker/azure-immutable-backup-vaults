# Design decision 2: One geo-redundant vault per region, with Cross Region Restore

Status: in use

## The problem

Azure VM backup needs the vault to be in the same region as the VM. A regional outage needs a copy of the data outside that region.

## What I chose

One Recovery Services vault per region in each subscription. Each vault uses geo-redundant storage and has Cross Region Restore turned on. Both are set when the vault is created, because storage redundancy can't be changed once the first backup is configured.

Every vault gets the same four tier policies with the same names.

## What this means

Geo-redundant storage costs more than locally redundant storage, and Cross Region Restore adds its own charge.

Cross Region Restore lets you restore in the paired region. The copy there lags behind. Microsoft says the worst case for Azure VMs is 36 hours. That's longer than the 24 hour recovery point target for Business-Essential and Operational, so after a regional outage those tiers could lose more data than their target. In a normal restore from the main region, the targets still hold.

Restoring from backup can't meet the Critical tier's 4 hour recovery time either. Critical VMs also need replication with Azure Site Recovery, which is covered in [azure-site-recovery-failover-testing](https://github.com/RaeRucker/azure-site-recovery-failover-testing).

Because every vault has the same policy names, the Azure Policy auto-enroll assignments look the same in every region.
