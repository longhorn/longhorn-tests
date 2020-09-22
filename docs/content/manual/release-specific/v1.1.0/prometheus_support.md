---
title: Prometheus Support
---
Prometheus Support allows user to monitor the longhorn metrics. The details are available at https://longhorn.io/docs/1.1.0/monitoring/
## Monitor longhorn
1. Deploy the Prometheus-operator, ServiceMonitor pointing to longhorn-backend and Prometheus as mentioned in the doc.
2. Create an ingress pointing to Prometheus service.
3. Access the Prometheus web UI using the ingress created in the step 2.
4. Select the metrics from below to monitor the longhorn resources.
    1. longhorn_volume_capacity_bytes
    2. longhorn_volume_actual_size_bytes
    3. longhorn_volume_state
    4. longhorn_volume_robustness
    5. longhorn_instance_manager_cpu_requests_millicpu
    6. longhorn_instance_manager_cpu_usage_millicpu
    7. longhorn_instance_manager_memory_requests_bytes
    8. longhorn_instance_manager_memory_usage_bytes
    9. longhorn_manager_cpu_usage_millicpu
    10. longhorn_manager_memory_usage_bytes
    11. longhorn_node_count_total
    12. longhorn_node_status
    13. longhorn_node_cpu_capacity_millicpu
    14. longhorn_node_cpu_usage_millicpu
    15. longhorn_node_memory_capacity_bytes
    16. longhorn_node_memory_usage_bytes
5. Deploy workloads which use Longhorn volumes into the cluster. Verify that there is no abnormal data. e.g: volume capacity is 0, cpu usage is over 4000 milicpu etc.
6. Attach a volume to a node. Detach the volume and attach it to a different node. Verify that the volume's information is reported by at most 1 longhorn-manager at any time.

## Configure Prometheus alert manager
1. Deploy the Alertmanager as mentioned in the doc.
2. Modify the alert configuration file and set email or slack.
3. Deploy a service using node port to access web UI of the alert manager as mentioned in the doc.
4. Follow the steps from the doc to create PrometheusRule and configure the Prometheus server.
5. Go beyond the threshold set for PrometheusRule in the step 4.
6. Verify the email or slack, user should get the alert message.

## Monitor with Grafana
1. Create a ConfigMap referring to the Prometheus. (Refer the doc)
2. Deploy the Grafana and a service to access the UI.
3. Go to Grafana dashboard and import prebuilt longhorn example.
4. Verify the graphs and data are available to monitor.

## Monitor with Rancher app
1. Create a cluster in Rancher. (1 etcd/control plane and 3 worker nodes)
2. Deploy longhorn v1.1.0.
3. Enable the monitoring for a project.
4. Deploy the ServiceMonitor pointing to longhorn-backend.
5. Access the url provided by the app to access Prometheus or Grafana.
6. Verify the longhorn metrics are available to monitor.