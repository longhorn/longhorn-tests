---
title: Test Support Bundle Extended Collection
---

## Related issue
https://github.com/longhorn/longhorn/issues/6754

## Test /proc/mounts file

**Given** Longhorn installed  
**When** generated support-bundle  
**And** proc_mounts file should exist in support-bundle/nodes/<name>/hostinfo/

## Test multipath.config file

**Given** Longhorn installed  
**And** /etc/multipath.config exists on cluster nodes  
**When** generated support-bundle  
**And** multipath.config should exist in support-bundle/nodes/<name>/hostinfo/
