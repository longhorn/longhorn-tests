---
title: Test uninstallation
---
## Stability of uninstallation
1. Launch Longhorn system.
2. Use scripts to continuously create then delete multiple DaemonSets. 
    - e.g., putting the following python test into the manager integration test directory and run it:
    ```
    from common import get_apps_api_client # NOQA
    
    
    def test_uninstall_script():
        apps_api = get_apps_api_client()
        while True:
            for i in range(10):
                name = "ds-" + str(i)
                try:
                    ds = apps_api.read_namespaced_daemon_set(name, "default")
                    if ds.status.number_ready == ds.status.number_ready:
                        apps_api.delete_namespaced_daemon_set(name, "default")
                except Exception:
                    apps_api.create_namespaced_daemon_set(
                        "default", ds_manifest(name))
    
    
    def ds_manifest(name):
        return {
            'apiVersion': 'apps/v1',
            'kind': 'DaemonSet',
            'metadata': {
                'name': name
            },
            'spec': {
                'selector': {
                    'matchLabels': {
                        'app': name
                    }
                },
                'template': {
                    'metadata': {
                        'labels': {
                            'app': name
                        }
                    },
                    'spec': {
                        'terminationGracePeriodSeconds': 10,
                        'containers': [{
                            'image': 'busybox',
                            'imagePullPolicy': 'IfNotPresent',
                            'name': 'sleep',
                            'args': [
                                '/bin/sh',
                                '-c',
                                'while true;do date;sleep 5; done'
                            ],
                        }]
                    }
                },
            }
        }
    ```

3. Start to uninstall longhorn.
4. Check if the uninstaller pod gets stuck there

## Performance improvement of uninstallation
1. Install Longhorn v1.1.0 on a 4 nodes cluster (1 etcd/control plane and 3 workers).
2. Uninstall longhorn v1.1.0.
3. Uninstallation should be completed somewhere between ~(1-2) min which was observed between ~(2-3) min in similar set up with Longhorn v1.0.2.
4. There should not be repeated log messages like below:
    ```
    time="2020-07-31T20:25:54Z" level=info msg="2 instance managers remaining"
    time="2020-07-31T20:25:55Z" level=info msg="2 instance managers remaining"
    time="2020-07-31T20:25:56Z" level=info msg="2 instance managers remaining"
    time="2020-07-31T20:25:57Z" level=info msg="2 instance managers remaining"
    time="2020-07-31T20:25:58Z" level=info msg="2 instance managers remaining"
    time="2020-07-31T20:25:59Z" level=info msg="2 instance managers remaining"
    time="2020-07-31T20:25:59Z" level=info msg="2 instance managers remaining"
    time="2020-07-31T20:26:00Z" level=info msg="2 instance managers remaining"
    time="2020-07-31T20:26:01Z" level=info msg="2 instance managers remaining"
    time="2020-07-31T20:26:02Z" level=info msg="2 instance managers remaining"
    time="2020-07-31T20:26:02Z" level=info msg="2 instance managers remaining"
    time="2020-07-31T20:26:03Z" level=info msg="2 instance managers remaining"
    time="2020-07-31T20:26:04Z" level=info msg="2 instance managers remaining"
    ```
5. Also, Below logs should not be present anymore:
    ```
    time="2020-08-06T18:35:05Z" level=debug msg="Instance Manager Controller longhorn-node-1 picked up instance-manager-e-1e97de2b"
    time="2020-08-06T18:35:05Z" level=debug msg="Instance Manager Controller longhorn-node-1 picked up instance-manager-e-b7b0e26c"
    time="2020-08-06T18:35:07Z" level=debug msg="Instance Manager Controller longhorn-node-1 picked up instance-manager-e-c597a586"
    time="2020-08-06T18:35:07Z" level=debug msg="Instance Manager Controller longhorn-node-1 picked up instance-manager-e-1e97de2b"
    time="2020-08-06T18:35:08Z" level=debug msg="Instance Manager Controller longhorn-node-1 picked up instance-manager-e-b7b0e26c"
    time="2020-08-06T18:35:09Z" level=debug msg="Instance Manager Controller longhorn-node-1 picked up instance-manager-e-c597a586"
    time="2020-08-06T18:35:10Z" level=debug msg="Instance Manager Controller longhorn-node-1 picked up instance-manager-e-1e97de2b"
    time="2020-08-06T18:35:10Z" level=warning msg="Can't find instance manager for pod instance-manager-r-fea32bbc, may be deleted"
    time="2020-08-06T18:35:10Z" level=warning msg="Can't find instance manager for pod instance-manager-r-fea32bbc, may be deleted"
    time="2020-08-06T18:35:10Z" level=error msg="failed to mark existing instances to error when stopping instance manager monitor: failed to update instance map for instance manager instance-manager-e-1e97de2b: Operation cannot be fulfilled on instancemanagers.longhorn.io \"instance-manager-e-1e97de2b\": the object has been modified; please apply your changes to the latest version and try again"
    time="2020-08-06T18:35:10Z" level=debug msg="Instance Manager Controller longhorn-node-1 picked up instance-manager-e-b7b0e26c"
    time="2020-08-06T18:35:11Z" level=debug msg="Instance Manager Controller longhorn-node-1 picked up instance-manager-e-1e97de2b"
    time="2020-08-06T18:35:12Z" level=debug msg="Instance Manager Controller longhorn-node-1 picked up instance-manager-e-c597a586"
    time="2020-08-06T18:35:13Z" level=debug msg="Instance Manager Controller longhorn-node-1 picked up instance-manager-e-b7b0e26c"
    time="2020-08-06T18:35:14Z" level=debug msg="Instance Manager Controller longhorn-node-1 picked up instance-manager-e-1e97de2b"
    time="2020-08-06T18:35:15Z" level=debug msg="Instance Manager Controller longhorn-node-1 picked up instance-manager-e-c597a586"
    time="2020-08-06T18:35:15Z" level=debug msg="Instance Manager Controller longhorn-node-1 picked up instance-manager-e-b7b0e26c"
    time="2020-08-06T18:35:16Z" level=debug msg="Instance Manager Controller longhorn-node-1 picked up instance-manager-e-1e97de2b"
    time="2020-08-06T18:35:16Z" level=debug msg="Instance Manager Controller longhorn-node-1 picked up instance-manager-e-c597a586"
    time="2020-08-06T18:35:17Z" level=error msg="failed to mark existing instances to error when stopping instance manager monitor: failed to update instance map for instance manager instance-manager-e-c597a586: Operation cannot be fulfilled on instancemanagers.longhorn.io \"instance-manager-e-c597a586\": the object has been modified; please apply your changes to the latest version and try again"
    time="2020-08-06T18:35:18Z" level=debug msg="Instance Manager Controller longhorn-node-1 picked up instance-manager-e-b7b0e26c"
    time="2020-08-06T18:35:19Z" level=debug msg="Instance Manager Controller longhorn-node-1 picked up instance-manager-e-1e97de2b"
    ```
