---
title: Test Helm uninstall Longhorn in different namespace
---

---
title: Test Label-driven Recurring Job


## Related issue
https://github.com/longhorn/longhorn/issues/467

## Test

**Given** helm install Longhorn in different namespace

**When** helm uninstall Longhorn

**Then** Longhorn should complete uninstalling.
