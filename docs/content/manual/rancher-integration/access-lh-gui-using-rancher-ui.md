---
title: Access Longhorn GUI using Rancher proxy
---

**Given** Downstream (RKE2/RKE1/K3s) cluster in Rancher

AND Deploy Longhorn using either of Kubectl/helm/marketplace app

**When** Click the `Longhorn` app on Rancher UI

**Then** Navigates to Longhorn UI

AND User should be to do all the operations available on the Longhorn GUI

AND URL should be a suffix to the Rancher URL

AND NO error in the console logs
 