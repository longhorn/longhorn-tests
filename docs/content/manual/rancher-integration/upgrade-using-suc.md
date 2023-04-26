---
title: Upgrade Kubernetes using SUC
---

Note: Longhorn version v1.3.x doesn't support Kubernetes v1.25 and onwards

Test with Longhorn default setting of 'Node Drain Policy': `block-if-contains-last-replica`
---

### 1. Upgrade multi node cluster using SUC - K3s cluster

**Given**  Multi node (1 master and 3 worker) K3s cluster (not provisioned by Rancher) with K3s prior version with Longhorn installed

AND [System Upgrade Controller](https://github.com/rancher/system-upgrade-controller#deploying) deployed

AND few RWO and RWX volumes attached with node/pod exists

AND 1 RWO and 1 RWX volumes unattached

AND 1 RWO volume with 50 Gi data

**When** Upgrade the cluster using the `plan` CR

**Then** Upgrade should be successful
 
AND Volumes should be healthy and data should be intact after upgrade completes

AND The volumes which were attached initially should be attached and the ones which is unattached should be unattached

AND Logs should not have any unexpected errors


### 2. Upgrade multi node cluster using SUC - Concurrency of node to upgrade > 1 

**Given**  Multi node (1 master and 3 worker) K3s cluster (not provisioned by Rancher) prior version with Longhorn installed

AND [System Upgrade Controller](https://github.com/rancher/system-upgrade-controller#deploying) deployed

AND few RWO and RWX volumes attached with node/pod exists

AND 1 RWO and 1 RWX volumes unattached

AND 1 RWO volume with 50 Gi data

**When** Set the concurrency to 2 in the `plan` CR and upgrade the cluster

**Then** Upgrade should be successful
 
AND Volumes should be healthy and data should be intact after upgrade completes

AND The volumes which were attached initially should be attached and the ones which is unattached should be unattached

AND Logs should not have any unexpected errors
