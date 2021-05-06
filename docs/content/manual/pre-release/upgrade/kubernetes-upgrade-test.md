---
title: Kubernetes upgrade test
---
We also need to cover the Kubernetes upgrade process for supported Kubernetes version, make sure pod and volumes works after a major version upgrade.

## Related Issue
https://github.com/longhorn/longhorn/issues/2566

## Test with K8s upgrade
1. Create a K8s (Immediate prior version) cluster with 3 worker nodes and 1 control plane.
2. Deploy Longhorn version (Immediate prior version) on the cluster.
3. Create a volume and attach to a pod.
4. Write data to the volume and compute the checksum.
5. Create 2nd volume and keep it detached.
6. Upgrade K8s to the latest version.
7. Observe the volume replicas get rebuilt as the instance manager goes down temporarily for the upgrade.
8. Verify all the volume should come up healthy after all the nodes are upgraded.
9. Upgrade Longhorn to the latest version and verify all the volumes become healthy eventually.
10. Verify the data in the volume.

**Known Issue**: If the volumes are still attaching and the instance managers got killed due to node went down temporarily for the upgrade, the replicas on those instance managers will be out of sync and will become error.
https://github.com/longhorn/longhorn/issues/494
 
## Test with K8s upgrade with Drain
1. Create a K8s (Immediate prior version) cluster with 3 worker nodes and 1 control plane.
2. Deploy Longhorn version (Immediate prior version) on the cluster.
3. Create a volume and attach to a pod.
4. Write data to the volume and compute the checksum.
5. Create 2nd volume and keep it detached.
6. Upgrade K8s version to latest, drain each node first before it gets upgraded. If using Rancher, upgrade with "Drain before upgrade" enabled.
7. Observe the volume replicas get rebuilt as the instance manager goes down temporarily for the upgrade.
8. Verify all the volume should come up healthy after all the nodes are upgraded.
9. Upgrade Longhorn to the latest version and verify all the volumes become healthy eventually.
10. Verify the data in the volume.

Note: In this case, no problem w.r.t attaching/detaching should be observed.

## Test with K3s upgrade.
1. Repeat the above tests with k3s cluster.
