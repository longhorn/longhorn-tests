*** Settings ***
Documentation    Deployment Keywords

Library    Collections
Library    ../libs/keywords/deployment_keywords.py

*** Keywords ***
Create deployment ${idx} with ${volume_type} volume
    ${deployment_name} =    create_deployment    ${volume_type}
    Insert Into List    ${deployment_list}    ${idx}    ${deployment_name}

Create deployment ${idx} with ${volume_type} and ${option} volume
    ${deployment_name} =    create_deployment    ${volume_type}    ${option}
    Insert Into List    ${deployment_list}    ${idx}    ${deployment_name}

Keep writing data to deployment ${idx}
    ${pod_name} =    get_workload_pod_name    ${deployment_list}[${idx}]
    keep_writing_pod_data    ${pod_name}

Check deployment ${idx} works
    ${pod_name} =    get_workload_pod_name    ${deployment_list}[${idx}]
    ${pod_data_checksum} =    write_pod_random_data    ${pod_name}    1024
    check_pod_data_checksum    ${pod_name}    ${pod_data_checksum}
