---
title: Test ISCSI Installation on EKS
---

This is for EKS or similar users who doesn't need to log into each host to install 'ISCSI' individually.

Test steps:

1. Create an EKS cluster with 3 nodes.
2. Run the following command to install iscsi on every nodes.
```
kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/iscsi/longhorn-iscsi-installation.yaml
```
3. In Longhorn Manager Repo Directory run:
```
kubectl apply -Rf ./deploy/install/
```
4. Longhorn should be able installed successfully.
5. Try to create a pod with a pvc:
```
kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/master/examples/simple_pvc.yaml
kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/master/examples/simple_pod.yaml
```
6. Check the pod is created successfully with a valid Longhorn volume mounted.
