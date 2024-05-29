---
title: Support bundle node collection timeout
---

When the timeout expires, the support bundle generation will proceed without requiring the collection of node bundles.

## Related issues

- https://github.com/longhorn/longhorn/issues/8623

## Test support bundle image supports node collection timeout

**Given** Run the support bundle manager image (version 0.0.38 or later) using Docker.
```
> docker run -it longhornio/support-bundle-kit:v0.0.38 bash
```

**When** Execute `support-bundle-kit manager --help`.  
**Then** The help menu displays the `--node-timeout` option.
```
> support-bundle-kit manager --help | grep node-timeout
      --node-timeout duration       The support bundle node collection time out
```

## Test `support-bundle-node-collection-timeout` setting

**Given** Simulate the node bundle blockage by patching the [rancher/support-bundle-kit](https://github.com/rancher/support-bundle-kit) code base and create an image.
```diff
diff --git a/pkg/manager/manager.go b/pkg/manager/manager.go
index 87e7b147..1835820b 100644
--- a/pkg/manager/manager.go
+++ b/pkg/manager/manager.go
@@ -324,7 +324,7 @@ func (m *SupportBundleManager) completeNode(node string) {
        _, ok := m.expectedNodes[node]
        if ok {
                logrus.Debugf("Complete node %s", node)
-               delete(m.expectedNodes, node)
+               // delete(m.expectedNodes, node)
        } else {
                logrus.Warnf("Complete an unknown node %s", node)
        }
```
**And** Configure `support-bundle-manager-image` setting value to use the image created in the previous step.
```
> kubectl -n longhorn-system edit settings.longhorn.io support-bundle-manager-image

> kubectl -n longhorn-system get settings.longhorn.io support-bundle-manager-image
NAME                           VALUE                                         AGE
support-bundle-manager-image   c3y1huang/research:48-lh-support-bundle-kit   7d23h
```
**And** Set `support-bundle-node-collection-timeout` setting value to 5.
```bsah
> kubectl -n longhorn-system edit settings.longhorn.io support-bundle-node-collection-timeout

> kubectl -n longhorn-system get settings.longhorn.io support-bundle-node-collection-timeout
NAME                                     VALUE   AGE
support-bundle-node-collection-timeout   5       1h
```

**When** Generate a support bundle using Longhorn UI.  
**And** Monitor the support bundle manager logs.
```
> kubectl -n longhorn-system logs `kubectl -n longhorn-system get pod -l app=support-bundle-manager --no-headers | awk '{print $1}'` -f
```

**Then** The support bundle is generated after the configured timeout.
```
> kubectl -n longhorn-system get pod -l app=support-bundle-agent
NAME                                                            READY   STATUS    RESTARTS   AGE
supportbundle-agent-support-bundle-2024-05-28t03-01-40z-d7x7x   1/1     Running   0          5m1s
supportbundle-agent-support-bundle-2024-05-28t03-01-40z-jxj6c   1/1     Running   0          5m1s
supportbundle-agent-support-bundle-2024-05-28t03-01-40z-mmrll   1/1     Running   0          5m1s
> kubectl -n longhorn-system get pod -l app=support-bundle-agent
NAME                                                            READY   STATUS        RESTARTS   AGE
supportbundle-agent-support-bundle-2024-05-28t03-01-40z-mmrll   0/1     Terminating   0          5m2s
supportbundle-agent-support-bundle-2024-05-28t03-01-40z-jxj6c   0/1     Terminating   0          5m2s
```
**And** A timeout log is recorded in the support bundle manager pod logs.
```
time="2024-05-28T03:07:07Z" level=info msg="Some nodes are timeout, not all node bundles are received."
```