---
title: "[Expand Volume](https://longhorn.io/docs/1.3.0/advanced-resources/support-managed-k8s-service/manage-node-group-on-gke/)"
---
1. Create GKE cluster with 3 nodes and install Longhorn.
2. Create [deployment](https://github.com/longhorn/longhorn/blob/master/examples/deployment.yaml) and write some data to it.
3. In Longhorn, set `replica-replenishment-wait-interval` to `0`.
4. Add a new node-pool. Later Longhorn components will be automatically deployed on the nodes in this pool.

    ```
    GKE_NODEPOOL_NAME_NEW=<new-nodepool-name>
    GKE_REGION=<gke-region>
    GKE_CLUSTER_NAME=<gke-cluster-name>
    GKE_IMAGE_TYPE=Ubuntu
    GKE_MACHINE_TYPE=<gcp-machine-type>
    GKE_DISK_SIZE_NEW=<new-disk-size-in-gb>
    GKE_NODE_NUM=<number-of-nodes>
    gcloud container node-pools create ${GKE_NODEPOOL_NAME_NEW} \
      --region ${GKE_REGION} \
      --cluster ${GKE_CLUSTER_NAME} \
      --image-type ${GKE_IMAGE_TYPE} \
      --machine-type ${GKE_MACHINE_TYPE} \
      --disk-size ${GKE_DISK_SIZE_NEW} \
      --num-nodes ${GKE_NODE_NUM}
  
    gcloud container node-pools list \
      --zone ${GKE_REGION} \
      --cluster ${GKE_CLUSTER_NAME} 
    ```
5. Using Longhorn UI to disable the disk scheduling and request eviction for nodes in the old node-pool.
6. Cordon and drain Kubernetes nodes in the old node-pool.
    ```
    GKE_NODEPOOL_NAME_OLD=<old-nodepool-name>
    for n in `kubectl get nodes | grep ${GKE_CLUSTER_NAME}-${GKE_NODEPOOL_NAME_OLD}- | awk '{print $1}'`; do
      kubectl cordon $n && \
      kubectl drain $n --ignore-daemonsets --pod-selector='app!=csi-attacher,app!=csi-provisioner' --delete-emptydir-data
    done
    ```
7. Delete old node-pool.
    ```
    gcloud container node-pools delete ${GKE_NODEPOOL_NAME_OLD}\
      --zone ${GKE_REGION} \
      --cluster ${GKE_CLUSTER_NAME}
    ```
8. Check the deployment in step 2 still running and data exist, and check volume expanded as expected through Longhorn UI.