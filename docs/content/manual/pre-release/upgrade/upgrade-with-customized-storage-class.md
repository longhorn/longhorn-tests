---
title: Test system upgrade with a new storage class being default
---

1. Install a previous stable Longhorn on a K8s cluster.
1. Create a storage class 'longhorn-rep-2' with replica 2 and make it default.
1. Create some volumes with the above created storage class and attach them to workloads.
1. Upgrade Longhorn to latest version.
1. Longhorn should be upgraded.
1. Storage class 'longhorn-rep-2' should be the default storage class.
1. Create two volumes, one with 'longhorn' storage class and other with 'longhorn-rep-2'.
2. Verify the volumes are created as per their storage class. 
