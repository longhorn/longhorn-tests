---
title: Change imagePullPolicy to IfNotPresent Test
---
1. Install Longhorn using Helm chart with the new `longhorn master`
2. Verify that Engine Image daemonset, Manager daemonset, UI deployment, Driver Deployer deployment has the field `spec.template.spec.containers.imagePullPolicy` set to `IfNotPresent`
3. run the bash script `dev/scripts/update-image-pull-policy.sh` inside `longhorn` repo
4. Verify that Engine Image daemonset, Manager daemonset, UI deployment, Driver Deployer deployment has the field `spec.template.spec.containers.imagePullPolicy` set back to `Always`
