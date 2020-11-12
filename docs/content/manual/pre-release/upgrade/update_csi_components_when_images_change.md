---
title: Re-deploy CSI components when their images change
---

1. Install Longhorn
1. Change the `longhorn-driver-deployer` yaml at https://github.com/longhorn/longhorn-manager/blob/c2ceb9f3f991810f811601d8c41c09b67fb50746/deploy/install/02-components/04-driver.yaml#L50 to use the new images for some CSI components
1. `Kubectl apply -f` the `longhorn-driver-deployer` yaml 
1. Verify that only CSI components with the new images are re-deployed and have new images
1. Redeploy `longhorn-driver-deployer` without changing the images.
1. Verify that no CSI component is re-deployed