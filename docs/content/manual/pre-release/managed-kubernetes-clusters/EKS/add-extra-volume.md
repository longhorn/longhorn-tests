---
title: "[Add Extra Volume](https://longhorn.io/docs/1.3.0/advanced-resources/support-managed-k8s-service/manage-node-group-on-eks/#create-additional-volume)"
---
1. Create EKS cluster with 3 nodes and install Longhorn.
2. Create [deployment](https://github.com/longhorn/longhorn/blob/master/examples/deployment.yaml) and write some data to it.
3. In Longhorn, set `replica-replenishment-wait-interval` to `0`.
4. Go to the launch template of the EKS cluster node-group. You can find in the EKS cluster tab `Configuration/Compute/<node-group-name>` and click the launch template.
5. Click `Modify template (Create new version)` in the `Actions` drop-down menu.
6. Choose the `Source template version` in the `Launch template name and version description`.
7. Click `Advanced` then `Add new volume` in `Configure storage` and fill in the fields.
8. Adjust the auto-mount script and add to `User data` in `Advanced details`. Make sure the `DEV_PATH` matches the `Device name` of the additional volume.
    ```
    MIME-Version: 1.0
    Content-Type: multipart/mixed; boundary="==MYBOUNDARY=="
    --==MYBOUNDARY==
    Content-Type: text/x-shellscript; charset="us-ascii"
    #!/bin/bash
    # https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html#launch-template-user-data
    echo "Running custom user data script"
    DEV_PATH="/dev/sdb"
    mkfs -t ext4 ${DEV_PATH}
    MOUNT_PATH="/mnt/longhorn"
    mkdir ${MOUNT_PATH}
    mount ${DEV_PATH} ${MOUNT_PATH}
    ```
9. Click `Create template version` to save changes.
10. Go to the EKS cluster node-group and change `Launch template version` in `Node Group configuration`. Track the status in the `Update history` tab.
11. After update succeeded, check the deployment in step 2 still running and data exist, and check the extra volume can be added through Longhorn UI.