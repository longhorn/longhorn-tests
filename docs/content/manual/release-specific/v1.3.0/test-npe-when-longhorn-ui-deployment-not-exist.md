---
title: Test NPE when longhorn UI deployment CR not exist
---

## Related issue
https://github.com/longhorn/longhorn/issues/4065

## Test

**Given** helm install Longhorn

**When** delete `deployment/longhorn-ui`
*And* update `setting/kubernetes-cluster-autoscaler-enabled` to true or false

**Then** longhorn-manager pods should still be `Running`.
