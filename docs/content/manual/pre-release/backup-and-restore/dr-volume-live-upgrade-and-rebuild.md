---
title: "[#1279](https://github.com/longhorn/longhorn/issues/1279) DR volume live upgrade and rebuild"
---
1. Launch Longhorn v1.0.1.
2. Launch a pod with Longhorn volume.
3. Write data to the volume and take the 1st backup.
4. Create 2 DR volumes from the 1st backup.
5. Shutdown the pod and wait for the original volume detached.
6. Expand the original volume and wait for the expansion complete.
7. Write data to the original volume and take the 2nd backup. (Make sure the total data size is larger than the original volume size so that there is date written to the expanded part.)
8. Trigger incremental restore for the DR volumes by listing the backup volumes, and wait for restore complete.
9. Upgrade Longhorn to the latest version.
10. Crash one random replica for the 1st DR volume .
11. Verify the 1st DR volume won't rebuild replicas and keep state `Degraded`.
12. Write data to the original volume and take the 3rd backup.
13. Trigger incremental restore for the DR volumes, and wait for restore complete.
14. Do live upgrade for the 1st DR volume. This live upgrade call should fail and nothing gets changed.
15. Activate the 1st DR volume. 
16. Launch a pod for the 1st activated volume, and verify the restored data is correct.
17. Do live upgrade for the original volume and the 2nd DR volumes.
18. Crash one random replica for the 2nd DR volume.
19. Wait for the restore & rebuild complete.
20. Delete one replica for the 2nd DR volume, then activate the DR volume before the rebuild complete.
21. Verify the DR volume will be auto detached after the rebuild complete.
22. Launch a pod for the 2nd activated volume, and verify the restored data is correct.
23. Crash one replica for the 2nd activated volume.
24. Wait for the rebuild complete, then verify the volume still works fine by reading/writing more data.
