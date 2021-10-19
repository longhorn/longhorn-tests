---
title: 2. UI
---

Accessibility of Longhorn UI
----------------------------

| **#**   | **Test Case** | **Test Instructions** |
| --- | --- | --- |
| 1.  | Access Longhorn UI using rancher proxy | 1.  Create a cluster (3 worker nodes and 1 etcd/control plane) in rancher, Go to the default project.<br>2.  Go to App, Click the launch app.<br>3.  Select longhorn.<br>4.  Select `Rancher-Proxy` under the Longhorn UI service.<br>5.  Once the app is deployed successfully, click the [/index.html](https://173.255.255.35/k8s/clusters/c-qnl4b/api/v1/namespaces/longhorn-system/services/http:longhorn-frontend:80/proxy/) link appears in App page.<br>6.  The page should redirect to longhorn UI - [https://rancher/k8s/clusters/c-aaaa/api/v1/namespaces/longhorn-system/services/http:longhorn-frontend:80/proxy/#/dashboard](https://173.255.255.35/k8s/clusters/c-qnl4b/api/v1/namespaces/longhorn-system/services/http:longhorn-frontend:80/proxy/#/dashboard)<br>7.  Verify all the pages, refresh each page and verify. Create a volume and check the volume detail page also. |
| 2.  | Access Longhorn UI under Kubectl proxy | 1.  Create a cluster (3 worker nodes and 1 etcd/control plane) using rke.<br>2.  Start kubectl proxy by command `kubectl proxy`.<br>3.  It should start proxy locally on 8001 port.<br>4.  Navigate to [http://localhost:8001/api/v1/namespaces/longhorn-system/services/http:longhorn-frontend:http/proxy/](http://localhost:8001/api/v1/namespaces/longhorn-system/services/http:longhorn-frontend:http/proxy/)<br>5.  The above link should open the longhorn UI.<br>6.  Verify all the pages, refresh each page and verify. Create a volume and check the volume detail page also. |
| 3.  | Access Longhorn UI with node port | 1.  Create a cluster (3 worker nodes and 1 etcd/control plane) in rancher, Go to the default project.<br>2.  Go to App, Click the launch app.<br>3.  Select longhorn.<br>4.  Select `NodePort` under the Longhorn UI service.<br>5.  Once the app is deployed successfully, click the link like [32059/tcp](http://104.131.80.163:32059/) appears in App page.<br>6.  The page should redirect to longhorn UI - [http://node-ip:32059/#/dashboard](http://104.131.80.163:32059/#/dashboard)<br>7.  Verify all the pages, refresh each page and verify. Create a volume and check the volume detail page also. |
| 4.  | Access Longhorn UI with ingress controller | 1.  Create a cluster(3 worker nodes and 1 etcd/control plane).<br>2.  Deploy longhorn.<br>3.  Create ingress controller. refer [https://longhorn.io/docs/1.0.1/deploy/accessing-the-ui/longhorn-ingress/](https://longhorn.io/docs/1.0.1/deploy/accessing-the-ui/longhorn-ingress/)<br>4.  If cluster is imported/created in rancher create ingress using rancher UI by selecting `Target Backend` as `longhorn frontend` and path `/`<br>5.  Access the ingress. It should redirect to longhorn UI.<br>6.  Verify all the pages, refresh each page and verify. Create a volume and check the volume detail page also. |
| 5.  | Access Longhorn UI with a load balancer | 1.  Create a cluster (3 worker nodes and 1 etcd/control plane) in rancher.<br>2.  Create a route 53 entry pointing to worker nodes of the cluster in AWS.<br>3.  Deploy longhorn from catalog library and mention the route 53 entry in the load balancer.<br>4.  Go to the link that appears on the app page for the longhorn app.<br>5.  The page to redirect to longhorn UI with URL as route 53 entry.<br>6.  Verify all the pages, refresh each page and verify. Create a volume and check the volume detail page also.
| 6.  | Access Longhorn UI with reverse proxy | 1.  Create a cluster (3 worker nodes and 1 etcd/control plane) in rancher, Go to the default project.<br>2.  Go to App, Click the launch app.<br>3.  Select longhorn.<br>4.  Select `NodePort` under the Longhorn UI service.<br>5.  Install nginx in local system.<br>6.  Set the `proxy_pass` of [http://node-ip:32059](http://104.131.80.163:32059/#/dashboard) in ngnix.conf file as per below example.<br>7.  Start nginx<br>8.  Access the port given in `listen` parameter from nginx.conf. ex - //localhost:822<br>9.  The page should redirect to longhorn UI<br>10.  Verify all the pages, refresh each page and verify. Create a volume and check the volume detail page also.

nginx.conf example
        
    `events { worker_connections` `1024``; }`
    
    `http {`
    
    `server {`
    
    `gzip on;`
    
    `gzip_min_length 1k;`
    
    `gzip_comp_level` `2``;`
    
    `gzip_types text/plain application/javascript application/x-javascript text/css application/xml text/javascript application/x-httpd-php image/jpeg image/gif image/png image/svg+xml;`
    
    `gzip_vary on;`
    
    `gzip_disable` `"MSIE [1-6]\."``;`
    
    `listen` `8223``;`
    
    `proxy_http_version` `1.1``;`
    
    `proxy_set_header Upgrade $http_upgrade;`
    
    `proxy_set_header Connection` `"upgrade"``;`
    
    `proxy_redirect   off;`
    
    `proxy_set_header  Host       $http_host;`
    
    `proxy_set_header  X-Real-IP    $remote_addr;`
    
    `proxy_set_header  X-Forwarded-For $proxy_add_x_forwarded_for;`
    
    `proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;`
    
    `proxy_max_temp_file_size` `0``;`
    
    `proxy_connect_timeout  ` `90``;`
    
    `proxy_send_timeout    ` `90``;`
    
    `proxy_read_timeout    ` `90``;`
    
    `proxy_buffer_size     1024k;`
    
    `proxy_buffers      ` `8` `1024k;`
    
    `proxy_busy_buffers_size  1024k;`
    
    `proxy_temp_file_write_size 1024k;`
    
    `location / {`
    
    `proxy_pass` `"[http://node-ip:32059/](http://node-ip:32059/)"``;`
    
    `}`
    
    `}`
    
    `}`
    
    
Dashboard
---------

1.  Make sure the volume diagram matches the volume list page
    
2.  Make sure the storage diagram matches the node list page
    
3.  Make sure the node diagram matches the node list page
    
4.  Make sure the event log shows up.
    

| **#**   | **Test Case** | **Test Instructions** | **Expected Results** | 
| --- | --- | --- | --- |
| 1   | Volume Diagram | *   Verify Volume Diagram | *   At all time, Volume Diagram should correctly reflect the number and state of Longhorn Volumes (Healthy, Degraded, In Progress, Fault, Detached) |
| 2   | Storage Diagram | *   Verify Storage Diagram | *   At all time, Storage Diagram should correctly reflect Disks Storage status (Schedulable, Reserved, Used, Disabled) |
| 3   | Node Diagram | *   Verify Node Diagram | *   At all time, Volume Diagram should correctly reflect the number and state of Longhorn Nodes (Schedulable, Unschedulable, Down, Disabled) |
| 4   | Event Logs | *   Verify Event Logs | *   Make sure Longhorn events shows up in Event Logs. |
| 5   | Longhorn Version | *   Verify the version | *   Make sure the version is correct|
| 6   | Support Bundle Link | *   Click the SupportBundle link | *   A pop up to enter issue id and description should appear.<br>*   On saving the form, the support bundle file should be generated and downloaded |
| 7   | Other links at bottom of the page | *   Click links Documentation, File an issue and Slack | *   Make sure the navigation of the Document, File an issue and Slack are correct. |

Additional Tests
----------------

| **Test case** | **Steps** | **Expected Results** |
| --- | --- | --- |
| Sort in the columns | Verify sorting happens correctly in the columns |
| Filter | Verify Filter on different columns work |
