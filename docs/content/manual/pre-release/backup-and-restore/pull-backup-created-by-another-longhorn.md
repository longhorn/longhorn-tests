---
title: "[#4637](https://github.com/longhorn/longhorn/issues/4637) pull backup created by another Longhorn system"
---
1. Prepare 2 k8s clusters: cluster A and cluster B. 
2. Install previous version of Longhorn which doesn't include this fix e.g v1.3.1, v1.2.5 on cluster A.
3. Install the release version of Longhorn on cluster B.
4. Set the same backup target on both cluster A and cluster B.
5. Create volume, write some data, and take backup on cluster A.
6. Wait for backup target polling update on cluster B.
7. Make sure the backup created by cluster A can be pulled on cluster B.
8. Restore the pulled backup and verify the data on cluster B.
9. Repeat the test with both clusters installed the release version of Longhorn.