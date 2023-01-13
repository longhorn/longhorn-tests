---
title: Test the trim related option update for old volumes
---

## Related issue
https://github.com/longhorn/longhorn/issues/5218

## Test step

**Given** Deploy Longhorn v1.3.2

*And* Created and attached a volume.

*And* Upgrade Longhorn to the latest.

*And* Do live upgrade for the volume. (The 1st volume using the latest engine image but running in the old instance manager.)

*And* Created and attached a volume with the v1.3.2 engine image. (The 2nd volume using the old engine image but running in the new instance manager.)

**When** Try to update `volume.spec.unmapMarkSnapChainRemoved` for both volumes via `kubectl` or GUI

**Then** Verify `engine.status.unmapMarkSnapChainRemovedEnabled` for both volumes is always `false`

*And* No error messages in the longhorn manager pod logs.

*And* Both volumes function correctly.
