*** Settings ***
Documentation    Deployment Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/deployment_keywords.py
Library    ../libs/keywords/node_keywords.py
Library    ../libs/keywords/workload_keywords.py
Library    ../libs/keywords/volume_keywords.py

*** Keywords ***
Create deployment ${deployment_id} with persistentvolumeclaim ${claim_id}
    [Arguments]    &{config}
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    create_deployment    ${deployment_name}    ${claim_name}    &{config}

Create deployment ${deployment_id} with block persistentvolumeclaim ${claim_id}
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    create_deployment    ${deployment_name}    ${claim_name}    block_volume=True

Create deployment ${deployment_id} with persistentvolumeclaim ${claim_id} and liveness probe
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    create_deployment    ${deployment_name}    ${claim_name}    enable_pvc_io_and_liveness_probe=${True}

Create deployment ${deployment_id} with persistentvolumeclaim ${claim_id} with max replicaset
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    ${node_names} =    list_node_names_by_role    worker
    ${node_count} =    Get length  ${node_names}
    create_deployment    ${deployment_name}    ${claim_name}   ${node_count}

Create deployment ${deployment_id} with volume ${volume_id}
    ${volume_id}=  Convert To String  ${volume_id}
    Create persistentvolume for volume ${volume_id}
    Create persistentvolumeclaim for volume ${volume_id}
    ${deployment_name}=    generate_name_with_suffix    deployment    ${deployment_id}
    ${pvc_name}=    generate_name_with_suffix    volume    ${volume_id}
    create_deployment    ${deployment_name}   ${pvc_name}

Create deployment ${deployment_id} using volume ${volume_id}
    [Arguments]    ${num_replicaset}

    ${node_count} =    Set Variable    3
    IF    '${num_replicaset}' == 'max'
        ${node_names} =    list_node_names_by_role    worker
        ${node_count} =    Get length  ${node_names}
    ELSE IF    '${num_replicaset}' != ''
        ${node_count} =    Convert To Integer    ${num_replicaset}
    END

    ${claim_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    create_deployment    ${deployment_name}    ${claim_name}   ${node_count}

Delete deployment ${deployment_id}
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    delete_deployment    ${deployment_name}

Make block device filesystem in deployment ${deployment_id}
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    make_block_device_filesystem_in_workload_pod    ${deployment_name}

Mount block device on ${mount_point} in deployment ${deployment_id}
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    mount_block_device_in_workload_pod    ${deployment_name}    ${mount_point}

Write ${size} MB data to file ${file_name} in deployment ${deployment_id}
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    write_workload_pod_random_data    ${deployment_name}    ${size}    ${file_name}

And Write ${size} MB data to block device in deployment ${deployment_id} and check data is intact
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    write_and_check_workload_pod_random_data_to_block_device    ${deployment_name}    ${size}

Check deployment ${deployment_id} data in file ${file_name} is intact
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    check_workload_pod_data_checksum    ${deployment_name}    ${file_name}

Check deployment ${deployment_id} works    
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    write_workload_pod_random_data    ${deployment_name}    1024    random-data
    check_workload_pod_data_checksum    ${deployment_name}    random-data

Check all deployment ${deployment_id} replica pods are working
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    write_and_check_all_workload_pod_random_data    ${deployment_name}    1024    random-data

Wait for deployment ${deployment_id} pods stable
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    wait_for_workload_pods_stable   ${deployment_name}

Get deployment ${deployment_id} pod name
    ${deployment_name} =   generate_name_with_suffix    deployment    ${deployment_id}
    ${pod_name} =    get_workload_pod_name    ${deployment_name}
    Set Test Variable    ${pod_name}

Check deployment ${deployment_id} pod not restarted
    ${deployment_name} =   generate_name_with_suffix    deployment    ${deployment_id}
    ${current_pod_name} =    get_workload_pod_name    ${deployment_name}
    Should Be Equal    ${pod_name}    ${current_pod_name}

Scale deployment ${deployment_id} to ${replicaset_size}
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    scale_deployment    ${deployment_name}    ${replicaset_size}

Scale down deployment ${deployment_id} to detach volume
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    ${volume_name} =    get_workload_volume_name    ${deployment_name}
    scale_deployment    ${deployment_name}    0
    wait_for_volume_detached    ${volume_name}

Scale up deployment ${deployment_id} to attach volume
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    ${volume_name} =    get_workload_volume_name    ${deployment_name}
    scale_deployment    ${deployment_name}    1
    wait_for_volume_attached    ${volume_name}

Wait for deployment ${deployment_id} volume size expanded
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    wait_for_workload_claim_size_expanded    ${deployment_name}
