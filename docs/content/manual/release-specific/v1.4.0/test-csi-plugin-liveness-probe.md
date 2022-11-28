---
title: Test CSI plugin liveness probe
---

## Related discussion
https://github.com/longhorn/longhorn/issues/3907

## Test CSI plugin liveness probe should recover CSI socket file

**Given** healthy Longhorn cluster

**When** delete the Longhorn CSI socket file on one of the node(`node-1`).
    `rm /var/lib/kubelet/plugins/driver.longhorn.io/csi.sock`

**Then** the `longhorn-csi-plugin-*` pod on `node-1` should be restarted.

And the `csi-provisioner-*` pod on `node-1` should be restarted.  
And the `csi-resizer-*`     pod on `node-1` should be restarted.  
And the `csi-snapshotter-*` pod on `node-1` should be restarted.  
And the `csi-attacher-*`    pod on `node-1` should be restarted.  
> **Note:** In `node-1`, the other pods of the CSI sidecar components restarted
            are triggered by their internal [ProbeForever](https://github.com/kubernetes-csi/csi-lib-utils/blob/e085359dea1b0e9e49b02cb6bb30f33a80c6fe02/rpc/common.go#L109)
            to the CSI connection. It is not due to the liveness probe of the
            `longhorn-csi-plugin`.

And Longhorn CSI socket file should exist.
