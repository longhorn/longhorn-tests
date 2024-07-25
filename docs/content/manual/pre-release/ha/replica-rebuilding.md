---
title: Replica Rebuilding
---

### Basic Rebuilding test
1. Create and attach a volume.
2. Write a large amount of data to the volume.
3. Disable disk scheduling and the node scheduling for one replica. 
4. Crash the replica progress. Verify 
    1. the corresponding replica will become ERROR.
    2. the volume will keep robustness Degraded.
5. Enable the disk scheduling. Verify nothing changes.
6. Enable the node scheduling. Verify.
    1. the failed replica is reused by Longhorn.
    2. the rebuilding progress in UI page looks good.
    3. the data content is correct after rebuilding.
    4. volume r/w works fine.
7. Direct delete one replica via UI. Verify 
    1. a new replica will be replenished immediately.
    2. the rebuilding progress in UI page looks good.
    3. the data content is correct after rebuilding.
    4. volume r/w works fine.
    

### Auto balancing of replica rebuilding

#### Related issue:
https://github.com/longhorn/longhorn/issues/4105

Given Setting "replica-soft-anti-affinity" is "false"

And Setting "replica-auto-balance-disk-pressure-percentage" is "80"

And Disable node scheduling on 2 nodes. let's say node-2 & node-3

And Create multiple volumes to reach disk space percentage more 50%

When Enable node scheduling on node-2

Then Replica should rebuilt on node-2 to reduce the pressure on node-1

When Setting "replica-auto-balance-disk-pressure-percentage" is "40"

And Enable node scheduling on node-3

Then Replica should rebuilt on node-3

When Replica rebuilding is in progress, kill the replica process

Then Replica should be failed and a new replica rebuilding should get trigger

And No orphaned data should be leftover on the disk 
