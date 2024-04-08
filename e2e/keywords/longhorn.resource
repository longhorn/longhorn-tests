*** Settings ***
Documentation       Longhorn Keywords

Library             ../libs/keywords/instancemanager_keywords.py
Library             ../libs/keywords/workload_keywords.py

*** Variables ***
@{longhorn_workloads}
...    csi-attacher
...    csi-provisioner
...    csi-resizer
...    csi-snapshotter
...    longhorn-driver-deployer
...    longhorn-csi-plugin
...    longhorn-manager
...    longhorn-ui

*** Keywords ***
Wait for longhorn ready
    wait_for_all_instance_manager_running
    wait_for_workloads_pods_running    ${longhorn_workloads}    longhorn-system
