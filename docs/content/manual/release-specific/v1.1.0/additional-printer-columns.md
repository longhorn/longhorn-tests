---
title: Test Additional Printer Columns
---


For each of the case below: 

1. Fresh installation of Longhorn. (make sure to delete all Longhorn CRDs before installation)
1. Upgrade from older version.

Run:

```
kubectl get <LONGHORN-CRD> -n longhorn-system
```

Verify that the output contains information as specify in the `additionalPrinerColumns` 
at [here](https://github.com/longhorn/longhorn-manager/blob/master/deploy/install/01-prerequisite/03-crd.yaml)
