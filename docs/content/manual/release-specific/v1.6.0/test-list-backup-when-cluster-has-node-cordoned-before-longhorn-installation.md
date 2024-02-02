---
title: Test list backup when cluster has node cordoned before Longhorn installation
---

## Related issue
https://github.com/longhorn/longhorn/issues/7619

## Test step

**Given** a cluster has 3 worker nodes.  
**And** 2 worker nodes are cordoned.  
**And** Longhorn is installed.  

**When** Setting up a backup target.  

**Then** no error is observed on the UI Backup page.  
**And** Backup custom resources are created if the backup target has existing backups.  

