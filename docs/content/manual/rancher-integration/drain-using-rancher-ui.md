---
title: Drain using Rancher UI
---

**Note:** Enabling `Delete Empty Dir Data` is mandatory to drain a node if a pod is associated with any storage.


Test with Longhorn default setting of 'Node Drain Policy': `block-if-contains-last-replica`
----

### 1. Drain operation on single node using Rancher UI

**Given**  Single node (1 Worker) cluster with Longhorn installed

AND few RWO and RWX volumes attached with node/pod exists

AND 1 RWO and 1 RWX volumes unattached

**When** Drain the node with default values of Rancher UI

**Then** Drain should be blocked, user can see Rancher trying to drain the node but stuck in `drainig` and `cordoned`

AND Volumes should be healthy and data should be intact once user stops `drain` and `uncordoned` the node

AND The volumes which were attached initially should be attached and the ones which is unattached should be unattached

AND Logs should not have any unexpected errors

### 2. Drain operation on single node using Rancher UI with `Delete Empty Dir Data`

**Given**  Single node (1 Worker) cluster with Longhorn installed

AND few RWO and RWX volumes attached with node/pod exists

AND 1 RWO and 1 RWX volumes unattached

**When** Drain the worker node one by one with `Delete Empty Dir Data` set to `Yes` and other values to default using Rancher UI

**Then** Drain should be blocked. Longhorn's pdb should prevent draining the IM from the node.

AND Volumes should be healthy and data should be intact once user stops `drain` and `uncordoned` the node

AND The volumes which were attached initially should be attached and the ones which is unattached should be unattached

AND Logs should not have any unexpected errors


### 3. Drain operation on a multiple node using Rancher UI - default value

**Given**  Cluster with 1 etcd/control plane and 3 worker nodes with Longhorn installed

AND few RWO and RWX volumes attached with node/pod exists

AND few RWO and RWX volumes unattached

**When** Drain the worker node one by one with `Delete Empty Dir Data` set to `Yes` and other values to default using Rancher UI

**Then** Drain should be successful
 
AND Volumes should be healthy and data should be intact after drain completes

AND The volumes which were attached initially should be attached and the ones which is unattached should be unattached

AND Logs should not have any unexpected errors


### 4. Drain operation on a multiple node using Rancher UI - Force

**Given**  Cluster with 1 etcd/control plane and 3 worker nodes with Longhorn installed

AND few RWO and RWX volumes attached with node/pod exists

AND few RWO and RWX volumes unattached

**When** Drain the worker node one by one with `Force` and `Delete Empty Dir Data` option enabled using Rancher UI.

**Then** Drain should be successful

AND Volumes should be healthy and data should be intact after drain completes

AND The volumes which were attached initially should be attached and the ones which is unattached should be unattached

AND Logs should not have any unexpected errors.


### 5. Drain operation on a multiple node using Rancher UI - Single replica of volumes

**Given**  Cluster with 1 etcd/control plane and 3 worker nodes with Longhorn installed

AND few RWO and RWX volumes with 1 replica attached with node/pod exists

AND few RWO and RWX volumes with 1 replica unattached

**When** Drain the worker node one by one, start with the node which has volume's replica

**Then** Drain should be blocked. Longhorn's pdb should prevent draining the IM from the node.

AND Volumes should be healthy and data should be intact after drain completes

AND The volumes which were attached initially should be attached and the ones which is unattached should be unattached

AND Logs should not have any unexpected errors


### 6. Longhorn volume with 50/100 Gi data

**Given**  Cluster with 1 etcd/control plane and 3 worker nodes with Longhorn installed

AND 1 volume with 50/100 Gi of data attached to a node

**When** Drain the node using Rancher UI with default value and `Delete Empty Dir Data` enabled

**Then** Drain should be successful for 2 node but should fail for last node

AND Volume data should be intact

AND Once there are 2 healthy replica rebuilt, then retry drain should be successful


### 7. Drain the attached node when backup in Longhorn is in progress

**Given**  Cluster with 1 etcd/control plane and 3 worker nodes with Longhorn installed

AND 1 RWO volume (3 replicas) attached with 10 Gi data

AND Backup is in progress

**When** Drain the attached node using Rancher UI with default value and `Delete Empty Dir Data` enabled

**Then** Drain should be successful

AND Backup should be interrupted

AND Volume's data should be intact

AND Volume should be attached once the drain finishes

AND Next backup should be successful

### 8. Drain the replica node when backup in Longhorn is in progress

**Given**  Cluster with 1 etcd/control plane and 3 worker nodes with Longhorn installed

AND 1 RWO volume (3 replicas) attached with 10 Gi data

AND Backup is in progress

**When** Drain the node on which replica responsible for backup exists using Rancher UI

**Then** Drain should be successful

AND Backup should be interrupted

AND Volume's data should be intact

AND Volume should be attached once the drain finishes

AND Next backup should be successful


### 9. Drain operation with short timeout

**Given**  Cluster with 1 etcd/control plane and 3 worker nodes with Longhorn installed

AND few RWO and RWX volumes attached with node/pod exist

AND few RWO and RWX volumes unattached

**When** Drain the worker node one by one with timeout 5 sec

**Then** Drain should be interrupted due to timeout

AND No volumes should stuck in attaching/detaching state

**When** Uncordon all the nodes one by one

**Then** All volumes should become healthy eventually

AND There shouldn't be any data loss in the volumes


### 10. Interrupt drain operation

**Given**  Cluster with 1 etcd/control plane and 3 worker nodes with Longhorn installed

AND few RWO and RWX volumes attached with node/pod exist

AND few RWO and RWX volumes unattached

**When** Trigger the drain and cancel it when drain is in progress 

**Then** Drain should be interrupted without causing data loss of volumes.

AND No volumes should stuck in attaching/detaching state


Test with Longhorn setting of 'Node Drain Policy': `allow-if-replica-is-stopped`
--------

### 1. Drain using Rancher UI - Single replica:

**Given** Single node (1 Worker) cluster with Longhorn installed

AND 1 RWO and 1 RWX volumes unattached


**When** Drain the node using Rancher UI default value and `Delete Empty Dir Data` enabled

**Then** Drain should be successful

AND Volumes should be unattached

**When** Uncordon the node after drain completes

AND data of all volumes should be intact


### 2. Repeat the below test cases:
1. Drain operation on a multiple node using Rancher UI - default value
2. Drain operation on a multiple node using Rancher UI - Force


Test with Longhorn setting of 'Node Drain Policy': `always-allow`
------

### 1. Drain using Rancher UI - Single replica:

**Given** Single node cluster with Longhorn installed

AND 1 RWO and 1 RWX volumes attached with node

**When** Drain the node using Rancher UI default value and `Delete Empty Dir Data` enabled

**Then** Drain should be successful and replica should fail.

AND Volumes should be become faulted and auto salvage should trigger which results in healthy replica and volume.

### 2. Repeat the below test cases:
1. Drain operation on a multiple node using Rancher UI - default value
2. Drain operation on a multiple node using Rancher UI - Force
