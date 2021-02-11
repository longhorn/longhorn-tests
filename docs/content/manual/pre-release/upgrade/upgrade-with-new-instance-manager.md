---
title: Test System Upgrade with New Instance Manager
---

1. Prepare 3 sets of longhorn-manager and longhorn-instance-manager images.
2. Deploy Longhorn with the 1st set of images.
3. Set `Guaranteed Engine Manager CPU` and `Guaranteed Replica Manager CPU` to 15 and 24, respectively. 
   Then wait for the instance manager recreation.
4. Create and attach a volume to a node (node1).
5. Upgrade the Longhorn system with the 2nd set of images. 
   Verify the CPU requests in the pods of both instance managers match the settings. 
6. Create and attach one more volume to node1.
7. Upgrade the Longhorn system with the 3rd set of images.
8. Verify the pods of the 3rd instance manager cannot be launched on node1 since there is no available CPU for the allocation.
9. Detach the volume in the 1st instance manager pod. 
   Verify the related instance manager pods will be cleaned up and the new instance manager pod can be launched on node1.
