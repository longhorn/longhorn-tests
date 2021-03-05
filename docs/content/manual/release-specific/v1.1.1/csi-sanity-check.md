---
title: CSI Sanity Check
---

## Related issue
https://github.com/longhorn/longhorn/issues/2076

## Run csi-sanity
1. Prepare Longhorn cluster and setup backup target.
2. Make csi-sanity binary from [csi-test](https://github.com/kubernetes-csi/csi-test).
3. On one of the cluster node, run csi-sanity binary.
    ```bash
    csi-sanity -csi.endpoint /var/lib/kubelet/obsoleted-longhorn-plugins/driver.longhorn.io/csi.sock -ginkgo.skip="should create volume from an existing source snapshot|should return appropriate values|should succeed when creating snapshot with maximum-length name|should succeed when requesting to create a snapshot with already existing name and same source volume ID|should fail when requesting to create a snapshot with already existing name and different source volume ID"
    ```
    ---
    **NOTE**

    The skipped tests will be tracked by [#2271](https://github.com/longhorn/longhorn/issues/2271).

    ---
