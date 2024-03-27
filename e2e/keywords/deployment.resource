*** Settings ***
Documentation    Deployment Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/deployment_keywords.py

*** Keywords ***
#TODO
# these functions can be merged into workload.resource
Create deployment ${deployment_id} with persistentvolumeclaim ${claim_id}
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    create_deployment    ${deployment_name}    ${claim_name}

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
