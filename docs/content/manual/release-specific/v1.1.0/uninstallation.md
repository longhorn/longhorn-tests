---
title: Test uninstallation
---
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
