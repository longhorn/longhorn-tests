---
title: Test cases to reproduce attachment-detachment issues
---
**Prerequisite:** Have an environment with just with 2 worker nodes or taint 1 out of 3 worker node to be `NoExecute` & `NoSchedule`.
This will serve as a constrained fallback and limited source of recovery in the event of failure.   


#### 1. Kill the engines and instance manager repeatedly 
**Given** 1 RWO and 1 RWX volume is attached to a pod.
And Both the volumes have 2 replicas.
And Random data is continuously being written to the volume using command `dd if=/dev/urandom of=file1 count=100 bs=1M conv=fsync status=progress oflag=direct,sync`

**When** One replica rebuilding is triggered by crashing the IM
AND Immediately IM associated with another replica is crashed
AND After crashing IMs, detaching of Volume is tried either by pod deletion or using Longhorn UI    

**Then** Volume should not stuck in attaching-detaching loop

**When** Volume is detached and manually attached again.
And Engine running on the node where is volume is attached in killed

**Then** Volume should recover once the engine is back online.

#### 2. Illegal values in Volume/Snap.meta
**Given** 1 RWO and 1 RWX volume is attached to a pod.
And Both the volumes have 2 replicas.

**When** Some random values are set in the Volume/snap meta file
And If replica rebuilding is triggered and the IM associated with another replica is also crashed

**Then** Volume should not stuck in attaching-detaching loop


#### 3. Deletion of Volume/Snap.meta
**Given** 1 RWO and 1 RWX volume is attached to a pod.
And Both the volumes have 2 replicas.

**When** The Volume & snap meta files are deleted one by one.
And If replica rebuilding is triggered and the IM associated with another replica is also crashed

**Then** Volume should not stuck in attaching-detaching loop

#### 4. Failed replica tries to rebuild from other just crashed replica - https://github.com/longhorn/longhorn/issues/4212
**Given** 1 RWO and 1 RWX volume is attached to a pod.
And Both the volumes have 2 replicas.
And Random data is continuously being written to the volume using command `dd if=/dev/urandom of=file1 count=100 bs=1M conv=fsync status=progress oflag=direct,sync`

**When** One replica rebuilding is triggered by crashing the IM
AND Immediately IM associated with another replica is crashed

**Then** Volume should not stuck in attaching-detaching loop.

#### 5. Volume attachment Modification/deletion

**Given** A deployment and statefulSet are created with same name and attached to Longhorn Volume.
AND Some data is written and their md5sum is computed

**When** The statefulSet and Deployment are deleted without deleting the volumes
And Same named new statefulSet and Deployment are created with new PVCs.
And Before above deployed workload could attach to volumes, attached node is rebooted

**Then** After node reboot completion, volumes should reflect right status.
And the newly created deployment and statefulSet should get attached to the volumes.

**When** The volume attachments of above workloads are deleted.
And above workloads are deleted and recreated immediately.

**Then** No multi attach or other errors should be observed.

#### 6. Use monitoring/word press/db workloads
**Given** Monitoring and word press and any other db related workload are deployed in the system
And All the volumes have 2 replicas.
And Random data is continuously being written to the volume using command `dd if=/dev/urandom of=file1 count=100 bs=1M conv=fsync status=progress oflag=direct,sync`

**When** One replica rebuilding is triggered by crashing the IM
AND Immediately IM associated with another replica is crashed

**Then** Volume should not stuck in attaching-detaching loop.
 