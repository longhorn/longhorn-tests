---
title: Test Helm uninstall Longhorn in different namespace
---

## Related issue
https://github.com/longhorn/longhorn/issues/2034

## Test

**Given** helm install Longhorn in different namespace

**When** helm uninstall Longhorn

**Then** Longhorn should complete uninstalling.
