---
title: Replica Rebuilding
---
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
 