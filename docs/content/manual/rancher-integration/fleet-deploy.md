---
title: Longhorn using fleet on multiple downstream clusters
---

reference: https://github.com/rancher/fleet

### Test Longhorn deployment using fleet:
**Given** Downstream multiple (RKE2/RKE1/K3s) clusters in Rancher

**When** Use fleet to deploy Longhorn

**Then** Longhorn should be deployed to all the cluster

AND Longhorn UI should be accessible using Rancher proxy


### Test Longhorn uninstall using fleet:
**Given** Downstream multiple (RKE2/RKE1/K3s) clusters in Rancher

AND Longhorn is deployed on all the clusters using fleet

**When** Use fleet to uninstall Longhorn

**Then** Longhorn should be uninstalled from all the cluster

AND No Longhorn CRDs should be present in the cluster


### Test Longhorn upgrade using fleet:
**Given** Downstream multiple (RKE2/RKE1/K3s) clusters in Rancher

AND Longhorn is deployed on all the clusters using fleet

AND 1 RWO and 1 RWX volumes attached to node

**When** Use fleet to upgrade Longhorn

**Then** Longhorn should be upgraded from all the cluster

AND Data of volumes should be intact
