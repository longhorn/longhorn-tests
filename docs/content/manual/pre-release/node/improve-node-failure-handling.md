---
title: Improve Node Failure Handling By Automatically Force Delete Terminating Pods of StatefulSet/Deployment On Downed Node
---
1. Setup a cluster of 3 worker nodes
1. Install Longhorn and set `Default Replica Count = 2` (because we will turn off one node)
1. Create a StatefulSet with 2 pods using the command:
    ```
    kubectl create -f https://raw.githubusercontent.com/longhorn/longhorn/master/examples/statefulset.yaml
    ```
1. Create a volume + pv + pvc named `vol1` and create a deployment(1 pod) of default ubuntu named `shell` with the usage of pvc `vol1` mounted under `/mnt/vol1`
1. Find the node which contains one pod of the StatefulSet/Deployment. Power off the node

#### StatefulSet
##### if `NodeDownPodDeletionPolicy ` is set to `do-nothing ` | `delete-deployment-pod`
- wait till the `pod.deletionTimestamp` has passed
- verify no replacement pod generated, the pod is stuck at terminating forever.

##### if `NodeDownPodDeletionPolicy ` is set to `delete-statefulset-pod ` | `delete-both-statefulset-and-deployment-pod`
- wait till pod's status becomes `terminating` and the `pod.deletionTimestamp` has passed (around 7 minutes)
- verify that the pod is deleted and there is a new running replacement pod. 
- Verify that you can access/read/write the volume on the new pod

#### Deployment
##### if `NodeDownPodDeletionPolicy ` is set to `do-nothing ` | `delete-statefulset-pod` AND `Volume Attachment Recovery Policy` is `never`
- wait till the `pod.deletionTimestamp` has passed
- replacement pod will be stuck in `Pending` state forever
- force delete the terminating pod
- wait till replacement pod is running
- verify that you can access `vol1` via the `shell` replacement pod under `/mnt/vol1` once it is in the running state
##### if `NodeDownPodDeletionPolicy ` is set to `do-nothing ` | `delete-statefulset-pod` AND `Volume Attachment Recovery Policy` is `wait`
- wait till replacement pod is generated (default is around 6 minutes, kubernetes setting)
- wait till the `pod.deletionTimestamp` has passed
- verify that you can access `vol1` via the `shell` replacement pod under `/mnt/vol1` once it is in the running state
- verify that the original `shell` pod is stuck in `Pending` state forever
##### if `NodeDownPodDeletionPolicy ` is set to `do-nothing ` | `delete-statefulset-pod` AND `Volume Attachment Recovery Policy` is `immediate`
- wait till replacement pod is generated (default is around 6 minutes, kubernetes setting)
- verify that you can access `vol1` via the `shell` replacement pod under `/mnt/vol1` once it is in the running state
- verify that the original `shell` pod is stuck in `Pending` state forever
##### if `NodeDownPodDeletionPolicy ` is set to `delete-deployment-pod ` | `delete-both-statefulset-and-deployment-pod` AND `Volume Attachment Recovery Policy` is `never`| `wait`|`immediate`
- wait till the `pod.deletionTimestamp` has passed
- verify that the pod is deleted and there is a new running replacement pod. 
- verify that you can access `vol1` via the `shell` replacement pod under `/mnt/vol1`
#### Other kinds
- Verify that Longhorn never deletes any other pod on the downed node.
#### Test example
One typical scenario when the enhancement has succeeded is as below. When a node (say `node-x`) goes down (assume using Kubernetes' default settings and user allows Longhorn to force delete pods):

| Time | Event | 
| :------------- | :----------: | 
| 0m:00s | `node-x`goes down and stops sending heartbeats to Kubernetes Node controller  |
| 0m:40s | Kubernetes Node controller reports `node-x` is `NotReady`.    |
| 5m:40s | Kubernetes Node controller starts evicting pods from `node-x` using graceful termination (set `DeletionTimestamp` and `deletionGracePeriodSeconds = 10s/30s`)  |
| 5m:50s/6m:10s | Longhorn forces delete the pod of StatefulSet/Deployment which uses Longhorn volume |
