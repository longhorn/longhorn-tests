---
title: Recover Longhorn volumes after Rancher cluster restore
---

Notice that the behaviors will be different if the cluster node roles are different. e.g., A cluster contains 1 dedicated master node + 3 worker node is different from a cluster contains 3 nodes which are both master and worker.
This test may need to be validated for both kind of cluster.

1. Launch a Longhorn system. Deploy one more compatible engine image.
2. Prepare some volumes with workloads:
    1. Create and attach volume A via UI. Write some data and do some snapshot operations. (Validate 1 case: The volume deleted after the cluster snapshot will be restored but is invalid)
    2. Deploy a single pod with volume B. Write some data, do some snapshot operations, and create some backups. (Validate 3 cases: <1> data modification won't crash the whole volume; <2> backup info will be resynced; <3> users need to manual restart the single pod)
    3. Deploy a StatefulSet with volume C. Write some data and do some snapshot operations. (Validate 1 case: Users need to manually recover the volume if all existing replicas are replaced by new replicas)
    4. Deploy a StatefulSet with volume D. Write some data and do some snapshot operations. (Validate 2 cases: <1> volume can be recovered automatically if some replicas are removed and some new replicas are replenished; <2> snapshot info will be resynced;)
    5. Deploy a Deployment with volume E. Write some data and do some snapshot operations. (Validate 4 cases: <1> engine upgrade; <2> offline expansion)
3. Create a cluster snapshot via Rancher.
4. Do the followings before the restore:
    1. Delete volume A.
    2. Write more data to volume B and create more backups.
    3. Remove all current replicas one by one for volume C. Then all replicas of volume C are new replicas.
    4. Remove some replicas for volume D. Do snapshot creation, deletion, and revert.
    5. Scale down the workload. Upgrade volume E from the default image to another engine image. And do expansion.
    6. Create and attach volume F via UI. Write some data and do some snapshot operations. (Validate 1 case: Users need to manuall recover the volume if it's created after the cluster snapshot)
5. Restore the cluster. 
6. Check the followings according to the doc:
    1. Volume A is back. But there is no data in it. And users can re-delete it.
    2. Volume B can be reattached or keep attached with correct data. The backup info of volume B is resynced when the volume is reattahed. The pod can use the volume after restart.
    3. All old removed replicas are back and all newly rebuilt replicas in step4-3 disappear for volume C. There is no data in volume C. The data directories of the disappeared replicas are still on the node. Hence the data are be recovered by exporting a single replica volume.
    4. The old removed replicas are back and the newly rebuilt replicas in step4-4 disappear for volume D. The restored replicas will become failed then get rebuilt with correct data. The data directories of the disappeared replicas are still on the node.
    5. Volume E re-uses the default engine image, and gets stuck in shrinking the expanded size to the original size. By re-scaling down the workload, re-upgrade and re-expand the volume. The volume can work fine then.
    6. Volume F will disappear. The data directories of the disappeared replicas are still on the node. Hence the data are be recovered by exporting a single replica volume.

The github issue link: https://github.com/longhorn/longhorn/issues/2228
