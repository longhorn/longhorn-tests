---
title: "Uninstallation Checks"
---

### Prerequisites
1. Have a setup of Longhorn installed on a kubernetes cluster.
2. Have few volumes backups stored on S3/NFS backup store.
3. Have one DR volume created (not activated) in another cluster with a volume in current cluster.

### Test steps
1. Uninstall Longhorn.
2. Check the logs of the job `longhorn-uninstall`, make sure there is no error.
3. Check all the components of Longhorn from the namespace longhorn-system are uninstalled. E.g. Longhorn manager, Longhorn driver, Longhorn UI, instance manager, engine image, CSI driver etc.
4. Check all the CRDs are removed `kubectl get crds | grep longhorn`.
5. Check the backup stores, the backups taken should NOT be removed.
6. Activate the DR volume in the other cluster and check the data.

**Note:** If uninstalling from Rancher cluster using cluster explorer, uninstall Longhorn first then the crds.