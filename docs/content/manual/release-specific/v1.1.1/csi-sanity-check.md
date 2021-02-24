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

    ---
    **NOTE**

    Some success of CSI sanity tests is dependent on [#2270](https://github.com/longhorn/longhorn/issues/2270).

    Currently, there will be 11 test failures caused by the dependent PR. Those could also be tested by applying the dependent PR.
    ```
    Summarizing 11 Failures:

    [Fail] Node Service NodeGetVolumeStats [It] should fail when volume does not exist on the specified path 
    /mnt/sda2/go/src/github.com/kubernetes-csi/csi-test/pkg/sanity/node.go:196

    [Fail] Node Service [It] should work 
    /mnt/sda2/go/src/github.com/kubernetes-csi/csi-test/pkg/sanity/node.go:91

    [Fail] Node Service [It] should be idempotent 
    /mnt/sda2/go/src/github.com/kubernetes-csi/csi-test/pkg/sanity/node.go:91

    [Fail] Controller Service [Controller Server] CreateVolume [It] should not  fail when requesting to create a volume with already existing name and   same capacity 
    /mnt/sda2/go/src/github.com/kubernetes-csi/csi-test/pkg/sanity/controller.  go:465

    [Fail] Controller Service [Controller Server] CreateVolume [It] should  fail when requesting to create a volume with already existing name and   different capacity 
    /mnt/sda2/go/src/github.com/kubernetes-csi/csi-test/pkg/sanity/controller.  go:506

    [Fail] Controller Service [Controller Server] CreateVolume [It] should not  fail when creating volume with maximum-length name 
    /mnt/sda2/go/src/github.com/kubernetes-csi/csi-test/pkg/sanity/controller.  go:554

    [Fail] Controller Service [Controller Server] ValidateVolumeCapabilities    [It] should fail when no volume capabilities are provided 
    /mnt/sda2/go/src/github.com/kubernetes-csi/csi-test/pkg/sanity/controller.  go:753

    [Fail] Controller Service [Controller Server] ControllerPublishVolume [It]  should fail when the node does not exist 
    /mnt/sda2/go/src/github.com/kubernetes-csi/csi-test/pkg/sanity/controller.  go:967

    [Fail] Controller Service [Controller Server] volume lifecycle [It] should  work 
    /mnt/sda2/go/src/github.com/kubernetes-csi/csi-test/pkg/sanity/controller.  go:1659

    [Fail] Controller Service [Controller Server] volume lifecycle [It] should  be idempotent 
    /mnt/sda2/go/src/github.com/kubernetes-csi/csi-test/pkg/sanity/controller.  go:1659

    [Fail] ExpandVolume [Controller Server] [It] should work 
    /mnt/sda2/go/src/github.com/kubernetes-csi/csi-test/pkg/sanity/controller.  go:1537

    Ran 42 of 77 Specs in 0.534 seconds
    FAIL! -- 31 Passed | 11 Failed | 1 Pending | 34 Skipped
    ```
    ---