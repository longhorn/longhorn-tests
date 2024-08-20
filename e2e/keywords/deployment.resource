*** Settings ***
Documentation    Deployment Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/deployment_keywords.py
Library    ../libs/keywords/node_keywords.py
Library    ../libs/keywords/workload_keywords.py

*** Keywords ***
Create deployment ${deployment_id} with persistentvolumeclaim ${claim_id}
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    create_deployment    ${deployment_name}    ${claim_name}

Create deployment ${deployment_id} with persistentvolumeclaim ${claim_id} with max replicaset
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    ${node_names} =    list_node_names_by_role    worker
    ${node_count} =    Get length  ${node_names}
    create_deployment    ${deployment_name}    ${claim_name}   ${node_count}

Delete deployment ${deployment_id}
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    delete_deployment    ${deployment_name}

Write ${size} MB data to file ${file_name} in deployment ${deployment_id}
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    write_workload_pod_random_data    ${deployment_name}    ${size}    ${file_name}

Check deployment ${deployment_id} data in file ${file_name} is intact
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    check_workload_pod_data_checksum    ${deployment_name}    ${file_name}

Check deployment ${deployment_id} works
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    write_workload_pod_random_data    ${deployment_name}    1024    random-data
    check_workload_pod_data_checksum    ${deployment_name}    random-data

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