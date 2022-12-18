---
title: Checksum enabled large volume with multiple rebuilding
---

1. Create a 50 Gi volume. write around 30 Gi data into it.
1. Enable the setting `Snapshot Data Integrity`. 
1. Keep writing in the volume continuously using dd command like `while true; do dd if=/dev/urandom of=t1 bs=512 count=1000 conv=fsync status=progress && rm t1; done`.
1. Create a recurring job of backup for every 15 min.
1. Delete a replica and wait for the replica rebuilding.
1. Compare the performance of replica rebuilding from previous Longhorn version without the setting `Snapshot Data Integrity`.
1. Verify the Longhorn manager logs, no abnormal logs should be present.
1. Repeat the steps of deletion of the replica and verify Longhorn doesn't take more time than the first iteration.  
