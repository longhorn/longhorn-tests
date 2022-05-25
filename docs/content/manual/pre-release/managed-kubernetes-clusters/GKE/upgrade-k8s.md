---
title: "[Upgrade K8s](https://longhorn.io/docs/1.3.0/advanced-resources/support-managed-k8s-service/upgrade-k8s-on-gke/)"
---
1. Create GKE cluster with 3 nodes and install Longhorn.
2. Create [deployment](https://github.com/longhorn/longhorn/blob/master/examples/deployment.yaml) and write some data to it.
3. In Longhorn, set `replica-replenishment-wait-interval` to `0`.
4. See [Upgrading the cluster](https://cloud.google.com/kubernetes-engine/docs/how-to/upgrading-a-cluster#upgrading_the_cluster) and [Upgrading node pools](https://cloud.google.com/kubernetes-engine/docs/how-to/upgrading-a-cluster#upgrading-nodes) for instructions.
5. Check the deployment in step 2 still running and data exist.