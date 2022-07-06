---
title: Degraded availability with added nodes
---

#### Volume creation using UI with degraded availability and added node

##### Related Issue:
- https://github.com/longhorn/longhorn/issues/1701

##### Prerequisites:
- Start with 1 node cluster.
- Double check if "Allow Volume Creation with Degraded Availability" is ticked or return **true** with following command:
    - `kubectl get settings.longhorn.io/allow-volume-creation-with-degraded-availability -n longhorn-system`

##### Steps:
1. Create a Deployment Pod with a volume and three replicas.
    1. After the volume is attached, on Volume page it should be displayed as `Degraded`
    1. Hover the crusor to the red circle exclamation mark, the tooltip will says, "The volume cannot be scheduled".
    1. Click into the volume detail page it will display `Scheduling Failure` but the volume remain fuctional as expected.
1. Write data to the Pod.
1. Scale down the deployment to 0 to detach the volume.
    1. Volume return to `Detached` state.
    1. Both `Degraded` and `Scheduling Failure` should be gone.
1. Scale up the deployment back to 1 verify the data.
    1. `Scheduling Failure` should be seen again from the UI.
1. Add another node to the cluster.
    1. Volume should start rebuilding on the second node soon.
1. Once the rebuild completed, scale down and back up the deployment to verify the data.
1. And the third node to the cluster.
   1. Volume should start rebuilding on the third node soon.
   1. Once the rebuilding starts, the `Scheduling Failure` should be gone.
1. Scale down and back the deployment to verify the data.
