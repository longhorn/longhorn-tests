---
title: Recurring backup job interruptions
---

## Related Issue
https://github.com/longhorn/longhorn/issues/1882

## Scenario 1- ```Allow Recurring Job While Volume Is Detached``` disabled, attached pod scaled down while the recurring backup was in progress.
1. Create a volume, attach to a pod of a statefulSet, and write 800 Mi data into it.
2. Set a recurring job.
3. While the recurring job is in progress, scale down the pod to 0 of the statefulSet.
4. Volume first detached and cron job gets finished saying unable to complete the backup.
5. Verify the volume again gets auto attached to another node and cron job gets recreated.
6. Verify after backup completion, the volume gets detached.

## Scenario 2- ```Allow Recurring Job While Volume Is Detached``` enabled, attached pod scaled down while the recurring backup was in progress.
1. Enable ```Allow Recurring Job While Volume Is Detached```
2. Create a volume, attach to a pod, and write 800 Mi data into it.
3. Set a recurring job.
4. While the recurring job is in progress, scale down the pod to 0.
5. Volume first detached and cron job gets completed saying unable to complete the backup.
6. Verify volume again gets auto attached to another node and cron job gets recreated.
7. Verify after backup completion, the volume gets detached.

## Scenario 3- Cron job and volume attached to the same node, Node is powered down and volume detached manually.
1. Enable ```Allow Recurring Job While Volume Is Detached```
2. Attach a volume to pod of a statefulSet, write data into it and set a recurring backup.
3. Detach from the pod by scaling down the statefulSet.
4. The attached node to volume is power down when the recurring job backup was in progress.
5. The volume is manually detached while the cron job remains in unknown state.
6. The cron job remains in unknown state for about 7 mins and then another pod gets created.
7. Verify the volume get attached to another node and once the job is completed, volume gets detached.

## Scenario 4- Cron job and volume attached to different node, Node is powered down.
1. Enable ```Allow Recurring Job While Volume Is Detached```
2. Attach a volume to pod of a statefulSet, write data into it and set a recurring backup.
3. Detach from the pod by scaling down the statefulSet.
4. The attached node to volume is power down when the recurring job backup was in progress.
5. Another cron job pod gets created with logs in the previous pod as below.
    ```
    time="2020-11-09T07:39:10Z" level=info msg="Automatically attach volume volume-test-2 to node node-1"
    time="2020-11-09T07:39:12Z" level=info msg="Volume volume-test-2 is in state attached"
    time="2020-11-09T07:39:12Z" level=info msg="Running recurring backup for volume volume-test-2"
    time="2020-11-09T07:39:22Z" level=debug msg="Creating backup , current progress 0"
    time="2020-11-09T07:39:27Z" level=debug msg="Creating backup , current progress 4"
    time="2020-11-09T07:40:42Z" level=info msg="Automatically detach the volume volume-test-2"
    ```
6. Verify the volume get attached to another node and once the job is completed, volume gets detached.

## Scenario 5- Cron job and volume attached to the same node, Node is restarted.
1. Enable ```Allow Recurring Job While Volume Is Detached```
2. Attach a volume to pod of a statefulSet, write data into it and set a recurring backup.
3. Detach from the pod by scaling down the statefulSet.
4. The attached node to volume is power down when the recurring job backup was in progress.
5. The volume is manually detached while the cron job remains in unknown state.
6. Power on the node.
7. The cron job which was stuck in unknown state get removed and new cron job get recreated.
8. Verify the volume get attached to another node and the backup job is completed.

## Scenario 6- Cron job and volume attached to the same/different node, Node is powered down and ```Pod Deletion Policy When Node is Down```is set as ```delete-both-statefulset-and-deployment-pod```
1. Enable ```Allow Recurring Job While Volume Is Detached```
2. Attach a volume to pod of a statefulSet, write data into it and set a recurring backup.
3. The attached node to volume is power down when the recurring job backup was in progress.
4. The cron job (if on the same node) and the pod remains in unknown state for about 7 mins and then another pod gets created for the cron job (if on the same node) and statefulSet. If cron job is on another node, it fails to complete the backup and tries to create new job to complete backup which fails with error ```level=fatal msg="Error taking snapshot: failed to complete backupAndCleanup for pvc-4feb233e-9503-4d4b-8cda-a5bdf005b146: could not get volume-head for volume pvc-4feb233e-9503-4d4b-8cda-a5bdf005b146: Bad response statusCode [500]. Status [500 Internal Server Error]. Body: [message=fail to get snapshot: cannot get client for volume pvc-4feb233e-9503-4d4b-8cda-a5bdf005b146: engine is not running, code=Server Error, detail=] from [http://longhorn-backend:9500/v1/volumes/pvc-4feb233e-9503-4d4b-8cda-a5bdf005b146?action=snapshotGet]"```
5. After 7 min the cron job takes over the creation of another pod of stateful set and the volume gets auto attached to another node, completes the backup and gets detached.
6. Verify the statefulSet pod successfully reattaches to the volume after sometime.
