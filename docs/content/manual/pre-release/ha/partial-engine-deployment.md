---
title: Longhorn with engine is not deployed on all the nodes
---

## Related Issue
https://github.com/longhorn/longhorn/issues/2081

## Scenarios:
### Case 1: Test volume operations when engine image DaemonSet is miss scheduled 
1. Install Longhorn in a 3-node cluster: `node-1`, `node-2`, `node-3`
1. Create a volume, `vol-1`, of 3 replicas
1. Create another volume, `vol-2`, of 3 replicas
1. Taint `node-1` with the taint: `key=value:NoSchedule`
1. Check that all functions (attach, detach, snapshot, backup, expand, restore, creating DR volume, ... ) are working ok for `vol-1`

### Case 2: Test volume operations engine image DaemonSet is not fully deployed
1. Continue from case 1
1. Attach `vol-1` to `node-1`. Change the number of replicas of `vol-1` to 2. Delete the replica on `node-1`
1. Delete the pod on `node-1` of the engine image DaemonSet. Or delete the engine image DaemonSet and wait for Longhorn to automatically recreates it. 
1. Notice that the engine image CR state become deploying
1. Verify that functions (detach, snapshot, backup) are working ok for `vol-1`
1. Detach `vol-1`
1. Verify that Longhorn cannot attach `vol-1` to `node-1` since there is no engine image on `node-1`
1. Check that all functions (attach to other nodes, detach, snapshot, backup, expand, restore, creating DR volume, ... ) are working ok for `vol-1`
1. Verify that `vol-2` cannot be attached to any nodes because one of its replica is sitting on the `node-1` which doesn't have the engine image

### Case 3: Test engine upgrade when engine image DaemonSet is not fully deployed
1. Continue from case 2
1. Deploy a new engine image, `newEI`
1. Verify that you can upgrade `vol-1` to `newEI` (both live and offline upgrade)
1. Verify that you can not upgrade `vol-2` to `newEI`
