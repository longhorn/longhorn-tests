---
title: Test Backup Creation With Old Engine Image
---

## Related issue
https://github.com/longhorn/longhorn/issues/2897

## Test Step

**Given** with Longhorn v1.2.0-rc2 or above.
*And* deploy compatible engine image `oldEI` older than test version (for example: `longhornio/longhorn-engine:<previous feature/patch release version>`).
*And* create volume `vol-old-engine`.
*And* attach volume `vol-old-engine` to one of a node.
*And* upgrade volume `vol-old-engine` to engine image `oldEI`.

**When** create backup of volume `vol-old-engine`.

**Then** watch kubectl `kubectl -n longhorn-system get backups.longhorn.io -l backup-volume=vol-old-engine -w`.
*And* should see only one backup be left after a while.
