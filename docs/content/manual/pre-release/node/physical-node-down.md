---
title: Physical node down
---
1. One physical node down should result in the state of that node change to `Down`.
2. When using with CSI driver, one node with controller (StatefulSet/Deployment) and pod down should result in Kubernetes migrate the pod to another node, and Longhorn volume should be able to be used on that node as well. Test scenarios for this are documented [here](improve-node-failure-handling).
3. Reboot the node that the controller attached to. After reboot complete, the volume should be reattached to the node.
