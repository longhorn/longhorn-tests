*** Settings ***
Documentation       Longhorn engine image related keywords

Library             String
Library             ../libs/keywords/common_keywords.py
Library             ../libs/keywords/engine_image_keywords.py
Library             ../libs/keywords/workload_keywords.py

*** Keywords ***
Create compatible engine image
    ${compatible_engine_image_name} =    deploy_compatible_engine_image
    Set Test Variable    ${compatible_engine_image_name}

Wait to engine image ${custom_engine_image} to be deployed
    wait_for_engine_image_deployed    ${custom_engine_image}

Wait for engine image daemonset pods recreated and running
    ${longhorn_namespace} =    get_longhorn_namespace
    ${output}=    Run Command
    ...    kubectl -n longhorn-system get ds -l longhorn.io/component=engine-image --no-headers -o custom-columns=NAME:.metadata.name
    @{ds_names}=    Split To Lines    ${output}
    FOR    ${ds_name}    IN    @{ds_names}
        wait_for_workload_pods_recreated    ${ds_name}    daemonset    ${longhorn_namespace}
        Run command and wait for output
        ...    kubectl -n ${longhorn_namespace} get pods | grep ${ds_name} | grep -c Running
        ...    3
    END
