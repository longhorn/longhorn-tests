---
title: Test Version Bump: Bump Kubernetes, API version group, CSI component's dependency version
---

GitHub issue: https://github.com/longhorn/longhorn/issues/2757

# Test with specific Kubernetes version
1. For each Kubernetes version (1.18, 1.19, 1.20, 1.21, 1.22), test basic functionalities of Longhorn v1.2.0
   (create/attach/detach/delete volume/backup/snapshot using yaml/UI)

# Test Kubernetes and Longhorn upgrade 
1. Deploy K3s v1.21
2. Deploy Longhorn v1.1.2
3. Create some workload pods using Longhorn volumes
4. Upgrade Longhorn to v1.2.0
5. Verify that everything is OK
6. Upgrade K3s to v1.22
7. Verify that everything is OK

# Retest the Upgrade Lease Lock
We remove the client-go patch https://github.com/longhorn/longhorn-manager/pull/639#issuecomment-905030885,
so we need to retest the test ../v1.0.2/upgrade-lease-lock.md

> Note: Longhorn versions prior to v1.2.0 will not work on k8s/k3s v1.22