---
title: Node drain and deletion test
---
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
