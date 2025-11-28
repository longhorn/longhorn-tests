*** Settings ***
Documentation    Appco Component Version Verification

Test Tags    appco

Library    String
Library    Collections
Library    OperatingSystem

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/storageclass.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LONGHORN_NAMESPACE}    longhorn-system
${DEP_VERSIONS_URL}    https://raw.githubusercontent.com/longhorn/dep-versions/v1.9.x/versions.json

*** Keywords ***
List Pods In Namespace With Label
    [Arguments]    ${namespace}    ${label_selector}
    [Documentation]    List pods in namespace with label selector
    ${cmd}=    Set Variable    kubectl -n ${namespace} get pods -l ${label_selector} -o jsonpath='{.items[*].metadata.name}'
    ${pods_str}=    Execute Command And Get Output    ${cmd}
    @{pods}=    Split String    ${pods_str}
    RETURN    @{pods}

Execute Command And Get Output
    [Arguments]    ${command}
    [Documentation]    Execute shell command and return output
    ${result}=    Run    ${command}
    RETURN    ${result}

Download JSON From URL
    [Arguments]    ${url}
    [Documentation]    Download JSON file using curl
    ${result}=    Execute Command And Get Output    curl -fsSL ${url}
    RETURN    ${result}

Parse JSON String
    [Arguments]    ${json_string}
    [Documentation]    Parse JSON string to dictionary
    ${json_dict}=    Evaluate    json.loads('''${json_string}''')    json
    RETURN    ${json_dict}

Get Expected Version From JSON
    [Arguments]    ${json_data}    ${component_key}    ${tag_key}=tag
    [Documentation]    Extract expected version from JSON
    ${component}=    Get From Dictionary    ${json_data}    ${component_key}
    ${version}=    Get From Dictionary    ${component}    ${tag_key}
    RETURN    ${version}

Extract Version Base
    [Arguments]    ${version_string}
    [Documentation]    Extract base version (remove 'v' prefix, '-date' and '+build' suffixes)
    ${cleaned}=    Remove String    ${version_string}    v
    # Remove '-date' suffix first (e.g., v4.10.0-20251030 -> 4.10.0)
    ${base}=    Fetch From Left    ${cleaned}    -
    # Remove '+build' suffix (e.g., 1.0.79+2 -> 1.0.79)
    ${base}=    Fetch From Left    ${base}    +
    RETURN    ${base}

Extract Major Version
    [Arguments]    ${version_string}    ${segments}=2
    [Documentation]    Extract major version (e.g., v25.05.0+4 -> 25.05)
    ${cleaned}=    Remove String    ${version_string}    v
    ${base}=    Fetch From Left    ${cleaned}    +
    @{parts}=    Split String    ${base}    .
    ${major_parts}=    Get Slice From List    ${parts}    0    ${segments}
    ${major}=    Evaluate    ".".join(${major_parts})
    RETURN    ${major}

Get Pod Image Tag
    [Arguments]    ${resource_type}    ${resource_name}    ${container_name}=${EMPTY}
    [Documentation]    Get image tag from deployment or daemonset
    ${jsonpath}=    Set Variable If
    ...    '${container_name}' == '${EMPTY}'
    ...    {.spec.template.spec.containers[0].image}
    ...    {.spec.template.spec.containers[?(@.name=="${container_name}")].image}

    ${cmd}=    Set Variable    kubectl -n ${LONGHORN_NAMESPACE} get ${resource_type} ${resource_name} -o jsonpath='${jsonpath}'
    ${image}=    Execute Command And Get Output    ${cmd}

    ${tag}=    Fetch From Right    ${image}    :
    RETURN    ${tag}

Check CSI Component Version
    [Arguments]    ${component_name}    ${deployment_name}    ${expected_version}
    [Documentation]    Check CSI component version matches expected
    Log    Checking ${component_name}...

    ${image_tag}=    Get Pod Image Tag    deploy    ${deployment_name}
    ${actual_base}=    Extract Version Base    ${image_tag}
    ${expected_base}=    Extract Version Base    ${expected_version}

    ${passed}=    Run Keyword And Return Status    Should Be Equal    ${actual_base}    ${expected_base}
    Record Check Result    ${passed}    ${component_name}: ${actual_base}    ${component_name}: Expected ${expected_base}, Actual ${actual_base} (full: ${image_tag})

Check Component Version In Pod
    [Arguments]    ${component_name}    ${pod_name}    ${command}    ${expected_version}    ${is_major}=${FALSE}
    [Documentation]    Check V2 component version by executing command in pod
    Log    Checking ${component_name} in pod ${pod_name}...

    ${output}=    pod_exec    ${pod_name}    ${LONGHORN_NAMESPACE}    ${command}

    Run Keyword If    ${is_major}
    ...      Check Version Major Match    ${component_name}    ${output}    ${expected_version}
    ...    ELSE
    ...      Check Version Contains    ${component_name}    ${output}    ${expected_version}

Check Version Contains
    [Arguments]    ${component_name}    ${output}    ${expected_version}
    ${expected_base}=    Extract Version Base    ${expected_version}
    ${passed}=    Run Keyword And Return Status    Should Contain    ${output}    ${expected_base}
    Record Check Result    ${passed}    ${component_name}: ${output}    ${component_name}: Expected ${expected_base} in output: ${output}

Check Version Major Match
    [Arguments]    ${component_name}    ${output}    ${expected_version}
    ${expected_major}=    Extract Major Version    ${expected_version}
    ${passed}=    Run Keyword And Return Status    Should Contain Any    ${output}    ${expected_major}    v${expected_major}    V${expected_major}
    Record Check Result    ${passed}    ${component_name}: ${output}    ${component_name}: Expected major ${expected_major} in output: ${output}

Get Expected Component Version
    [Documentation]    Download and parse version specification from GitHub
    Log    Source: ${DEP_VERSIONS_URL}
    ${json_string}=    Download JSON From URL    ${DEP_VERSIONS_URL}
    ${versions_json}=    Parse JSON String    ${json_string}

    ${versions}=    Create Dictionary
    ${components}=    Create List
    ...    csi-attacher
    ...    csi-provisioner
    ...    csi-resizer
    ...    csi-snapshotter
    ...    csi-node-driver-registrar
    ...    livenessprobe
    ...    nvme-cli
    ...    tgt
    ...    spdk
    ...    libnvme
    ...    nfs-ganesha
    # libqcow is only available for appco 1.10+
#    ...    libqcow

    FOR    ${component}    IN    @{components}
        ${ver}=    Get Expected Version From JSON    ${versions_json}    ${component}
        Set To Dictionary    ${versions}    ${component}    ${ver}
    END

    RETURN    ${versions}

Check All CSI Component Versions
    [Arguments]    ${versions}
    [Documentation]    Check all CSI related component versions

    # Standard CSI components
    Check CSI Component Version    csi-attacher    csi-attacher    ${versions}[csi-attacher]
    Check CSI Component Version    csi-provisioner    csi-provisioner    ${versions}[csi-provisioner]
    Check CSI Component Version    csi-resizer    csi-resizer    ${versions}[csi-resizer]
    Check CSI Component Version    csi-snapshotter    csi-snapshotter    ${versions}[csi-snapshotter]

    # Node driver registrar
    ${image_tag}=    Get Pod Image Tag    ds    longhorn-csi-plugin    node-driver-registrar
    ${actual_base}=    Extract Version Base    ${image_tag}
    ${expected_base}=    Extract Version Base    ${versions}[csi-node-driver-registrar]

    ${passed}=    Run Keyword And Return Status    Should Be Equal    ${actual_base}    ${expected_base}
    Record Check Result    ${passed}    csi-node-driver-registrar: ${actual_base}    csi-node-driver-registrar: Expected ${expected_base}, Actual ${actual_base}

    # Liveness probe
    ${cmd}=    Set Variable    kubectl -n ${LONGHORN_NAMESPACE} get ds longhorn-csi-plugin -o jsonpath='{.spec.template.spec.containers[*].image}'
    ${liveness_image}=    Execute Command And Get Output    ${cmd}
    ${images}=    Split String    ${liveness_image}
    ${liveness_full}=    Evaluate    [img for img in ${images} if 'livenessprobe' in img][0]
    ${liveness_tag}=    Fetch From Right    ${liveness_full}    :
    ${actual_base}=    Extract Version Base    ${liveness_tag}
    ${expected_base}=    Extract Version Base    ${versions}[livenessprobe]

    ${passed}=    Run Keyword And Return Status    Should Be Equal    ${actual_base}    ${expected_base}
    Record Check Result    ${passed}    livenessprobe: ${actual_base}    livenessprobe: Expected ${expected_base}, Actual ${actual_base}

Check All V2 Component Versions
    [Arguments]    ${versions}
    [Documentation]    Check all V2 data engine component versions

    ${v2_pods}=    List Pods In Namespace With Label    ${LONGHORN_NAMESPACE}    longhorn.io/component=instance-manager,longhorn.io/data-engine=v2
    Should Not Be Empty    ${v2_pods}    msg=No running v2 instance-manager pod found
    ${v2_pod}=    Get From List    ${v2_pods}    0
    Log    Using v2 instance manager pod: ${v2_pod}

    Check Component Version In Pod    nvme-cli    ${v2_pod}    nvme version | head -n 1    ${versions}[nvme-cli]
    Check Component Version In Pod    tgt    ${v2_pod}    tgtd --version    ${versions}[tgt]
    Check Component Version In Pod    spdk    ${v2_pod}    spdk_tgt --version    ${versions}[spdk]    is_major=${TRUE}
    Check Component Version In Pod    libnvme    ${v2_pod}    nvme version | grep libnvme    ${versions}[libnvme]
    # libqcow is only available for appco 1.10+
#    Check Component Version In Pod    libqcow    ${v2_pod}    sh -c 'find /usr -name "*libqcow*" -o -name "*qcow*" 2>/dev/null | grep -v proc | xargs ls -ld'    ${versions}[libqcow]

Check NFS Component Versions
    [Arguments]    ${versions}
    [Documentation]    Check all NFS/Share Manager component versions
    ${sm_pods}=    List Pods In Namespace With Label    ${LONGHORN_NAMESPACE}    longhorn.io/component=share-manager
    Should Not Be Empty    ${sm_pods}    msg=No share-manager pod found (NFS feature may not be enabled)
    ${sm_pod}=    Get From List    ${sm_pods}    0
    Log    Using share manager pod: ${sm_pod}

    Check Component Version In Pod    nfs-ganesha    ${sm_pod}    ganesha.nfsd -v    ${versions}[nfs-ganesha]    is_major=${TRUE}

Record Check Result
    [Arguments]    ${passed}    ${pass_msg}    ${fail_msg}
    Run Keyword If    ${passed}
    ...      Append To List    ${VERSION_REPORT}    PASS: ${pass_msg}
    ...    ELSE
    ...      Run Keywords  Append To List    ${VERSION_REPORT}    FAIL: ${fail_msg}
    ...      AND           Append To List    ${FAILED_CHECKS}    ${fail_msg}

Check Component Version Result
    [Documentation]    Fail the test if any checks failed
    ${failed_count}=    Get Length    ${FAILED_CHECKS}
    ${report_string}=    Evaluate    "\\n".join(${VERSION_REPORT})
    ${fail_msg}=    Evaluate    "\\n".join(${FAILED_CHECKS})

    Run Keyword If    ${failed_count} != 0
    ...      Fail    ${fail_msg}
    ...    ELSE
    ...      Log    ${report_string}

*** Test Cases ***
Verify Appco Component Versions
    [Documentation]    Verify all Appco component versions match dep-versions specification
    ...
    ...    - This test:
    ...    - 1. Enables v2 data engine and creates RWX volume (to trigger all components)
    ...    - 2. Downloads version spec from GitHub
    ...    - 3. Checks CSI component versions
    ...    - 4. Checks V2 instance-manager component versions
    ...    - 5. Checks NFS/share-manager component versions

    Set Test Variable    @{FAILED_CHECKS}    @{EMPTY}
    Set Test Variable    @{VERSION_REPORT}    @{EMPTY}

    Given Create storageclass longhorn-test with    dataEngine=v1
    And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test
    And Create deployment deploy-rwx with persistentvolumeclaim 0
    And Wait for volume of deployment deploy-rwx attached and healthy

    ${versions}=    Get Expected Component Version

    When Check All CSI Component Versions    ${versions}
    And Check All V2 Component Versions    ${versions}
    And Check NFS Component Versions    ${versions}

    Then Check Component Version Result

