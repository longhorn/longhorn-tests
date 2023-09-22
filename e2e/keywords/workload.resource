*** Settings ***
Documentation    Workload Keywords

Library    Collections
Library    ../libs/keywords/workload_keywords.py

*** Keywords ***
Create deployment ${idx} with ${volume_type} volume
    ${deployment_name} =    create_deployment    ${volume_type}
    Insert Into List    ${deployment_list}    ${idx}    ${deployment_name}

Create statefulset ${idx} with ${volume_type} volume
    ${statefulset_name} =    create_statefulset    ${volume_type}
    Insert Into List    ${statefulset_list}    ${idx}    ${statefulset_name}

Create deployment ${idx} with ${volume_type} and ${option} volume
    ${deployment_name} =    create_deployment    ${volume_type}    ${option}
    Insert Into List    ${deployment_list}    ${idx}    ${deployment_name}

Create statefulset ${idx} with ${volume_type} and ${option} volume
    ${statefulset_name} =    create_statefulset    ${volume_type}    ${option}
    Insert Into List    ${statefulset_list}    ${idx}    ${statefulset_name}

Keep writing data to deployment ${idx}
    ${pod_name} =    get_workload_pod_name    ${deployment_list}[${idx}]
    keep_writing_pod_data    ${pod_name}

Keep writing data to statefulset ${idx}
    ${pod_name} =    get_workload_pod_name    ${statefulset_list}[${idx}]
    keep_writing_pod_data    ${pod_name}

Check deployment ${idx} works
    ${pod_name} =    get_workload_pod_name    ${deployment_list}[${idx}]
    ${pod_data_checksum} =    write_pod_random_data    ${pod_name}    1024
    check_pod_data    ${pod_name}    ${pod_data_checksum}

Check statefulset ${idx} works
    ${pod_name} =    get_workload_pod_name    ${statefulset_list}[${idx}]
    ${pod_data_checksum} =    write_pod_random_data    ${pod_name}    1024
    check_pod_data    ${pod_name}    ${pod_data_checksum}

Wait for statefulset ${idx} stable
    wait_for_workload_pod_stable   ${statefulset_list}[${idx}]
