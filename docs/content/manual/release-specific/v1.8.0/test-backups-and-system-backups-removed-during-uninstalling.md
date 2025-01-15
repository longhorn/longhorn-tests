---
title: Backups And System Backups Removed During Uninstalling
---

## Related issues

- https://github.com/longhorn/longhorn/issues/10104

## LEP

- https://github.com/longhorn/longhorn/pull/5411

## Test Uninstall Longhorn After An Upgrade

**Given** a Longhorn 1.7.x cluster with 3 worker nodes.

**AND** the default backup target is set.

**When** volumes, completed backups, failed backups, and a system backup are created.

**And** Longhorn is upgraded to v1.8.0.

**Then** Upgrade successfully.

**And** the `OwnerReference` of the system backup is added.

**When** Longhorn is uninstalled.

**Then** the uninstallation completes successfully.

**And** backups and the system backup remain on the backupstore.

