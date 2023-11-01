*** Settings ***
Documentation    Workload Keywords

Library    Collections
Library    ../libs/keywords/workload_keywords.py
Library    ../libs/keywords/persistent_volume_claim_keywords.py

*** Keywords ***
Create deployment ${idx} with ${volume_type} volume
    ${deployment_name} =    create_deployment    ${volume_type}
    Insert Into List    ${deployment_list}    ${idx}    ${deployment_name}

Create statefulset ${idx} with ${volume_type} volume
    ${statefulset_name} =    create_statefulset    ${volume_type}
    Insert Into List    ${statefulset_list}    ${idx}    ${statefulset_name}

    ${volume_name} =    get_workload_volume_name    ${statefulset_name}
    Insert Into List    ${volume_list}    ${idx}    ${volume_name}

    ${pvc_name} =    get_workload_pvc_name    ${statefulset_name}
    Insert Into List    ${persistentvolumeclaim_list}    ${idx}    ${pvc_name}

Scale down statefulset ${idx} to detach volume
    ${statefulset} =    get_statefulset    ${statefulset_list}[${idx}]
    ${scale_up_replica_count} =   Set Variable    ${statefulset.spec.replicas}
    Set Test Variable   ${scale_up_replica_count}

    scale_statefulset    ${statefulset_list}[${idx}]    0
    wait_for_volume_detached    ${volume_list}[${idx}]

Scale up statefulset ${idx} to attach volume
    scale_statefulset    ${statefulset_list}[${idx}]    ${scale_up_replica_count}
    wait_for_volume_healthy    ${volume_list}[${idx}]
    wait_for_statefulset_replicas_ready    ${statefulset_list}[${idx}]    ${scale_up_replica_count}

Create deployment ${idx} with ${volume_type} and ${option} volume
    ${deployment_name} =    create_deployment    ${volume_type}    ${option}
    Insert Into List    ${deployment_list}    ${idx}    ${deployment_name}

Create statefulset ${idx} with ${volume_type} and ${option} volume
    ${statefulset_name} =    create_statefulset    ${volume_type}    ${option}
    Insert Into List    ${statefulset_list}    ${idx}    ${statefulset_name}

Expand statefulset ${idx} volume by ${size} MiB
    ${expected_size} =     expand_pvc_size_by_mib    ${persistentvolumeclaim_list}[${idx}]    ${size}
    Set Test Variable    ${expected_size}

Write ${size} MB data to statefulset ${idx}
    ${pod_name} =    get_workload_pod_name    ${statefulset_list}[${idx}]
    ${pod_data_checksum} =    write_pod_random_data    ${pod_name}    ${size}
    Insert Into List    ${data_checksum_list}    ${idx}    ${pod_data_checksum}

Keep writing data to deployment ${idx}
    ${pod_name} =    get_workload_pod_name    ${deployment_list}[${idx}]
    keep_writing_pod_data    ${pod_name}

Keep writing data to statefulset ${idx}
    ${pod_name} =    get_workload_pod_name    ${statefulset_list}[${idx}]
    keep_writing_pod_data    ${pod_name}

Check deployment ${idx} works
    ${pod_name} =    get_workload_pod_name    ${deployment_list}[${idx}]
    ${pod_data_checksum} =    write_pod_random_data    ${pod_name}    1024
    check_pod_data_checksum    ${pod_name}    ${pod_data_checksum}

Check statefulset ${idx} works
    ${pod_name} =    get_workload_pod_name    ${statefulset_list}[${idx}]
    ${pod_data_checksum} =    write_pod_random_data    ${pod_name}    1024
    check_pod_data_checksum    ${pod_name}    ${pod_data_checksum}

Check statefulset ${idx} data is intact
    ${pod_name} =    get_workload_pod_name    ${statefulset_list}[${idx}]
    ${expected_data_checksum} =     Get From List    ${data_checksum_list}    ${idx}
    check_pod_data_checksum    ${pod_name}    ${expected_data_checksum}

Wait for statefulset ${idx} volume size expanded
    wait_for_volume_expand_to_size    ${volume_list}[${idx}]    ${expected_size}

Wait for statefulset ${idx} stable
    wait_for_workload_pod_stable   ${statefulset_list}[${idx}]

