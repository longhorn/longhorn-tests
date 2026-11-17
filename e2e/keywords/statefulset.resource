*** Settings ***
Documentation    StatefulSet Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/statefulset_keywords.py
Library    ../libs/keywords/volume_keywords.py

*** Keywords ***
Create statefulset ${statefulset_id} using ${volume_type} volume
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    create_statefulset    ${statefulset_name}    ${volume_type}

Create statefulset ${statefulset_id} using ${volume_type} volume with ${sc_name} storageclass
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    create_statefulset    ${statefulset_name}    ${volume_type}    ${sc_name}

Create statefulset ${statefulset_id} using ${volume_type} volume with ${sc_name} storageclass and size ${size} Mi
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    create_statefulset    ${statefulset_name}    ${volume_type}    ${sc_name}    ${size}Mi

Create statefulset ${statefulset_id} using ${volume_type} volume with ${sc_name} storageclass and size ${size} Gi
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    create_statefulset    ${statefulset_name}    ${volume_type}    ${sc_name}    ${size}Gi

Create statefulset ${statefulset_id}
    [Arguments]    &{config}
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    create_statefulset    ${statefulset_name}    &{config}

Scale statefulset ${statefulset_id} to ${replicaset_size}
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    scale_statefulset    ${statefulset_name}    ${replicaset_size}

Scale down statefulset ${statefulset_id} to detach volume
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    scale_statefulset_down    ${statefulset_name}

Scale up statefulset ${statefulset_id} to attach volume
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    scale_statefulset_up    ${statefulset_name}

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

Wait for statefulset ${statefulset_id} volume attached
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    wait_for_workload_volume_attached    ${statefulset_name}

Wait for statefulset ${statefulset_id} pods stable
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    wait_for_workload_pods_stable   ${statefulset_name}

Wait for statefulset ${statefulset_id} to have ${count} ready replicas
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    wait_for_statefulset_replicas_ready    ${statefulset_name}    ${count}

Get volume of statefulset ${statefulset_id} pod ${ordinal}
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    ${volume_name} =    get_statefulset_pod_volume_name    ${statefulset_name}    ${ordinal}
    RETURN    ${volume_name}

Wait for volumes of statefulset ${statefulset_id} to have replicas on ${node_count} different nodes
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    wait_for_statefulset_volume_replicas_on_nodes    ${statefulset_name}    ${node_count}

Wait for volumes of statefulset ${statefulset_id} to have no replica on node ${node_id}
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    ${node_name} =    get_node_by_index    ${node_id}
    wait_for_statefulset_volume_replicas_off_node    ${statefulset_name}    ${node_name}

Get volume of statefulset ${statefulset_id} on node ${node_id}
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${volume_name} =    get_statefulset_volume_on_node    ${statefulset_name}    ${node_name}
    RETURN    ${volume_name}

Wait for volumes of statefulset ${statefulset_id} detached
    ${statefulset_name} =    generate_name_with_suffix    statefulset    ${statefulset_id}
    wait_for_statefulset_volumes_detached    ${statefulset_name}
