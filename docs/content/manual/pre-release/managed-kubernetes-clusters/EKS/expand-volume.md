---
title: "[Expand Volume](https://longhorn.io/docs/1.3.0/advanced-resources/support-managed-k8s-service/manage-node-group-on-eks/#storage-expansion)"
---
1. Create EKS cluster with 3 nodes and install Longhorn.
2. Create [deployment](https://github.com/longhorn/longhorn/blob/master/examples/deployment.yaml) and write some data to it.
3. In Longhorn, set `replica-replenishment-wait-interval` to `0`.
4. Go to the launch template of the EKS cluster node-group. You can find in the EKS cluster tab `Configuration/Compute/<node-group-name>` and click the launch template.
5. Click `Modify template (Create new version)` in the `Actions` drop-down menu.
6. Choose the `Source template version` in the `Launch template name and version description`.
7. Update the volume size in `Configure storage`.
8. Click `Create template version` to save changes.
9. Go to the EKS cluster node-group and change `Launch template version` in `Node Group configuration`. Track the status in the `Update history` tab.
8. After update succeeded, check the deployment in step 2 still running and data exist, and check volume expanded as expected through Longhorn UI.