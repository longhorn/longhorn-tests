---
title: Recurring backup job interruptions
---

## Related Issue
https://github.com/longhorn/longhorn/issues/1882

## Scenario 1- ```Allow Recurring Job While Volume Is Detached``` disabled, attached pod scaled down while the recurring backup was in progress.
1. Create a volume, attach to a pod of a statefulSet, and write 800 Mi data into it.
2. Set a recurring job.
3. While the recurring job is in progress, scale down the pod to 0 of the statefulSet.
4. Verify after backup completion, the volume gets detached.
5. Verify volume not gets attached during the next scheduled recurring backup time.

## Scenario 2- ```Allow Recurring Job While Volume Is Detached``` enabled, attached pod scaled down while the recurring backup was in progress.
1. Enable ```Allow Recurring Job While Volume Is Detached```
2. Create a volume, attach to a pod, and write 800 Mi data into it.
3. Set a recurring job.
4. While the recurring job is in progress, scale down the pod to 0.
5. Verify after backup completion, the volume gets detached.
6. Verify volume again gets attached when next round of recurring job started.
7. Verify after backup completion, the volume gets detached.

## Scenario 3- Cron job and volume attached to the same node, Node is powered down and volume detached.
1. Enable ```Allow Recurring Job While Volume Is Detached```
2. Attach a volume to pod of a statefulSet, write data into it and set a recurring backup.
3. Detach from the pod by scaling down the statefulSet.
4. The attached node to volume is powered down when the recurring job backup was in progress.
5. The volume becomes detached due to the node power off, while the cron job pod remains in the Running state.
6. The cron job pod remains in Running state for about 7 mins and then another pod gets created.
7. Verify the volume get attached to another node and once the job is completed, volume gets detached.

## Scenario 4- Cron job and volume attached to the same node, Node is restarted.
1. Enable ```Allow Recurring Job While Volume Is Detached```
2. Attach a volume to pod of a statefulSet, write data into it and set a recurring backup.
3. Detach from the pod by scaling down the statefulSet.
4. The attached node to volume is powered down when the recurring job backup was in progress.
5. The volume becomes detached due to the node power off, while the cron job pod remains in the Running state.
6. Power on the node.
7. Verify the volume get attached to different node and the backup job is completed.

## Scenario 5- Cron job and volume attached to the same/different node, Node is powered down and ```Pod Deletion Policy When Node is Down```is set as ```delete-both-statefulset-and-deployment-pod```
1. Set ```node-down-pod-deletion-policy``` to ```delete-both-statefulset-and-deployment-pod```
2. Enable ```Allow Recurring Job While Volume Is Detached```
3. Attach a volume to pod of a statefulSet, write data into it and set a recurring backup.
4. The attached node to volume is powered down when the recurring job backup was in progress.
5. The backup is in error state.
6. After 7 min the cron job takes over the creation of another pod of stateful set and the volume gets auto attached to another node, completes the backup and gets detached.
7. Verify the statefulSet pod successfully reattaches to the volume after sometime.
