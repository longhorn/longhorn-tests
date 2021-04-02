---
title: Set Tolerations/PriorityClass For System Components
---

## Related issue
https://github.com/longhorn/longhorn/issues/2120

Manual Tests:

### Case 1: Existing Longhorn installation
1. Install Longhorn master.
1. Change toleration in UI setting
1. Verify that `longhorn.io/last-applied-tolerations` annotation and `toleration` of manager, drive deployer, UI are not changed.
1. Verify that `longhorn.io/last-applied-tolerations` annotation and `toleration` for managed components (CSI components, IM pods, share manager pod, EI daemonset, backing-image-manager, cronjob) are updated correctly

### Case 2: New installation by Helm
1. Install Longhorn master, set tolerations like:
  ```yaml
  defaultSettings:
    taintToleration: "key=value:NoSchedule"

  longhornManager:
    priorityClass: ~
    tolerations:
    - key: key
      operator: Equal
      value: value
      effect: NoSchedule

  longhornDriver:
    priorityClass: ~
    tolerations:
    - key: key
      operator: Equal
      value: value
      effect: NoSchedule

  longhornUI:
    priorityClass: ~
    tolerations:
    - key: key
      operator: Equal
      value: value
      effect: NoSchedule   
  ```
3. Verify that the toleration is added for: IM pods, Share Manager pods, CSI deployments, CSI daemonset, the backup jobs, manager, drive deployer, UI
4. Uninstall the Helm release. 
   Verify that uninstalling job has the same toleration as Longhorn manager.
   Verify that the uninstallation success.

### Case 3: Upgrading from Helm
1. Install Longhorn v1.0.2 using Helm, set tolerations using Longhorn UI
1. Upgrade Longhorn to master version, verify that `longhorn.io/managed-by: longhorn-manager` is not set for manager, driver deployer and UI.
1. Verify that `longhorn.io/managed-by: longhorn-manager` label is added for:  IM CRs, EI CRs, Share Manager CRs, IM pods, Share Manager pods, CSI services, CSI deployments, CSI daemonset.
1. Verify that `longhorn.io/last-applied-tolerations` is set for: IM pods, Share Manager pods, CSI deployments, CSI daemonset
1. Edit the tolerations using Longhorn UI and verify the tolerations get updated for components other than Longhorn manager, driver deployer and UI only. Longhorn manager, driver deployer and UI pods should not get restarted.
1. Upgrade the chart to specify toleration for manager, drive deployer, UI.
1. Verify that the toleration get applied
1. Repeat this test case with Longhorn v1.1.0 in step 1

### Case 4: Upgrading from kubectl
1. Install Longhorn v1.0.2 using kubectl, set tolerations using Longhorn UI
1. Upgrade Longhorn to master version, verify that `longhorn.io/managed-by: longhorn-manager` is not set for manager, driver deployer and UI.
1. Verify that `longhorn.io/managed-by: longhorn-manager` label is added for:  IM CRs, EI CRs, Share Manager CRs, IM pods, Share Manager pods, CSI services, CSI deployments, CSI daemonset.
1. Verify that `longhorn.io/last-applied-tolerations` is set for: IM pods, Share Manager pods, CSI deployments, CSI daemonset
1. Edit the tolerations using Longhorn UI and verify the tolerations get updated for components other than Longhorn manager, driver deployer and UI only. Longhorn manager, driver deployer and UI pods should not get restarted.
1. Edit the Yaml to specify toleration for manager, drive deployer, UI and upgrade Longhorn using kubectl command.
1. Verify that the toleration get applied
1. Repeat this test case with Longhorn v1.1.0 in step 1

### Case 5: Node with taints
1. Add some taints to all node in the cluster, e.g., `key=value:NoSchedule`
1. Repeate case 2, 3, 4

### Case 6: Priority Class UI
1. Change Priority Class setting in Longhorn UI
1. Verify that Longhorn only updates the managed components

### Case 7: Priority Class Helm
1. Change Priority Class in Helm for manager, driver, UI
1. Verify that only priority class name of manager, driver, UI get updated
