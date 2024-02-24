---
title: Test Support Bundle Should Include Kubelet Log When On K3s Cluster
---

## Related issue
https://github.com/longhorn/longhorn/issues/7121

## Test

**Given** Longhorn installed on K3s cluster  
**When** generated support-bundle  
**Then** should have worker node kubelet logs in `k3s-agent-service.log`  
**And** should have control-plan node kubelet log in `k3s-service.log` (if Longhorn is deployed on control-plan node)  
