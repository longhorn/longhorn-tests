---
title: Test upgrade for migrated Longhorn on Rancher
---

## Related discussion
https://github.com/longhorn/longhorn/discussions/4198

**Context**: since few customers used our broken chart longhorn 100.2.1+up1.3.1 on Rancher (Now fixed) with the workaround. We would like to verify the future upgrade path for those customers.

## Steps

1. Set up a cluster of Kubernetes 1.20.
1. Adding this repo to the apps section in new rancher UI
    1. repo: https://github.com/PhanLe1010/charts.git
    1. branch: release-v2.6-longhorn-1.3.1.
1. Access old rancher UI by navigating to `<your-rancher-url>/g`.
1. Install Longhorn 1.0.2.
1. Create/attach some volumes. Create a few recurring snapshot/backup job that run every minutes.
1. Upgrade Longhorn to v1.2.4.
1. Migrate Longhorn to new chart in new rancher UI https://longhorn.io/kb/how-to-migrate-longhorn-chart-installed-in-old-rancher-ui-to-the-chart-in-new-rancher-ui/.
1. Upgrade to longhorn 100.2.1+up1.3.1 in the UI.
1. Verify the upgrade would be stuck at with error:
    ```
    Patch CustomResourceDefinition "volumes.longhorn.io" in namespace
    error updating the resource "volumes.longhorn.io":
             cannot patch "volumes.longhorn.io" with kind CustomResourceDefinition: CustomResourceDefinition.apiextensions.k8s.io "volumes.longhorn.io" is invalid: spec.conversion.strategy: Invalid value: "Webhook": must be None if spec.preserveUnknownFields is true
    Error: UPGRADE FAILED: cannot patch "engineimages.longhorn.io" with kind CustomResourceDefinition: CustomResourceDefinition.apiextensions.k8s.io "engineimages.longhorn.io" is invalid: spec.conversion.strategy: Invalid value: "Webhook": must be None if spec.preserveUnknownFields is true && cannot patch "nodes.longhorn.io" with kind CustomResourceDefinition: CustomResourceDefinition.apiextensions.k8s.io "nodes.longhorn.io" is invalid: spec.conversion.strategy: Invalid value: "Webhook": must be None if spec.preserveUnknownFields is true && cannot patch "volumes.longhorn.io" with kind CustomResourceDefinition: CustomResourceDefinition.apiextensions.k8s.io "volumes.longhorn.io" is invalid: spec.conversion.strategy: Invalid value: "Webhook": must be None if spec.preserveUnknownFields is true
    ```
1. Apply the [workaround](https://github.com/longhorn/longhorn/pull/4237#issuecomment-1195339461)
1. Retry upgrade to longhorn 100.2.1+up1.3.1 in the UI.
1. Verify the upgrade is ok.
1. Verify that the user can successfully upgrade to future chart releases (e.g., Longhorn v1.3.2) from this version longhorn 100.2.1+up1.3.1.
