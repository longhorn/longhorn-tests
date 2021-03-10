---
title: Node creation and deletion with restore
---

Notice that the behaviors will be different if the cluster node roles are different. e.g., A cluster contains 1 dedicated master node + 3 worker node is different from a cluster contains 3 nodes which are both master and worker.
This test may need to be validated for both kind of cluster.

1. Deploy a 3-worker-node cluster then install Longhorn system.
2. Deploy some workloads using Longhorn volumes then write some data.
3. Create a cluster snapshot via Rancher.
4. Add a new worker node for this cluster. Deploy workloads on this node.
5. Restore the cluster. 
6. Follow the doc after the restore. Verify:
    1. The new node is still in the Longhorn system. All necessary longhorn workloads will be on the node.
    2. The workloads and the volumes created in step 2 work fine after restarting.
    3. The data of the volumes created in step 4 can be recovered.
7. Create one more cluster snapshot.
8. Delete one node all related volumes/replicas on the node.
9. Restore the cluster.
10. Follow the doc after the restore. Verify:
    1. There is no corresponding Longhorn node CR.
    2. The Longhorn pods on the deleted node will be restored but they will become `Terminating` after several minutes. Users need to force deleting them.
    3. The volumes or replicas CRs on the gone node will be restored. Users can clean up them.
    4. The workloads and the volumes not on the removed node work fine after restarting.

The github issue link: https://github.com/longhorn/longhorn/issues/2228
