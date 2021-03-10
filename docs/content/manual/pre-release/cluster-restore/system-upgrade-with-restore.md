---
title: Longhorn system upgrade with restore
---

Notice that the behaviors will be different if the cluster node roles are different. e.g., A cluster contains 1 dedicated master node + 3 worker node is different from a cluster contains 3 nodes which are both master and worker.
This test may need to be validated for both kind of cluster.

1. Install Longhorn system. Deploy one more compatible engine image.
2. Deploy some workloads using Longhorn volumes then write some data.
3. Create a cluster snapshot via Rancher.
4. Upgrade the Longhorn system to a newer version. Then modify the settings or node configs (especially the configs introduced in the new version).
5. Restore the cluster.
6. Follow the doc after the restore. Verify:
   1. The system re-upgrade should succeed.
   2. The modifications for the settings or configs in step 4 won't be back. But users can re-modify them.
   3. The workloads and the volumes created in step 2 work fine after restarting.

The github issue link: https://github.com/longhorn/longhorn/issues/2228
