---
title: Test Service Account mount on host
---

1. This test case should be tested on both yaml installation, chart installation (Helm and Rancher UI), as well as upgrade scenarios
1. After install Longhorn using on of the above method, ssh into a worker node that has a longhorn-manager pod running
1. check the mount point `/run/secrets/kubernetes.io/serviceaccount` by running:
   ```
   root@node-1:~# findmnt  /run/secrets/kubernetes.io/serviceaccount
   ```
1. Verify that there is no such mount point
1. Kill the longhorn-manager pod on the above node and wait for it to be recreated and running
1. check the mount point `/run/secrets/kubernetes.io/serviceaccount` by running:
   ```
   root@node-1:~# findmnt  /run/secrets/kubernetes.io/serviceaccount
   ```
1. Verify that there is no such mount point
1. Repeat the step 5 to 7 a few times