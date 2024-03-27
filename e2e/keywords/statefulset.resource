*** Settings ***
Documentation    StatefulSet Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/statefulset_keywords.py

*** Keywords ***
#TODO
# these functions can be merged into workload.resource
Create statefulset ${statefulset_id} using ${volume_type} volume
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    create_statefulset    ${statefulset_name}    ${volume_type}

Create statefulset ${statefulset_id} using ${volume_type} volume with ${option} storageclass
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    create_statefulset    ${statefulset_name}    ${volume_type}    ${option}

Scale statefulset ${statefulset_id} to ${replicaset_size}
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    scale_statefulset    ${statefulset_name}    ${replicaset_size}

Scale down statefulset ${statefulset_id} to detach volume
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    scale_statefulset_down    ${statefulset_name}

Scale up statefulset ${statefulset_id} to attach volume
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    scale_statefulset_up    ${statefulset_name}

Expand statefulset ${statefulset_id} volume by ${size} MiB
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    expand_workload_claim_size_by_mib    ${statefulset_name}    ${size}

Write ${size} MB data to file ${file_name} in statefulset ${statefulset_id}
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    write_workload_pod_random_data    ${statefulset_name}    ${size}    ${file_name}

Check statefulset ${statefulset_id} works
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    write_workload_pod_random_data    ${statefulset_name}    1024    random-data
    check_workload_pod_data_checksum    ${statefulset_name}    random-data

Check statefulset ${statefulset_id} data in file ${file_name} is intact
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    check_workload_pod_data_checksum    ${statefulset_name}    ${file_name}

Wait for statefulset ${statefulset_id} volume size expanded
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    wait_for_workload_claim_size_expanded    ${statefulset_name}

Wait for statefulset ${statefulset_id} volume detached
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    wait_for_workload_volume_detached    ${statefulset_name}

Wait for statefulset ${statefulset_id} pods stable
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    wait_for_workload_pods_stable   ${statefulset_name}
