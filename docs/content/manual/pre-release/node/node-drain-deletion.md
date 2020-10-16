---
title: Node drain and deletion test
---
# Drain with force
Make sure the volumes on the drained/removed node can be detached or recovered correctly. The related issue: https://github.com/longhorn/longhorn/issues/1214
1. Deploy a cluster contains 3 worker nodes N1, N2, N3.
2. Deploy Longhorn.
3. Create a 1-replica deployment with a 3-replica Longhorn volume. The volume is attached to N1.
4. Write some data to the volume and get the md5sum.
5. Force drain and remove N2, which contains one replica only.
6. Wait for the volume Degraded.
7. Force drain and remove N1, which is the node the volume is attached to.
8. Wait for the volume detaching then being recovered. Will get attached to the workload/node.
9. Validate the volume content. The data is intact.

# Drain without force
1. Cordon the node. Longhorn will automatically disable the node scheduling when a Kubernetes node is cordoned.
2. Evict all the replicas from the node.
3. Run the following command to drain the node with ```force``` flag set to false.
    ```
    kubectl drain <Node name> --delete-local-data=true --force=false --grace-period=-1 --ignore-daemonsets=true --timeout=<Desired timeout in secs>
    ```
4. Observe that the workloads move to another node. The volumes should first detach and attach to workloads once they move to another node.
5. Observe the logs, one by one all the pods should get evicted.
    ```
    node/<node-name> already cordoned
    WARNING: ignoring DaemonSet-managed Pods: ingress-nginx/nginx-ingress-controller-bpf2t, kube-system/canal-hwk6v, longhorn-system/engine-image-ei-605a0f3e-8gb8l, longhorn-system/longhorn-csi-plugin-flq84, longhorn-system/longhorn-manager-tps6v
    evicting pod longhorn-system/instance-manager-r-1aebab59
    evicting pod kube-system/coredns-849545576b-v54vn
    evicting pod longhorn-system/instance-manager-e-e591dbce
    pod/instance-manager-r-1aebab59 evicted
    pod/instance-manager-e-e591dbce evicted
    pod/coredns-849545576b-v54vn evicted
    node/<node-name> evicted
    ```

Note: ```--ignore-daemonsets``` should be set to true to ignore some DaemonSets that exist on node such as Longhorn manager, Longhorn CSI plugin, engine image in a Longhorn deployed cluster.

