---
title: Upgrade Kubernetes using Rancher UI
---

Note: Longhorn version v1.3.x doesn't support Kubernetes v1.25 and onwards

Test with Longhorn default setting of 'Node Drain Policy': `block-if-contains-last-replica`
---

### 1. Upgrade single node cluster using Rancher UI - RKE2 cluster

**Given**  Single node RKE2 cluster provisioned in Rancher with K8s prior version with Longhorn installed

AND few RWO and RWX volumes attached with node/pod exists

AND 1 RWO and 1 RWX volumes unattached

AND 1 RWO volume with 50 Gi data

**When** Upgrade the Kubernetes version to latest version

**Then** Upgrade should be successful

AND Volumes should be healthy and data should be intact after upgrade completes

AND The volumes which were attached initially should be attached and the ones which is unattached should be unattached

AND Logs should not have any unexpected errors

### 2. Upgrade multi node cluster using Rancher UI - RKE2 cluster

**Given**  Multi node (1 master, 3 workers) RKE2 cluster provisioned in Rancher with K8s prior version with Longhorn installed

AND few RWO and RWX volumes attached with node/pod exists

AND 1 RWO and 1 RWX volumes unattached

AND 1 RWO volume with 50 Gi data

**When** Upgrade the Kubernetes version to latest version

**Then** Upgrade should be successful

AND Volumes should be healthy and data should be intact after upgrade completes

AND The volumes which were attached initially should be attached and the ones which is unattached should be unattached

AND Logs should not have any unexpected errors


### 3. Upgrade multi node cluster using Rancher UI - RKE1 cluster

**Given**  Multi node (1 master, 3 workers) RKE1 cluster provisioned in Rancher with K8s prior version with Longhorn installed

AND few RWO and RWX volumes attached with node/pod exists

AND 1 RWO and 1 RWX volumes unattached

AND 1 RWO volume with 50 Gi data


**When** Upgrade the Kubernetes version to latest version

**Then** Upgrade should be successful

AND Volumes should be healthy and data should be intact after upgrade completes

AND The volumes which were attached initially should be attached and the ones which is unattached should be unattached

AND Logs should not have any unexpected errors


### 4. Upgrade multi node cluster using Rancher UI - K3s cluster

**Given**  Multi node (1 master, 3 workers) K3s cluster provisioned in Rancher with K8s prior version with Longhorn installed

AND few RWO and RWX volumes attached with node/pod exists

AND 1 RWO and 1 RWX volumes unattached

AND 1 RWO volume with 50 Gi data

**When** Upgrade the Kubernetes version to latest version

**Then** Upgrade should be successful

AND Volumes should be healthy and data should be intact after upgrade completes

AND The volumes which were attached initially should be attached and the ones which is unattached should be unattached

AND Logs should not have any unexpected errors


### 5. Upgrade multi node cluster using Rancher UI - K3s Imported cluster

**Given**  Multi node (1 master, 3 workers) imported K3s cluster with K3s prior version with Longhorn installed

AND few RWO and RWX volumes attached with node/pod exists

AND 1 RWO and 1 RWX volumes unattached

AND 1 RWO volume with 50 Gi data

**When** Upgrade the Kubernetes version to latest version

**Then** Upgrade should be successful

AND Volumes should be healthy and data should be intact after upgrade completes

AND The volumes which were attached initially should be attached and the ones which is unattached should be unattached

AND Logs should not have any unexpected errors


### 6. Interrupt upgrade on multi node cluster

**Given**  Multi node (1 master, 3 workers) imported K3s cluster with K3s prior version with Longhorn installed

AND few RWO and RWX volumes attached with node/pod exists

AND 1 RWO and 1 RWX volumes unattached

**When** Upgrade the Kubernetes version to latest version, while upgrade is in progress kill the kubelet process on nodes

**Then** Upgrade should be successful as the kubelet should restart

AND No volume's data should be lost


**Note**: Below script can be used to kill kubelet continuously

```shell script
#!/bin/bash

while true; do
 # Find the process ID of the k3s kubelet
 pid=$(ps -ef | grep kubelet | grep -v grep | awk '{print $2}')

 if [ -z "$pid" ]; then
   echo "kubelet process not found"
 else
   # Kill the k3s kubelet process
   sudo kill $pid
   echo "kubelet process killed"
 fi

 # Wait for 5 seconds before checking again
 sleep 5
done
```

Test with Longhorn setting of 'Node Drain Policy': `allow-if-replica-is-stopped`
---
#### Repeat below test cases
1. Upgrade multi node cluster using Rancher UI - RKE2 cluster
2. Upgrade multi node cluster using Rancher UI - RKE1 cluster
3. Upgrade multi node cluster using Rancher UI - K3s Imported cluster

Test with Longhorn setting of 'Node Drain Policy': `always-allow`
---
#### Repeat below test cases
1. Upgrade multi node cluster using Rancher UI - RKE2 cluster
2. Upgrade multi node cluster using Rancher UI - RKE1 cluster
3. Upgrade multi node cluster using Rancher UI - K3s Imported cluster
