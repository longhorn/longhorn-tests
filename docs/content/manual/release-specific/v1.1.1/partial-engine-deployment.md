---
title: Longhorn with engine is not deployed on all the nodes
---

## Related Issue
https://github.com/longhorn/longhorn/issues/2081

## Scenarios:
### Case 1: Test volume operations when some of the engine image DaemonSet pods are miss scheduled 
1. Install Longhorn in a 3-node cluster: `node-1`, `node-2`, `node-3`
1. Create a volume, `vol-1`, of 3 replicas
1. Create another volume, `vol-2`, of 3 replicas
1. Taint `node-1` with the taint: `key=value:NoSchedule`
1. Check that all functions (attach, detach, snapshot, backup, expand, restore, creating DR volume, ... ) are working ok for `vol-1`

### Case 2: Test volume operations when some of engine image DaemonSet pods are not fully deployed
1. Continue from case 1
1. Attach `vol-1` to `node-1`. Change the number of replicas of `vol-1` to 2. Delete the replica on `node-1`
1. Delete the pod on `node-1` of the engine image DaemonSet. Or delete the engine image DaemonSet and wait for Longhorn to automatically recreates it. 
1. Notice that the engine image CR state become deploying
1. Verify that functions (detach, snapshot, backup) are working ok for `vol-1`
1. Detach `vol-1`
1. Verify that Longhorn cannot attach `vol-1` to `node-1` since there is no engine image on `node-1`
1. Check that all functions (attach to other nodes, detach, snapshot, backup, expand, restore, creating DR volume, ... ) are working ok for `vol-1`
1. Verify that `vol-2` cannot be attached to any nodes because one of its replica is sitting on the `node-1` which doesn't have the engine image

### Case 3: Test engine upgrade when some of the engine image DaemonSet pods are not fully deployed
1. Continue from case 2
1. Deploy a new engine image, `newEI`
1. Verify that you can upgrade `vol-1` to `newEI` (both live and offline upgrade)
1. Verify that you can not upgrade `vol-2` to `newEI`

### Case 4: Test replicas scheduling when some of the engine image DaemonSet pods are not fully deployed
1. Continue from case 2
1. Create a new volume, `vol-3`, with 2 replicas
1. Verify that replicas of `vol-3` are on `node-2` and `node-3`
1. Check that all functions (attach, detach, snapshot, backup, expand, restore, creating DR volume,... ) are working ok for `vol-3`

### Case 5: Test Longhorn upgrade when some of the engine image DaemonSet pods are not fully deployed
1. Continue from case 3
1. Upgrade Longhorn to a new version
1. Verify that the upgrade is not blocked. Longhorn successfully upgrades to the new version using the same default engine image even though the default engine image is not fully deployed.

### Case 6: Test `auto upgrade engine` feature when some of the engine image DaemonSet pods are not fully deployed
With the engine image is missing on `node-1`, we need  to re-verify the manual test for feature `auto upgrade engine` https://github.com/longhorn/longhorn-tests/blob/master/docs/content/manual/pre-release/upgrade/auto-upgrade-engine.md
Make sure that Longhorn automatically upgrades engine image for volumes that are either:
1. in the detached state, and has the new engine image on all replicas' node
1. in the attached state, and has the new engine image on all replicas' node and attaching node

### Case 7: Test `auto attach volume for recurring backup job` feature when some of the engine image DaemonSet pods are not fully deployed
Verify that the recurring backup job only attaches the volume to a node that has the engine image deployed. 

### Case 8: Test DR, restoring, expanding volumes  when some of the engine image DaemonSet pods are not fully deployed
1. Create a DR volume of 2 replicas. Verify that 2 replicas are on `node-2` and `node-3` and the DR volume is attached to either `node-2` or `node-3`. Let's say it is attached to `node-2`
1. Taint `node-2` with the taint: `key=value:NoSchedule`
1. Delete the pod of engine image DeamonSet on `node-2`. Now, the engine image is missing on `node-1` and `node-2`
1. Verify that the owner ID of the DR volume temporarily moves to `node-3`. And the DR volume will be auto-attached to `node-3`.
1. Restore a volume from backupstore. Set the replica to 1. Verify that replica is on `node-3` and the volume successfully restored.
1. Expand the restored volume in the previous step. Verify that the expansion is ok

### Case 9: Test reusing failed replica when some of the engine image DaemonSet pods are not fully deployed
Verify that Longhorn doesn't reuse the failed replicas on nodes that don't have engine image deployed
