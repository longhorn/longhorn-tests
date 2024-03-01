---
Test: restarting Kubelet should not result in repeated "no Pending workload pods ..." event for the workload pod.
---

## Related issues

- https://github.com/longhorn/longhorn/issues/8072

## Test step

**Given** A [deployment](https://github.com/longhorn/longhorn/blob/master/examples/deployment.yaml) is created.

**When** Kubelet on the node with attached volume of the deployment is restarted.
```bash
systemctl restart k3s-agent.service
```

**Then** Observe the events of the deployment pod.
```
kubectl get events --field-selector involvedObject.name=${POD_NAME} -w
```
**And** There are no recurring `no Pending workload pods for volume xxx to be mounted` events.
