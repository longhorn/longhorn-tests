---
title: Degraded availability with added nodes
---
https://github.com/longhorn/longhorn/issues/1701

#### Volume creation using UI with degraded availability and added node
Start with one node cluster.

1. Create a Deployment Pod with a volume and three replicas.
    1. After the volume is attached, `scheduling error` should be seen from the UI. But no functional impact.
1. Write data to the Pod.
1. Scale down the deployment to 0 to detach the volume.
    1. `scheduling error` should be gone.
1. Scale up the deployment back to 1 verify the data.
    1. `scheduling error` should be seen again from the UI.
1. Add another node to the cluster.
    1. Volume should start rebuilding on the second node soon.
1. Once the rebuild completed, scale down and back up the deployment to verify the data.
1. And the third node to the cluster.
   1. Volume should start rebuilding on the third node soon.
   1. Once the rebuilding starts, the `scheduling error` should be gone.
1. Scale down and back the deployment to verify the data.
