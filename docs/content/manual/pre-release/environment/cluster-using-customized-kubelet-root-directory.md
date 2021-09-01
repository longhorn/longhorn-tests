---
title: Cluster using customize kubelet root directory
---

1. Set up a cluster using a customized kubelet root directory. 
   e.g., launching k3s `k3s server --kubelet-arg "root-dir=/var/lib/longhorn-test" &`
2. Install `Longhorn` with env `KUBELET_ROOT_DIR` in `longhorn-driver-deployer` being set to the corresponding value.
3. Launch a pod using Longhorn volumes via StorageClass. Everything should work fine.
4. Delete the pod and the PVC. Everything should be cleaned up.
