---
title: "[Upgrade K8s](https://longhorn.io/docs/1.3.0/advanced-resources/support-managed-k8s-service/upgrade-k8s-on-aks/)"
---
1. Create AKS cluster with 3 nodes and install Longhorn.
2. Create [deployment](https://github.com/longhorn/longhorn/blob/master/examples/deployment.yaml) and write some data to it.
3. In Longhorn, set `replica-replenishment-wait-interval` to `0`.
4. Upgrade AKS control plane.
    ```
    AKS_RESOURCE_GROUP=<aks-resource-group>
    AKS_CLUSTER_NAME=<aks-cluster-name>
    AKS_K8S_VERSION_UPGRADE=<aks-k8s-version>
    az aks upgrade \
        --resource-group ${AKS_RESOURCE_GROUP} \
        --name ${AKS_CLUSTER_NAME} \
        --kubernetes-version ${AKS_K8S_VERSION_UPGRADE} \
        --control-plane-only
    ```
5. Add a new node-pool.

    ```
    AKS_NODEPOOL_NAME_NEW=<new-nodepool-name>
    AKS_DISK_SIZE=<disk-size-in-gb>
    AKS_NODE_NUM=<number-of-nodes>
    az aks nodepool add \
      --resource-group ${AKS_RESOURCE_GROUP} \
      --cluster-name ${AKS_CLUSTER_NAME} \
      --name ${AKS_NODEPOOL_NAME_NEW} \
      --node-count ${AKS_NODE_NUM} \
      --node-osdisk-size ${AKS_DISK_SIZE} \
      --kubernetes-version ${AKS_K8S_VERSION_UPGRADE} \
      --mode System
    ```
6. Using Longhorn UI to disable the disk scheduling and request eviction for nodes in the old node-pool.
7. Cordon and drain Kubernetes nodes in the old node-pool.
    ```
    AKS_NODEPOOL_NAME_OLD=<old-nodepool-name>
    for n in `kubectl get nodes | grep ${AKS_NODEPOOL_NAME_OLD}- | awk '{print $1}'`; do
      kubectl cordon $n && \
      kubectl drain $n --ignore-daemonsets --pod-selector='app!=csi-attacher,app!=csi-provisioner' --delete-emptydir-data
    done
    ```
8. Delete old node-pool.
    ```
    az aks nodepool delete \
      --cluster-name ${AKS_CLUSTER_NAME} \
      --name ${AKS_NODEPOOL_NAME_OLD} \
      --resource-group ${AKS_RESOURCE_GROUP}
    ```
9. Check the deployment in step 2 still running and data exist.