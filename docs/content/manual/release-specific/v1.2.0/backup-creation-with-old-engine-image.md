---
title: Test Backup Creation With Old Engine Image
---

## Related issue
https://github.com/longhorn/longhorn/issues/2897

## Test Step

**Given** deploy engine image `longhornio/longhorn-engine:v1.1.2`.
*And* create volume `vol-engine112`.
*And* attach volume `vol-engine112` to one of a node.
*And* upgrade volume `vol-engine112` to engine image `longhornio/longhorn-engine:v1.1.2`.

**When** create backup of volume `vol-engine112`.

**Then** watch kubectl `kubectl get backups.longhorn.io -l backup-volume=vol-engine112 -w`.
*And* should see 2 two backups temporarily (in transition state). One with state `Completed`, the other one with state `Ready`.
*And* should see the backup with state `Completed` be clean up, only the backup with state `Ready` be left.
