---
title: Physical node down
---
1. One physical node down should result in the state of that node change to `Down`.
2. When using with CSI driver, one node with controller (StatefulSet/Deployment) and pod down should result in Kubernetes migrate the pod to another node, and Longhorn volume should be able to be used on that node as well. Test scenarios for this are documented [here](../../../node/improve-node-failure-handling/).

   > **Note:**
   > 
   > In this case, RWX should be excluded.  
   >
   > Ref: https://github.com/longhorn/longhorn/issues/5900#issuecomment-1541360552