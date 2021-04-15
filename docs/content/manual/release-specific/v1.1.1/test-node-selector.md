---
title: Test Node Selector
---
### Prepare the cluster
1. Using Rancher RKE to create a cluster of 2 Windows worker nodes and 3 Linux worker nodes.
1. Rancher will add the taint `cattle.io/os=linux:NoSchedule` to Linux nodes
1. Kubernetes will add label `kubernetes.io/os:linux` to Linux nodes

### Test steps
Repeat the following steps for each type of Longhorn installation: Rancher, Helm, Kubectl:
1. Follow the Longhorn document at the PR https://github.com/longhorn/website/pull/287 to install Longhorn with toleration `cattle.io/os=linux:NoSchedule` and node selector `kubernetes.io/os:linux`
1. Verify that Longhorn get deployed successfully on the 3 Linux nodes
1. Verify all volume basic functionalities is working ok
1. Create a volume of 3 replica named `vol-1`
1. Add label `longhorn.io/rating:best` to 2 Linux nodes
1. Follow the Longhorn document at the PR https://github.com/longhorn/website/pull/287 to set 2 node selectors `kubernetes.io/os:linux` and `longhorn.io/rating:best` for Longhorn
1. Verify that Longhorn gets deployed successfully on the 2 Linux nodes
1. Attach the `vol-1` to a node, verify that the attachment succeeds. One replica of the volume fails because it is on the down node.
1. Delete all failed replicas on the down node
1. Delete the down node, verify the deletion succeeds
1. Detach the `vol-1`
1. Follow the Longhorn document at the PR https://github.com/longhorn/website/pull/287 to set 1 node selector `kubernetes.io/os:linux` for Longhorn
1. Verify that Longhorn get redeployed successfully on the 3 Linux nodes   
1. Attach the `vol-1` to a node, verify that the attachment succeeds. Longhorn starts rebuild the 3rd replica on the new node