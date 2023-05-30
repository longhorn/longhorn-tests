---
title: Test Node Drain Policy Setting
---

## With `node-drain-policy` is `block-if-contains-last-replica`

### 1. Basic unit tests

#### 1.1 Single worker node cluster with separate master node
1.1.1 RWO volumes
* Deploy Longhorn
* Verify that there is no PDB for `csi-attacher`, `csi-provisioner`, `longhorn-admission-webhook`, and `longhorn-conversion-webhook`
* Manually create a PVC (simulate the volume which has never been attached scenario)
* Verify that there is no PDB for `csi-attacher`, `csi-provisioner`, `longhorn-admission-webhook`, and `longhorn-conversion-webhook` because there is no attached volume
* Create a deployment that uses one RW0 Longhorn volume.
* Verify that there is PDB for `csi-attacher`, `csi-provisioner`, `longhorn-admission-webhook`, and `longhorn-conversion-webhook`
* Create another deployment that uses one RWO Longhorn volume. Scale down this deployment so that the volume is detached
* Drain the node by `kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data --force`
* Observe that the workload pods are evited first -> PDB of `csi-attacher`, `csi-provisioner`, `longhorn-admission-webhook`, and `longhorn-conversion-webhook` are removed -> `csi-attacher`, `csi-provisioner`, `longhorn-admission-webhook`, and `longhorn-conversion-webhook`, and instance-manager-e pods are evicted -> all volumes are successfully detached
* Observe that instance-manager-r is NOT evicted.

1.1.2 RWX volume
* Deploy Longhorn
* Verify that there is no PDB for `csi-attacher`, `csi-provisioner`, `longhorn-admission-webhook`, and `longhorn-conversion-webhook`
* Create a deployment of 2 pods that uses one RWX Longhorn volume.
* Verify that there is PDB for `csi-attacher`, `csi-provisioner`, `longhorn-admission-webhook`, and `longhorn-conversion-webhook`
* Drain the node by `kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data --force`
* Observe that the workload pods are evited first -> PDB of  `csi-attacher`, `csi-provisioner`, `longhorn-admission-webhook`, and `longhorn-conversion-webhook` are removed -> `csi-attacher`, `csi-provisioner`, `longhorn-admission-webhook`, and `longhorn-conversion-webhook`, and instance-manager-e pods are evicted -> all volumes are successfully detached
* Observe that instance-manager-r is NOT evicted.

#### 1.2 multi-node cluster
1.2.1 Multiple healthy replicas
* Deploy Longhorn
* Verify that there is no PDB for `csi-attacher`, `csi-provisioner`, `longhorn-admission-webhook`, and `longhorn-conversion-webhook`
* Manually create a PVC (simulate the volume which has never been attached scenario)
* Verify that there is no PDB for `csi-attacher`, `csi-provisioner`, `longhorn-admission-webhook`, and `longhorn-conversion-webhook` because there is no attached volume
* Create a deployment that uses one RW0 Longhorn volume.
* Verify that there is PDB for `csi-attacher`, `csi-provisioner`, `longhorn-admission-webhook`, and `longhorn-conversion-webhook`
* Create another deployment that uses one RWO Longhorn volume. Scale down this deployment so that the volume is detached
* Create a deployment of 2 pods that uses one RWX Longhorn volume.
* For each node one by one by `kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data --force`
* Verify that the drain can finish successfully
* Uncordon the node and move to next node

1.2.2 Single healthy replicas
* Given Longhorn with 2 nodes cluster: node-1, node-2
* Create a 5Gi volume with 2 replicas. 
* Attached the volume to node-2
* Stop node-1 that contains one of the replicas.
* Set `node-drain-policy` to `block-if-contains-last-replica`
* Attempts to drain node-2 that contains remaining replica.
* The node-2 becomes cordoned.
* All pods on node-2 are evicted except the replica instance manager pod.
* The message like below keeps appearing.
    ```
    evicting pod longhorn-system/instance-manager-r-xxxxxxxx
    error when evicting pods/"instance-manager-r-xxxxxxxx" -n "longhorn-system" (will retry after 5s): Cannot evict pod as it would violate the pod's disruption budget.
    ```



### 2. Upgrade Kubernetes for k3s cluster with standalone System Upgrade Controller deployment
* Deploy a 3 nodes with each node has all roles (master + worker)
* Install the [System Upgrade Controller](https://github.com/rancher/system-upgrade-controller#deploying)
* Deploy Longhorn
* Manually create a PVC (simulate the volume which has never been attached scenario)
* Create a deployment that uses one RW0 Longhorn volume.
* Create another deployment that uses one RWO Longhorn volume. Scale down this deployment so that the volume is detached
* Create another deployment of 2 pods that uses one RWX Longhorn volume.
* Deploying the `plan` CR to upgrade Kubernetes similar to:
```
  apiVersion: upgrade.cattle.io/v1
  kind: Plan
  metadata:
    name: k3s-server
    namespace: system-upgrade
  spec:
    concurrency: 1
    cordon: true
    nodeSelector:
      matchExpressions:
      - key: node-role.kubernetes.io/master
        operator: In
        values:
        - "true"
    serviceAccountName: system-upgrade
    drain:
      force: true
      skipWaitForDeleteTimeout: 60 # 1.18+ (honor pod disruption budgets up to 60 seconds per pod then moves on)
    upgrade:
      image: rancher/k3s-upgrade
    version: v1.21.11+k3s1
  ```
Note that the `concurrency` should be 1 to upgrade node one by one. `version` should be a newer K3s version. And it should contains the `drain` stage
* Verify that the upgrade went smoothly
* Exec into workload pod and make sure that the data is still there
* Repeat the upgrading process above 5 times to make sure

### 3. Upgrade Kubernetes for imported  k3s cluster in Rancher
* Creating a 3-node k3s cluster with each node is both master+worker role. K3s should be an old version such as `v1.21.9+k3s1` so that we can upgrade multiple times. Some instructions to create such cluster is here https://docs.k3s.io/datastore/ha-embedded
* Import the cluster into Rancher by: go to cluster management -> create new cluster -> generic cluster -> follow the instruction over there
* Update the upgrade strategy in cluster management -> click three dots menu on the imported cluster -> edit config -> K3s options -> close drain for both control plane and worker node like below:
![Screenshot from 2023-03-14 17-53-24](https://user-images.githubusercontent.com/22139961/225175432-87f076ac-552c-464a-a466-42356f1ac8e2.png)
* Install Longhorn
* Manually create a PVC (simulate the volume which has never been attached scenario)
* Create a deployment that uses one RW0 Longhorn volume.
* Create another deployment that uses one RWO Longhorn volume. Scale down this deployment so that the volume is detached
* Create another deployment of 2 pods that uses one RWX Longhorn volume.
* Using Rancher to upgrade the cluster to a newer Kubernetes version
* Verify that the upgrade went smoothly
* Exec into workload pod and make sure that the data is still there

### 4. Upgrade Kubernetes for provisioned k3s cluster in Rancher
* Using Rancher to provision a k3s cluster with an old version. For example, `v1.22.11+k3s2`. The cluster has 3 nodes each node with both worker and master role. Set the upgrade strategy as below:
![Screenshot from 2023-03-14 15-44-34](https://user-images.githubusercontent.com/22139961/225163284-51c017ed-650c-4263-849c-054a0a0abf20.png)
* Install Longhorn
* Manually create a PVC (simulate the volume which has never been attached scenario)
* Create a deployment that uses one RW0 Longhorn volume.
* Create another deployment that uses one RWO Longhorn volume. Scale down this deployment so that the volume is detached
* Create another deployment of 2 pods that uses one RWX Longhorn volume.
* Using Rancher to upgrade the cluster to a newer Kubernetes version
* Verify that the upgrade went smoothly
* Exec into workload pod and make sure that the data is still there

## With `node-drain-policy` is `allow-if-replica-is-stopped`

1. Repeat the test cases above. 
1. Verify that in the test `1.1.1`, `1.1.2`, `1.2.1`, `2`,`3`, and `4`, the drain is successfully. 
1. Verify that the test `1.2.2`, the drain is still failed


## With `node-drain-policy` as `always-allow`
1. Repeat the test cases above.
1. Verify that in the test `1.1.1`, `1.1.2`, `1.2.1`, `1.2.2`, `2`,`3`, and `4`, the drain is successfully. 



