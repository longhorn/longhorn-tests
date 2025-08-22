---
title: Support Bundle Collects Logs From Path Specified In Setting
---

## Related issue
https://github.com/longhorn/longhorn/issues/11522

## Test

**Given** V2 data engine is enabled  
**And** `/tmp/longhorn/logs/` directory exists on all cluster nodes  
**And** `log-path` setting is set to `/tmp/longhorn/logs/`  
**And** V2 instance manager pods have restarted  
**When** A support bundle is generated  
**Then** Files from the host's `log-path` directory exist under `<NODE>/log` in the support bundle