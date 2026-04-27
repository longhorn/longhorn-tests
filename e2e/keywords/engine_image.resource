*** Settings ***
Documentation       Longhorn engine image related keywords

Library             String
Library             ../libs/keywords/engine_image_keywords.py
Resource            workload.resource

*** Keywords ***
Create compatible engine image
    ${compatible_engine_image_name} =    deploy_compatible_engine_image
    Set Test Variable    ${compatible_engine_image_name}

Wait to engine image ${custom_engine_image} to be deployed
    wait_for_engine_image_deployed    ${custom_engine_image}

Wait for engine image daemonset pods recreated
    ${output}=    Run Command And Get Output
    ...    kubectl -n longhorn-system get ds -l longhorn.io/component=engine-image --no-headers -o custom-columns=NAME:.metadata.name
    @{ds_names}=    Split To Lines    ${output}
    FOR    ${ds_name}    IN    @{ds_names}
        Wait for daemonset ${ds_name} pods recreated    namespace=longhorn-system
    END
