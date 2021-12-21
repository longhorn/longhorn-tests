---
title: Restore to a new cluster
---

#### Back up the old cluster
1. Deploy the 1st cluster then install Longhorn system and Velero.
2. Deploy some workloads using Longhorn volumes then write some data:
   1. A simple pod using multiple volumes. And some volumes are using backing images.
   2. A StatefulSet.
   3. A Deployment with a RWX volume.
3. Config some recurring policies for the volumes.
4. Create backups for all volumes.
5. Create a cluster backup via Velero.
    ```bash
    velero backup create lh-cluster --exclude-resources persistentvolumes,persistentvolumeclaims,backuptargets.longhorn.io,backupvolumes.longhorn.io,backups.longhorn.io,nodes.longhorn.io,volumes.longhorn.io,engines.longhorn.io,replicas.longhorn.io,backingimagedatasources.longhorn.io,backingimagemanagers.longhorn.io,backingimages.longhorn.io,sharemanagers.longhorn.io,instancemanagers.longhorn.io,engineimages.longhorn.io
    ```
   
#### Restore to a new cluster
1. Deploy the 2nd cluster then install Velero only. You can try with different cluster config (more nodes or disks) here.
2. Restore the cluster backup. e.g.,
    ```bash
    velero restore create --from-backup lh-cluster
    ```
3. Removing all old instance manager pods and backing image manager pods from namespace `longhorn-system`. Since there is no corresponding InstanceManager CR or BackingImageManager CR for these old pods. 
4. Re-config nodes and disks for the restored Longhorn system if necessary.
5. Re-create backing images.
6. Restore all Longhorn volumes from the remote backup target.
7. Update the access mode to `ReadWriteMany` since all restored volumes are mode `ReadWriteOnce` by default.
8. Create PVCs and PVs with previous names for the restored volumes.
9. Verify all workloads work fine with correct data.

---

GitHub issue link: https://github.com/longhorn/longhorn/issues/3367
