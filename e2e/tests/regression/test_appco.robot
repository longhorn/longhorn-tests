*** Settings ***
Documentation    Appco Test Cases

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
Resource    ../keywords/k8s.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LONGHORN_NAMESPACE}    longhorn-system
${DEP_VERSIONS_URL}    None

*** Keywords ***
Download JSON From URL
    [Arguments]    ${url}
    [Documentation]    Download JSON file using curl
    ${cmd}=    Set Variable    curl -fsSL ${url}
    ${result}=    Run Command    ${cmd}
    RETURN    ${result}

Parse JSON String
    [Arguments]    ${json_string}
    [Documentation]    Parse JSON string to dictionary
    ${json_dict}=    Evaluate    json.loads('''${json_string}''')    json
    RETURN    ${json_dict}

Resolve Dep Versions Branch
    [Arguments]    ${longhorn_version}
    [Documentation]    Map LONGHORN_VERSION to dep-versions branch name
    ...    Accepts: master, v1.11.x, 1.10.2
    ${version}=    Strip String    ${longhorn_version}
    ${lower_version}=    Convert To Lowercase    ${version}

    Return From Keyword If    '${lower_version}' == 'master'    master

    # Strip leading 'v' prefix if present, then split on '.' to get major and minor
    ${stripped}=    Remove String    ${lower_version}    v
    @{parts}=    Split String    ${stripped}    .
    ${major}=    Get From List    ${parts}    0
    ${minor}=    Get From List    ${parts}    1
    ${branch}=    Set Variable    v${major}.${minor}.x
    RETURN    ${branch}

Resolve Dep Versions Url
    [Arguments]    ${longhorn_version}
    [Documentation]    Build dep-versions URL from LONGHORN_VERSION
    ${branch}=    Resolve Dep Versions Branch    ${longhorn_version}
    ${url}=    Set Variable    https://raw.githubusercontent.com/longhorn/dep-versions/${branch}/versions.json
    Log    Using dep-versions branch: ${branch}
    RETURN    ${url}

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
    ${image}=    Run Command    ${cmd}

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
    ...    libqcow

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
    ${liveness_image}=    Run Command    ${cmd}
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

    ${v2_pods}=    Get Pod By Label Selector    longhorn.io/component=instance-manager,longhorn.io/data-engine=v2    ${LONGHORN_NAMESPACE}
    Should Not Be Empty    ${v2_pods}    msg=No running v2 instance-manager pod found
    ${v2_pod}=    Get From List    ${v2_pods}    0
    Log    Using v2 instance manager pod: ${v2_pod}

    Check Component Version In Pod    nvme-cli    ${v2_pod}    nvme version | head -n 1    ${versions}[nvme-cli]
    Check Component Version In Pod    tgt    ${v2_pod}    tgtd --version    ${versions}[tgt]
    Check Component Version In Pod    spdk    ${v2_pod}    spdk_tgt --version    ${versions}[spdk]    is_major=${TRUE}
    Check Component Version In Pod    libnvme    ${v2_pod}    nvme version | grep libnvme    ${versions}[libnvme]
    # libqcow is only available for appco 1.10+
    Check Component Version In Pod    libqcow    ${v2_pod}    sh -c 'find /usr -name "*libqcow*" -o -name "*qcow*" 2>/dev/null | grep -v proc | xargs ls -ld'    ${versions}[libqcow]

Check NFS Component Versions
    [Arguments]    ${versions}
    [Documentation]    Check all NFS/Share Manager component versions
    ${sm_pods}=    Get Pod By Label Selector    longhorn.io/component=share-manager    ${LONGHORN_NAMESPACE}
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

Get Longhorn CRD Chart Version
    [Documentation]    Get the chart version of the installed longhorn-crd release
    ...                and expose it as ${chart_version} for the test case.

    ${chart_version}=    Run Command
    ...    helm list -n ${LONGHORN_NAMESPACE} --filter '^longhorn-crd$' -o json | jq -r '.[0].chart // "" | sub("^longhorn-crd-"; "")'
    ${chart_version}=    Strip String    ${chart_version}

    IF    not $chart_version
        Skip    longhorn-crd release not found — skipping migration test
    END

    Set Test Variable    ${chart_version}
    Log    longhorn-crd chart version: ${chart_version}

Download Longhorn CRD Chart
    [Arguments]    ${chart_version}    ${workdir}
    [Documentation]    Download the longhorn-crd chart matching ${chart_version} from
    ...                rancher/charts into ${workdir}/${chart_version}.
    Run Command
    ...    bash -c "cd '${workdir}' && bash '${CURDIR}/../../pipelines/appco/scripts/download-longhorn-crd-chart.sh' '${chart_version}'"

Patch Longhorn CRDs Resource Policy
    [Arguments]    ${chart_dir}    ${attachments_url}
    [Documentation]    Annotate every CRD in ${chart_dir}/templates/crds.yaml with
    ...                helm.sh/resource-policy=keep so Helm will not delete them on uninstall.
    ...                Pass $$ (shell PID) as the backup-suffix to skip the interactive prompt.
    Run Command    curl -fsSL '${attachments_url}/patch-resource-policy-annotation.sh' -o '${chart_dir}/patch.sh'
    Run Command    bash '${chart_dir}/patch.sh' '${chart_dir}/templates/crds.yaml' $$
    Run Command    rm -f '${chart_dir}/patch.sh'

Remove Longhorn CRD Helm Release
    [Arguments]    ${chart_dir}
    [Documentation]    Upgrade longhorn-crd with the patched chart so Helm records the
    ...                resource-policy annotation, then uninstall the release.
    Run Command    helm upgrade longhorn-crd -n ${LONGHORN_NAMESPACE} '${chart_dir}'
    Run Command    helm uninstall longhorn-crd -n ${LONGHORN_NAMESPACE}

Verify Longhorn CRDs Retained
    [Documentation]    Assert that longhorn.io CRDs still exist after the release was removed.
    Run Command    kubectl get crd volumes.longhorn.io
    ${crd_count}=    Run Command    kubectl get crd -o name | grep -c 'longhorn\.io'
    ${crd_count}=    Strip String    ${crd_count}
    Should Be True    int($crd_count) > 0
    ...    msg=No longhorn.io CRDs found after helm uninstall — CRDs were not retained
    Log    Verified: ${crd_count} longhorn.io CRDs retained after longhorn-crd release removal

Helm Login AppCo
    [Documentation]    Log into the SUSE Application Collection OCI registry by sourcing
    ...                longhorn_helm_chart.sh and calling helm_login_appco.
    ...                xtrace is suppressed around the call so credentials are never logged.
    Run Command
    ...    bash -c "{ set +x; } 2>/dev/null; source '${CURDIR}/../../pipelines/appco/scripts/longhorn_helm_chart.sh'; { set +x; } 2>/dev/null; helm_login_appco"

Migrate Longhorn CRD Ownership
    [Arguments]    ${attachments_url}
    [Documentation]    Transfer CRD ownership from the removed longhorn-crd release to the
    ...                longhorn release. Downloads and runs the SUSE migrate-crd-ownership.sh
    ...                script which patches each CRD's labels and annotations via kubectl.
    ${script}=    Run Command    mktemp --suffix=.sh
    ${script}=    Strip String    ${script}
    TRY
        Run Command    curl -fsSL '${attachments_url}/migrate-crd-ownership.sh' -o '${script}'
        Run Command    bash '${script}'
    FINALLY
        Run Command    rm -f '${script}'
    END

Verify Longhorn CRD Ownership Transferred
    [Documentation]    Assert that longhorn.io CRDs are now owned by the longhorn Helm
    ...                release, not longhorn-crd.
    ${release_name}=    Run Command
    ...    kubectl get crd volumes.longhorn.io -o jsonpath='{.metadata.annotations.meta\\.helm\\.sh/release-name}'

    Should Be Equal    ${release_name}    longhorn
    ...    msg=CRD ownership not transferred: release-name is '${release_name}', expected 'longhorn'

Create AppCo Pull Secret
    [Documentation]    Create the application-collection docker-registry secret in
    ...                ${LONGHORN_NAMESPACE} so SUSE Storage can pull images from
    ...                dp.apps.rancher.io. Sources create_appco_secret.sh which suppresses
    ...                xtrace internally to avoid leaking credentials.
    Run Command
    ...    bash -c "source '${CURDIR}/../../pipelines/utilities/create_appco_secret.sh'; create_appco_secret"

Upgrade To SUSE Storage
    [Arguments]    ${longhorn_install_version}
    [Documentation]    Upgrade the longhorn Helm release to SUSE Storage.
    ...                Derives the target version from the +up suffix of ${longhorn_install_version}
    ...                (e.g. 109.3.2+up1.11.3 → 1.11.3).
    ${suse_storage_version}=    Fetch From Right    ${longhorn_install_version}    +up
    Log    Upgrading to SUSE Storage ${suse_storage_version}
    Run Command    helm upgrade longhorn oci://dp.apps.rancher.io/charts/suse-storage --namespace ${LONGHORN_NAMESPACE} --version ${suse_storage_version} --set global.imagePullSecrets="{application-collection}" --timeout 10m

Verify SUSE Storage Upgrade
    [Arguments]    ${longhorn_install_version}
    [Documentation]    Verify the longhorn Helm release was successfully upgraded to SUSE Storage.
    ...                Checks release status, chart name, and waits for manager rollout.
    ${suse_storage_version}=    Fetch From Right    ${longhorn_install_version}    +up

    # Helm release must be in deployed state
    ${status}=    Run Command
    ...    helm list -n ${LONGHORN_NAMESPACE} --filter '^longhorn$' -o json | jq -r '.[0].status'
    ${status}=    Strip String    ${status}
    Should Be Equal    ${status}    deployed
    ...    msg=longhorn Helm release status is '${status}', expected 'deployed'

    # Chart name must have flipped from longhorn-* to suse-storage-{version}
    ${chart}=    Run Command
    ...    helm list -n ${LONGHORN_NAMESPACE} --filter '^longhorn$' -o json | jq -r '.[0].chart'
    ${chart}=    Strip String    ${chart}
    Should Be Equal    ${chart}    suse-storage-${suse_storage_version}
    ...    msg=Helm chart is '${chart}', expected 'suse-storage-${suse_storage_version}'

    # Wait for all Longhorn manager pods to finish rolling out
    Run Command
    ...    kubectl -n ${LONGHORN_NAMESPACE} rollout status daemonset/longhorn-manager --timeout=300s
    Log    Verified: SUSE Storage ${suse_storage_version} upgrade successful

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

    ${LONGHORN_VERSION}=    Get Environment Variable    LONGHORN_VERSION    default=master
    ${resolved_dep_versions_url}=    Resolve Dep Versions Url    ${LONGHORN_VERSION}
    Set Test Variable    ${DEP_VERSIONS_URL}    ${resolved_dep_versions_url}

    Given Create storageclass longhorn-test with    dataEngine=v1
    And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test
    And Create deployment deploy-rwx with persistentvolumeclaim 0
    And Wait for volume of deployment deploy-rwx attached and healthy

    ${versions}=    Get Expected Component Version

    When Check All CSI Component Versions    ${versions}
    And Check All V2 Component Versions    ${versions}
    And Check NFS Component Versions    ${versions}

    Then Check Component Version Result

Test Rancher App Longhorn Migration to SUSE-Storage
    [Documentation]    Verify that Longhorn installed via Rancher Apps Marketplace can be migrated
    ...    to SUSE-Storage
    ...
    ...    Note: This test can only run on the longhorn-rancher-chart-test pipeline.
    ...
    ...    Pre-conditions (set by pipeline):
    ...    - Longhorn is installed via Rancher Apps Marketplace
    ...    - LONGHORN_INSTALL_VERSION is the Rancher chart version (e.g. 109.3.1+up1.11.2)
    ...
    ...    Phase 1 - Detach CRD Helm release while retaining CRDs:
    ...    - Get installed longhorn-crd chart version
    ...    - Download matching chart from rancher/charts
    ...    - Patch CRDs with helm.sh/resource-policy=keep
    ...    - Remove longhorn-crd Helm release (CRDs are retained)
    ...    - Verify CRDs survived the uninstall
    ...
    ...    Phase 2 - Transfer CRD ownership from longhorn-crd to longhorn:
    ...    - Migrate Longhorn CRD ownership
    ...    - Verify CRD ownership transferred
    ...
    ...    Phase 3 - Install SUSE-Storage and verify:
    ...    - Login to AppCo Helm registry
    ...    - Create AppCo pull secret
    ...    - Upgrade to SUSE-Storage chart
    ...    - Verify SUSE-Storage version and rollout
    ...
    ...    Ref:
    ...    https://documentation.suse.com/cloudnative/storage/1.11/en/migration/migration.html#_migrating_longhorn_deployed_via_rancher_apps_marketplace_to_suse_storage
    ${LONGHORN_INSTALL_VERSION}=    Get Environment Variable    LONGHORN_INSTALL_VERSION
    ${workdir}=    Run Command    mktemp -d
    ${workdir}=    Strip String    ${workdir}
    ${attachments}=    Set Variable    https://documentation.suse.com/cloudnative/storage/1.11/en/_attachments

    # Phase 1: Remove longhorn-crd Helm release while keeping CRDs
    When Get Longhorn CRD Chart Version
    And Download Longhorn CRD Chart             chart_version=${chart_version}    workdir=${workdir}
    And Patch Longhorn CRDs Resource Policy     chart_dir=${workdir}/${chart_version}        attachments_url=${attachments}
    And Remove Longhorn CRD Helm Release        chart_dir=${workdir}/${chart_version}
    And Verify Longhorn CRDs Retained
    And Run Command    rm -rf '${workdir}'

    # Phase 2: Replace longhorn-crd with longhorn in Longhorn CRDs
    And Migrate Longhorn CRD Ownership    attachments_url=${attachments}
    And Verify Longhorn CRD Ownership Transferred

    # Phase 3: Install SUSE-Storage Longhorn Helm chart and verify component versions
    When Helm Login AppCo
    And Create AppCo Pull Secret
    And Upgrade To SUSE Storage    ${LONGHORN_INSTALL_VERSION}
    And Verify SUSE Storage Upgrade    ${LONGHORN_INSTALL_VERSION}
