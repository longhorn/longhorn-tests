---
title: Support Kubelet Volume Metrics
---

## Intro

Kubelet exposes [kubelet_volume_stats_* metrics](https://github.com/kubernetes/kubernetes/blob/4b24dca228d61f4d13dcd57b46465b0df74571f6/pkg/kubelet/metrics/collectors/volume_stats.go#L27).
Those metrics measure PVC's filesystem related information inside a Longhorn block device.


## Test steps:
1. Create a cluster and set up this monitoring system: https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack
1. Install Longhorn. Deploy some workloads using Longhorn volumes. 
   Make sure there are some workloads using Longhorn PVCs in  `volumeMode: Block` and some workloads using Longhorn PVCs in `volumeMode: Filesystem`. 
   See https://longhorn.io/docs/1.0.2/references/examples/ for examples.
1. Create ingress to Prometheus server and Grafana. 
1. Navigate to Prometheus server, verify that all Longhorn PVCs in `volumeMode: Filesystem` show up in metrics: `kubelet_volume_stats_capacity_bytes kubelet_volume_stats_available_bytes kubelet_volume_stats_used_bytes kubelet_volume_stats_inodes kubelet_volume_stats_inodes_free kubelet_volume_stats_inodes_used`.  
   Verify that all Longhorn PVCs in `volumeMode: Block` do not show up.
1. Write/Delete files in Longhorn volumes. 
   Verify that the Prometheus server shows the correct status of Longhorn PVCs. 
   Verify that alerts get fired when we go above [the thresholds](https://github.com/prometheus-community/helm-charts/blob/main/charts/kube-prometheus-stack/templates/prometheus/rules/kubernetes-storage.yaml?rgh-link-date=2020-09-24T13%3A00%3A06Z)
1. Navigate to Grafana, navigate to `Kubernetes/Persistent Volumes` dashboard. 
   Verify that graphs report correct data.
1. Negative test case: 
   use Longhorn UI to delete a volume of a running pod, 
   verify that the PVC corresponding volume still exists but it stops showing up in `kubelet_volume_stats_*` metrics
