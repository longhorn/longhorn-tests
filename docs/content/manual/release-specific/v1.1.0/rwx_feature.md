---
title: Test Read Write Many Feature
---

# Prerequisite:
1. Set up a Cluster of 4 nodes (1 etc/control plane and 3 workers)
2. Deploy Latest Longhorn-master

# Create StatefulSet/Deployment with single pod with volume attached in RWX mode.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 1 pod.
3. Verify that a PVC, ShareManger pod, CRD and volume in Longhorn get created.
4. Verify share-manager pod come up healthy.
5. Verify there is directory with the name of PVC exists in the ShareManager mount point.
Example - `ls /export/pvc-8c3481c7-4127-47c3-b840-5f41dc9d603e`
6. Write some data in the pod and verify the same data reflects in the ShareManager.
7. Verify the longhorn volume, it should reflect the correct size.

# Create StatefulSet/Deployment with more than 1 pod with volume attached in RWX mode.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Verify that 2 volumes in Longhorn get created.
4. Verify there is directory with the name of PVC exists in the ShareManager mount point i.e. `export`
5. Verify that Longhorn UI shows all the pods name attached to the volume.
5. Write some data in all the pod and verify all the data reflects in the ShareManager.
6. Verify the longhorn volume, it should reflect the correct size.

# Create StatefulSet/Deployment with the existing PVC of a RWX volume.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 1 pod.
3. Verify that a PVC, ShareManger pod, CRD and volume in Longhorn get created.
5. Write some data in the pod and verify the same data reflects in the ShareManager.
6. Create another StatefulSet/Deployment using the above created PVC.
7. Write some data in the new pod, the same should be reflected in the ShareManager pod.
8. Verify the longhorn volume, it should reflect the correct size.

# Scale up StatefulSet/Deployment with one pod attached with volume in RWX mode.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 1 pod.
4. Write some data in the pod and verify the same data reflects in the ShareManager.
5. Scale up the StatefulSet/Deployment.
6. Verify a new volume gets created.
7. Write some data in the new pod, the same should be reflected in the ShareManager pod.
8. Verify the longhorn volume, it should reflect the correct size.

# Scale down StatefulSet/Deployment attached with volume in RWX mode to zero.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 1 pod.
3. Write some data in the pod and verify the same data reflects in the ShareManager.
4. Scale down the StatefulSet/Deployment to zero
5. Verify the ShareManager pod gets deleted.
6. Verify the volume should be in detached state.
7. Create a new StatefulSet/Deployment with the existing PVC.
8. Verify the ShareManager should get created and volume should become attached.
9. Verify the data.
10. Delete the newly created StatefulSet/Deployment.
11. Verify the ShareManager pod gets deleted again.
12. Scale up the first StatefulSet/Deployment.
13. Verify the ShareManager should get created and volume should become attached.
14. Verify the data.

# Delete the Workload StatefulSet/Deployment attached with RWX volume.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod and verify the same data reflects in the ShareManager.
4. Delete the workload.
5. Verify the ShareManager pod gets deleted but the CRD should not be deleted.
6. Verify the ShareManager.status.state == "stopped". `kubectl get ShareManager -n longhorn-system`
6. Verify the volume should be in detached state.
7. Create another StatefulSet with existing PVC.
8. Verify the ShareManager should get created and volume should become attached.
9. Verify the data.

# Take snapshot and backup of a RWX volume in Longhorn.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Take a snapshot and a backup.
5. Write some more data into the pod.
6. Revert to snapshot 1 and verify the data.

# Restore a backup taken from a RWX volume in Longhorn.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Take a backup of the RWX volume.
5. Restore from the backup and select access mode as `rwx`.
6. Verify the restored volume has `volume.spec.accessMode` as `rwx`.
7. Create PV/PVC with `accessMode` as `rwx` for restored volume or create PV/PVC using Longhorn UI.
8. Attach a pod to the PVC created and verify the data.

# Restore an RWX backup into an RWO volume.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Take a backup of the RWX volume.
5. Restore from the backup and select access mode as `rwo`.
6. Verify the restored volume has `volume.spec.accessMode` as `rwo`.
7. Create a PV and PVC with `accessMode` as `rwo` for the restored volume or create them using Longhorn UI.
9. Attach a pod to the PVC and verify the data.
10. Try to attach the PVC to another pod on another node, user should get `multi attach` error.

# Restore an RWO backup into an RWX volume.
1. Create a PVC with RWO mode using longhorn class by selecting the option `read write once`.
2. Attach the PVC to a StatefulSet/Deployment with 1 pod.
3. Write some data in the pod.
4. Take a backup of the RWO volume.
5. Restore from the backup and select access mode as `rwx`.
6. Create a PV and PVC with `accessMode` as `rwx` for the restored volume or create them using Longhorn UI.
7. Verify the restored volume has `volume.spec.accessMode` as `rwx` now.
9. Attach a pod to the PVC and verify the data.
10. Attach more pods to the PVC, verify the volume is accessible from multiple pods.

# Create PV and PVC using Longhorn UI for RWX/RWO volume
1. Create an RWX volume using Longhorn UI.
2. Select the volume and create PV/PVC.
3. Verify the PV and PVC are created with `rwx` access mode.
4. Create an RWO volume using Longhorn UI.
5. Select the volume and create PV/PVC.
6. Verify the PV and PVC are created with `rwo` access mode.

# Create RWX DR volume of a RWX volume in Longhorn.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Take a backup of the volume.
5. Create a DR volume of the backup by selecting `rwx` in access mode.
6. Write more data in the pods and take more backups.
7. Verify the DR volume is getting synced with latest backup.
8. Activate the DR volume, attach it to multiple pods and verify the data.

# Create RWO DR volume of a RWX volume in Longhorn.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Take a backup of the volume.
5. Create a DR volume of the backup by selecting `rwo` in access mode.
6. Write more data in the pods and take more backups.
7. Verify the DR volume is getting synced with latest backup.
8. Activate the DR volume, attach it to a pod and verify the data.
9. Try to attach it to multiple pods, it should show `multi attach error`.

# Create RWX DR volume of a RWO volume in Longhorn.
1. Create a PVC with RWO mode using longhorn class by selecting the option `read write once`.
2. Attach the PVC to a StatefulSet/Deployment with 1 pod.
3. Write some data in the pod.
4. Take a backup of the volume.
5. Create a DR volume of the backup by selecting `rwx` in access mode.
6. Write more data in the pod and take more backups.
7. Verify the DR volume is getting synced with latest backup.
8. Activate the DR volume, attach it to multiple pods and verify the data.

# Expand the RWX volume.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Scale down the StatefulSet/Deployment.
4. Once the volume is detached, expand the volume.
5. Scale up the StatefulSet/Deployment and verify that user is able to write data in the expanded volume.
6. Verify the new size of the volume (same approach as in writing the data).

# Recurring Backup/Snapshot with RWX volume.
Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Schedule a recurring backup/Snapshot.
5. Verify the recurring jobs are getting created and is taking backup/snapshot successfully.

# Deletion of the replica of a Longhorn RWX volume.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Delete one of the replica and verify that the rebuild of replica is working fine.

# Data locality with RWX volume.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Enable `Data-locality`
5. Disable `Node soft anti-affinity`.
6. Disable the node where the volume is attached for some time.
7. Wait for replica to be rebuilt on another node.
8. Enable the node scheduling and verify a replica gets rebuilt on the attached node.

# Node eviction with RWX volume.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Do a node eviction and verify the data.

# Auto salvage feature on an RWX volume.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Crash all the replicas and verify the auto-salvage works fine.

# RWX volume with `Allow Recurring Job While Volume Is Detached` enabled.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Set a recurring backup and scale down all the pods.
5. Verify the volume get attached at scheduled time and backup/snapshot get created.

# RWX volume with Toleration.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Detach the volume by scaling down the StatefulSet/Deployment to 0.
5. Set some Toleration.
6. Wait for the Longhorn pods to be redeployed.
7. Scale up the StatefulSet/Deployment back to 2.
8. Verify the ShareManager pods have the toleration and annotation updated.

# Detach/Delete operation on an RWX volume.
1. Detach action on the RWX volume should not work. A detach will temporarily remove the volume then the share manager controller will try to attach it again and restart a new share manager pod.
2. On deletion of the RWX volume, the ShareManager CRDs should also get deleted.

# Crash instance e manager of the RWX volume
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Crash the instance manager.
5. On crashing the IM, the ShareManager pods should be immediately redeployed.
5. Based on the setting `Automatically Delete Workload Pod when The Volume Is Detached Unexpectedly`, the workload pods will get redeployed.
6. On recreating on workload pods, the volume should get attached successfully.
7. If `Automatically Delete Workload Pod when The Volume Is Detached Unexpectedly` is disabled, user should see I/O error on the mounted point.

# Reboot the ShareManager and workload node
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Reboot the ShareManager node.
5. The ShareManager pod should move to another node.
6. As the instance e manager is on the same node and based on setting `Automatically Delete Workload Pod when The Volume Is Detached Unexpectedly`, the workload should be redeployed and volume should be available to user.
7. Reboot the workload node.
8. On restart on the node, pods should get attached to the volume. Verify the data.

# Power down the ShareManager and workload node.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Power down the ShareManager node.
5. The ShareManager pod should move to another node.
6. As the instance manager is on the same node and based on the setting `Automatically Delete Workload Pod when The Volume Is Detached Unexpectedly`, the workload should be redeployed and volume should be available to user.
7. Power down the workload node.
8. The workload pods should move to another node based on `Pod Deletion Policy When Node is Down` setting.
9. Once the pods are up, they should get attached to the volume. Verify the data.

# Kill the nfs process in the ShareManager
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Kill the NFS server in the ShareManager pod.
5. The ShareManager pod should go into terminate then restarted by the ShareManager controller. The ganesha service pid can be seen by `cat /var/run/ganesha.pid`.
6. The workload pods should be restarted.
7. Verify the data in workload pods.

# Delete the ShareManager CRD.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Delete the ShareManager CRD.
5. A new ShareManager CRD should be created.
6. Workloads should be restarted based on the setting `Automatically Delete Workload Pod when The Volume Is Detached Unexpectedly`.

# Delete the ShareManager pod.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Delete the ShareManager pod.
5. A new ShareManager pod should be immediately created.

# Drain the ShareManager node.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Drain the ShareManager pod node.
5. The volume should get detached first, then the shareManager pod should move to another node and Volume should get reattached.

# Disk full on the ShareManager node.
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod and make the disk almost full.
4. Verify the RWX volume is not failed.
5. Verify the creation of snapshot/backup.
6. Try to write more data, and the it should error out `no space left`.

# Scheduling failure with RWX volume.
1. Disable 1 node. Enable `Allow Volume Creation with Degraded Availability`.
2. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
3. Attach the PVC to a StatefulSet/Deployment with 1 pod.
4. Verify the RWX volume gets created with degraded state.
5. Write some data in the pod.
6. Enable the node and the volume should become healthy.
7. Disable 1 node again and disable `Allow Volume Creation with Degraded Availability`.
8. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
9. Verify volume fails to schedule.

# Add a node in the cluster.
1. Add a node in the cluster.
2. Create multiple statefulSet/deployment with RWX volume.
3. Verify that the ShareManager pod is able to scheduled on the new node.

# Delete a node from the cluster
1. Create a PVC with RWX mode using longhorn class by selecting the option `read write many`.
2. Attach the PVC to a StatefulSet/Deployment with 2 pods.
3. Write some data in the pod.
4. Delete the ShareManager node from the cluster.
5. Verify the ShareManager pod move to new node and volume continues to be accessible.

# RWX on SeLinux enabled cluster
1. Verify the RWX feature with a Se Linux enabled cluster.

# RWX with Linux/SLES OS
1. Verify the RWX feature with a cluster of Linux and SLES OS.

# RWX with K3s set up
1. Set up a K3s cluster and verify the RWX feature.

# RWX in Air gap set up.
1. Set up an Air gap set up and verify the RWX feature.

# RWX in PSP enabled set up.
1. Enable PSP in a cluster and verify the RWX feature.
