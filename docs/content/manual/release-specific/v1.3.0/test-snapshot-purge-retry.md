---
title: Test snapshot purge retry
---

## Scenario
1. Create and attach a Longhorn volumes.
2. Write some data to the volume then create the 1st snapshot. e.g.
    ```
    dd if=/dev/urandom of=/dev/longhorn/<Longhorn volume name> bs=1M count=100
    ```
3. Try to delete the 1st snapshot. The snapshot will be marked as `Removed` then hidden on the volume detail page.
4. Write some non-overlapping data to the volume then create the 2nd snapshot. e.g.
     ```
     dd if=/dev/urandom of=/dev/longhorn/<Longhorn volume name> bs=1M count=100 seek=100
     ```
5. Re-try deleting the 1st snapshot via UI.
6. Verify snapshot purge is triggered:
   1. The 1st snapshot will be coalesced with the 2nd one, which means the size should be 200Mi. 
   2. The final snapshot name is the name of the 2nd one. 

