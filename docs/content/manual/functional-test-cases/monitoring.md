---
title: Monitoring
---

Prometheus Support test cases
----

1.  Install the Prometheus Operator (include a role and service account for it). For example:<pre>apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: prometheus-operator
  namespace: default
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: prometheus-operator
subjects:<br>  - kind: ServiceAccount
    name: prometheus-operator
    namespace: default<br>--
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: prometheus-operator
  namespace: default
rules:<br>  - apiGroups:<br>      - extensions
    resources:<br>      - thirdpartyresources
    verbs: ["*"]<br>  - apiGroups:<br>      - apiextensions.k8s.io
    resources:<br>      - customresourcedefinitions
    verbs: ["*"]<br>  - apiGroups:<br>      - monitoring.coreos.com
    resources:<br>      - alertmanagers<br>      - prometheuses<br>      - prometheuses/finalizers<br>      - servicemonitors<br>      - prometheusrules<br>      - podmonitors
    verbs: ["*"]<br>  - apiGroups:<br>      - apps
    resources:<br>      - statefulsets
    verbs: ["*"]<br>  - apiGroups: [""]
    resources:<br>      - configmaps<br>      - secrets
    verbs: ["*"]<br>  - apiGroups: [""]
    resources:<br>      - pods
    verbs: ["list", "delete"]<br>  - apiGroups: [""]
    resources:<br>      - services<br>      - endpoints
    verbs: ["get", "create", "update"]<br>  - apiGroups: [""]
    resources:<br>      - nodes
    verbs: ["list", "watch"]<br>  - apiGroups: [""]
    resources:<br>      - namespaces
    verbs: ["list", "watch"]</pre>
<pre>
apiVersion: v1
kind: ServiceAccount
metadata:
  name: prometheus-operator
  namespace: default
---
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: prometheus-operator
  name: prometheus-operator
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus-operator
  template:
    metadata:
      labels:
        app: prometheus-operator
    spec:
      containers:
        - args:
            - --kubelet-service=kube-system/kubelet
            - --config-reloader-image=quay.io/coreos/configmap-reload:v0.0.1
          image: quay.io/coreos/prometheus-operator:v0.36.0
          name: prometheus-operator
          ports:
            - containerPort: 8080
              name: http
          resources:
            limits:
              cpu: 200m
              memory: 100Mi
            requests:
              cpu: 100m
              memory: 50Mi
      securityContext:
        runAsNonRoot: true
        runAsUser: 65534
      serviceAccountName: prometheus-operator</pre>

2. Install a Service Monitor pointing to `longhon-backend` service by selecting `app: longhorn-manager` label. For example:<pre>apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: longhorn-backend
  labels:
    team: backend
spec:
  selector:
    matchLabels:
      app: longhorn-manager
  namespaceSelector:
    matchNames:<br>    - longhorn-system
  endpoints:<br>  - port: manager</pre>
3. Install Prometheus (include a role and service account for it). Include the above `service monitor` in the Prometheus's config. Expose to the Prometheus instance to outside using a service of type NodePort. For example:<pre>apiVersion: v1
kind: ServiceAccount
metadata:
  name: prometheus<br>---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: prometheus
rules:<br>  - apiGroups: [""]
    resources:<br>      - nodes<br>      - services<br>      - endpoints<br>      - pods<br>    verbs: ["get", "list", "watch"]<br>  - apiGroups: [""]
    resources:<br>      - configmaps
    verbs: ["get"]<br>  - nonResourceURLs: ["/metrics", "/federate"]
    verbs: ["get"]<br>---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: prometheus
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: prometheus
subjects:<br>  - kind: ServiceAccount
    name: prometheus
    namespace: default<br>---
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: prometheus
spec:
  serviceAccountName: prometheus
  serviceMonitorSelector:
    matchLabels:
            team: backend<br>---
apiVersion: v1
kind: Service
metadata:
  name: prometheus
spec:
  type: NodePort
  ports:<br>  - name: web
    port: 9090
    protocol: TCP
    targetPort: web
  ports:<br>    - port: 9090
  selector:
    prometheus: prometheus</pre>
4. Find the `prometheus` service and access Prometheus web UI using the nodeIP and the port

|     | **Test Scenario** | **Test Steps** | **Expected results** |
| --- | --- | --- | --- |
| 1   | All the Metrics are present | **Pre-requisite:**<br><br>1.  Prometheus is setup is done and Prometheus web UI is accessible.</pre<br><br>**Test Steps:**<br><br>1.  Go to Prometheus web UI.</pre<br>2.  Verify the metrics are available. | The below metrics should be available:<br><br>1.  longhorn\_volume\_capacity\_bytes</pre<br>2.  longhorn\_volume\_usage\_bytes</pre<br>3.  longhorn\_node\_status</pre<br>4.  onghorn\_instance\_manager\_cpu\_requests\_millicpu</pre<br>5.  longhorn\_instance\_manager\_cpu\_usage\_millicpu</pre<br>6.  longhorn\_instance\_manager\_memory\_requests\_bytes</pre<br>7.  longhorn\_instance\_manager\_memory\_usage\_bytes</pre<br>8.  longhorn\_manager\_cpu\_usage\_millicpu</pre<br>9.  longhorn\_manager\_memory\_usage\_bytes</pre<br>10.  longhorn\_disk\_capacity\_bytes</pre<br>11.  longhorn\_disk\_usage\_bytes</pre<br>12.  longhorn\_node\_capacity\_bytes</pre<br>13.  longhorn\_node\_usage\_bytes |
| 2   | longhorn\_volume\_capacity\_bytes | **Pre-requisite:**<br><br>1.  Prometheus is setup is done and Prometheus web UI is accessible.</pre<br><br>**Test Steps:**<br><br>1.  Create 4 volumes of different sizes. (2, 3, 4, 5 Gi)</pre<br>2.  Attach 1st volume to a pod and write 1 Gi data into it.</pre<br>3.  Attach 2nd volume to a pod and don’t write into.</pre<br>4.  Leave the 3rd volume to the detached state.</pre<br>5.  Attach the 4th volume to pod and write 1.5 Gi data into it. Detach the volume.</pre<br>6.  Go to Prometheus web UI.</pre<br>7.  Select `longhorn_volume_capacity_bytes` and execute. | 1.  All the volumes should be identified by Prometheus</pre<br>2.  All the volumes should show the capacity as 2 Gi |
| 3   | longhorn\_volume\_usage\_bytes | **Pre-requisite:**<br><br>1.  Prometheus is setup is done and Prometheus web UI is accessible.</pre<br><br>**Test Steps:**<br><br>1.  Create 4 volumes of different sizes. (2, 3, 4, 5 Gi)</pre<br>2.  Attach 1st volume to a pod and write 1 Gi data into it.</pre<br>3.  Attach 2nd volume to a pod and don’t write into.</pre<br>4.  Leave the 3rd volume to the detached state.</pre<br>5.  Attach the 4th volume to pod and write 1.5 Gi data into it. Detach the volume.</pre<br>6.  Go to Prometheus web UI.</pre<br>7.  Select `longhorn_volume_usage_bytes` and execute. | 1.  All the volumes should be identified by Prometheus</pre<br>2.  Volume-1 should show 1 Gi</pre<br>3.  Volume-2 should show 0 Gi</pre<br>4.  Volume-3 should show 0 Gi</pre<br>5.  Volume-4 should show 1.5 Gi |
| 4   | longhorn\_node\_status | **Pre-requisite:**<br><br>1.  Prometheus is setup is done and Prometheus web UI is accessible.</pre<br><br>**Test Steps:**<br><br>1.  Power down a node.</pre<br>2.  Disable a node.</pre<br>3.  Add a new node in the cluster.</pre<br>4.  Delete a node from the cluster.</pre<br>5.  Go to Prometheus web UI.</pre<br>6.  Select `longhorn_node_status` and execute. | 1.  All the nodes should be identified by Prometheus and one node should be shown in 3 rows based on the condition - `mountpropagation, ready, schedulable`</pre<br>2.  The correct status should be shown on Prometheus UI. |
| 5   | longhorn\_instance\_manager\_cpu\_requests\_millicpu | **Pre-requisite:**<br><br>1.  Prometheus is setup is done and Prometheus web UI is accessible.</pre<br><br>**Test Steps:**<br><br>1.  Create a volume and attach it to a pod.</pre<br>2.  Write 1 Gi data into it.</pre<br>3.  Set multiple recurring backup on the volume.</pre<br>4.  Go to Prometheus web UI.</pre<br>5.  Select `longhorn_instance_manager_cpu_requests_millicpu` and execute. | 1.  The reading of cpu\_requests should go up for the attached instance manager.</pre<br>2.  The reading of other instance managers should not get impacted. |
| 6   | longhorn\_instance\_manager\_cpu\_usage\_millicpu | **Pre-requisite:**<br><br>1.  Prometheus is setup is done and Prometheus web UI is accessible.</pre<br><br>**Test Steps:**<br><br>1.  Create a volume and attach it to a pod.</pre<br>2.  Write 1 Gi data into it.</pre<br>3.  Set multiple recurring backup on the volume.</pre<br>4.  Go to Prometheus web UI.</pre<br>5.  Select `longhorn_instance_manager_cpu_usage_millicpu` and execute. | 1.  The reading of cpu\_usage should be shown correctly</pre<br>2.  The reading of other instance managers should not get impacted. |
| 7   | longhorn\_instance\_manager\_memory\_requests\_bytes | **Pre-requisite:**<br><br>1.  Prometheus is setup is done and Prometheus web UI is accessible.</pre<br><br>**Test Steps:**<br><br>1.  Create a volume and attach it to a pod.</pre<br>2.  Write 1 Gi data into it.</pre<br>3.  Set multiple recurring backup on the volume.</pre<br>4.  Go to Prometheus web UI.</pre<br>5.  Select `longhorn_instance_manager_memory_requests_bytes` and execute. | 1.  The reading of memory\_requests should go up for the attached instance manager.</pre<br>2.  The reading of other instance managers should not get impacted. |
| 8   | longhorn\_instance\_manager\_memory\_usage\_bytes | **Pre-requisite:**<br><br>1.  Prometheus is setup is done and Prometheus web UI is accessible.</pre<br><br>**Test Steps:**<br><br>1.  Create a volume and attach it to a pod.</pre<br>2.  Write 1 Gi data into it.</pre<br>3.  Set multiple recurring backup on the volume.</pre<br>4.  Go to Prometheus web UI.</pre<br>5.  Select `longhorn_instance_manager_memory_usage_bytes` and execute. | 1.  The reading of memory\_usage should go up for the attached instance manager.</pre<br>2.  The reading of other instance managers should not get impacted. |
| 9   | longhorn\_manager\_cpu\_usage\_millicpu | **Pre-requisite:**<br><br>1.  Prometheus is setup is done and Prometheus web UI is accessible.</pre<br><br>**Test Steps:**<br><br>1.  Create 3 volumes of different sizes.</pre<br>2.  Attach 1st volume to a pod and write 1 Gi data into it.</pre<br>3.  Leave the 2rd volume to the detached state.</pre<br>4.  Attach the 3th volume to pod and write 1.5 Gi data into it. Attach the volume in maintenance mode.</pre<br>5.  Set a recurring backup on volume 1st.</pre<br>6.  Perform revert to snapshot with 3rd volume.</pre<br>7.  Go to Prometheus web UI.</pre<br>8.  Select `longhorn_manager_cpu_usage_millicpu` and execute. | 1.  Monitor the graph and the console on the Prometheus server, the cpu\_usage should go up. |
| 10  | longhorn\_manager\_memory\_usage\_bytes | **Pre-requisite:**<br><br>1.  Prometheus is setup is done and Prometheus web UI is accessible.</pre<br><br>**Test Steps:**<br><br>1.  Create 3 volumes of different sizes.</pre<br>2.  Attach 1st volume to a pod and write 1 Gi data into it.</pre<br>3.  Leave the 2rd volume to the detached state.</pre<br>4.  Attach the 3th volume to pod and write 1.5 Gi data into it. Attach the volume in maintenance mode.</pre<br>5.  Set a recurring backup on volume 1st.</pre<br>6.  Perform revert to snapshot with 3rd volume.</pre<br>7.  Try to make disk full of a node where `longhorn-manager` is running.</pre<br>8.  Go to Prometheus web UI.</pre<br>9.  Select `longhorn_manager_memory_usage_bytes` and execute. | 1.  Monitor the graph and the console on the Prometheus server, the memory\_usage should go up. |
| 11  | longhorn\_disk\_capacity\_bytes | **Pre-requisite:**<br><br>1.  Prometheus is setup is done and Prometheus web UI is accessible.</pre<br><br>**Test Steps:**<br><br>1.  Create volumes and attach them to each node.</pre<br>2.  Add an additional disk to all the nodes. (Different size)</pre<br>3.  Write into the volumes.</pre<br>4.  Power down a node.</pre<br>5.  Disable a node.</pre<br>6.  Add a new node in the cluster.</pre<br>7.  Delete a node from the cluster.</pre<br>8.  Go to Prometheus web UI.</pre<br>9.  Select `longhorn_disk_capacity_bytes` and execute. | 1.  All the disks should be identified by Prometheus.</pre<br>2.  All the disks should show the correct total size of the disks. |
| 12  | longhorn\_disk\_usage\_bytes | **Pre-requisite:**<br><br>1.  Prometheus is setup is done and Prometheus web UI is accessible.</pre<br><br>**Test Steps:**<br><br>1.  Create volumes and attach them to each node.</pre<br>2.  Add an additional disk to all the nodes. (Different size)</pre<br>3.  Write into the volumes.</pre<br>4.  Power down a node.</pre<br>5.  Disable a node.</pre<br>6.  Add a new node in the cluster.</pre<br>7.  Delete a node from the cluster.</pre<br>8.  Go to Prometheus web UI.</pre<br>9.  Select `longhorn_disk_usage_bytes` and execute. | 1.  All the disks should be identified by Prometheus.</pre<br>2.  All the disks should show the occupied size of the disks. |
| 13  | longhorn\_node\_capacity\_bytes | **Pre-requisite:**<br><br>1.  Prometheus is setup is done and Prometheus web UI is accessible.</pre<br><br>**Test Steps:**<br><br>1.  Create volumes and attach them to each node.</pre<br>2.  Add an additional disk to all the nodes. (Different size)</pre<br>3.  Write into the volumes.</pre<br>4.  Power down a node.</pre<br>5.  Disable a node.</pre<br>6.  Add a new node in the cluster.</pre<br>7.  Delete a node from the cluster.</pre<br>8.  Go to Prometheus web UI.</pre<br>9.  Select `longhorn_node_capacity_bytes` and execute. | 1.  All the nodes should be identified by Prometheus.</pre<br>2.  All the nodes should show the total capacity available of disks available. |
| 14  | longhorn\_node\_usage\_bytes | **Pre-requisite:**<br><br>1.  Prometheus is setup is done and Prometheus web UI is accessible.</pre<br><br>**Test Steps:**<br><br>1.  Create volumes and attach them to each node.</pre<br>2.  Add an additional disk to all the nodes. (Different size)</pre<br>3.  Write into the volumes.</pre<br>4.  Power down a node.</pre<br>5.  Disable a node.</pre<br>6.  Add a new node in the cluster.</pre<br>7.  Delete a node from the cluster.</pre<br>8.  Go to Prometheus web UI.</pre<br>9.  Select `longhorn_node_usage_bytes` and execute. | 1.  All the nodes should be identified by Prometheus</pre<br>2.  All the nodes should show the occupied space on all disks attached to the node. |

Note: More details can be found on https://longhorn.io/docs/1.2.2/monitoring/