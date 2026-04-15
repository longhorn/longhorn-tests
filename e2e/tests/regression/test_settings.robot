*** Settings ***
Documentation    Settings Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/backupstore.resource
Resource    ../keywords/sharemanager.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/snapshot.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Verify TooManySnapshots Condition After Creating Snapshots
    [Documentation]    Create a volume, create snapshots up to the expected warning threshold,
    ...                verify TooManySnapshots condition becomes True with the expected threshold
    ...                in the message, then delete all snapshots and purge, and verify the
    ...                condition becomes False with an empty message.
    [Arguments]    ${snapshot_max_count}    ${warning_threshold}    ${volume_snapshot_max_count}    ${expected_warning_snapshot_count}
    IF    '${DATA_ENGINE}' == 'v2'
        Skip    v2 data engine doesn't support snapshot-max-count: https://github.com/longhorn/longhorn/issues/12921
    END
    Given Setting snapshot-max-count is set to ${snapshot_max_count}
    And Setting snapshot-count-warning-threshold is set to ${warning_threshold}

    ${volume_suffix} =    Generate new uuid
    ${volume_name} =    Set Variable    vol-${volume_suffix}
    When Create volume ${volume_name}    snapshotMaxCount=${volume_snapshot_max_count}
    And Attach volume ${volume_name}
    And Wait for volume ${volume_name} healthy

    And Create ${expected_warning_snapshot_count} snapshot for volume ${volume_name}
    Then Run command and wait for output
    ...    kubectl get volume -n ${LONGHORN_NAMESPACE} ${volume_name} -o jsonpath='{.status.conditions[?(@.type=="TooManySnapshots")].status}'
    ...    True
    And Run command and wait for output
    ...    kubectl get volume -n ${LONGHORN_NAMESPACE} ${volume_name} -o jsonpath='{.status.conditions[?(@.type=="TooManySnapshots")].message}'
    ...    at or over the warning threshold ${expected_warning_snapshot_count}

    # Remove all snapshots
    FOR    ${i}    IN RANGE    ${expected_warning_snapshot_count}
        Delete snapshot ${i} of volume ${volume_name}
    END
    And Purge volume ${volume_name} snapshot

    Then Run command and wait for output
    ...    kubectl get volume -n ${LONGHORN_NAMESPACE} ${volume_name} -o jsonpath='{.status.conditions[?(@.type=="TooManySnapshots")].status}'
    ...    False
    And Run command and not expect output
    ...    kubectl get volume -n ${LONGHORN_NAMESPACE} ${volume_name} -o jsonpath='{.status.conditions[?(@.type=="TooManySnapshots")].message}'
    ...    at or over the warning threshold

*** Test Cases ***
Test Setting Update With Valid Value
    [Tags]    setting
    [Documentation]    Test that valid setting updates are applied correctly.
    [Template]    Update Setting To Valid Value And Verify
    default-replica-count    1    {"v1":"1","v2":"1"}
    default-replica-count    {"v1":"5","v2":"10"}    {"v1":"5","v2":"10"}
    disable-revision-counter    {"v1":"false"}    {"v1":"false"}

Test Setting Update With Invalid Value
    [Tags]    setting
    [Documentation]    Test that invalid setting updates are rejected and values remain unchanged.
    [Template]    Update Setting To Invalid Value And Verify
    disable-revision-counter    {"v1":"true","v2":"true"}
    disable-revision-counter    {"v2":"true"}
    disable-revision-counter    {"v3":"true"}
    default-replica-count    {}

Test Setting Concurrent Rebuild Limit
    [Tags]    setting
    [Documentation]    Test if setting Concurrent Replica Rebuild Per Node Limit works correctly.
    Given Setting concurrent-replica-rebuild-per-node-limit is set to 1

    When Create volume 0 with    size=5Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Create volume 1 with    size=5Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 1
    And Wait for volume 1 healthy

    # Write a large amount of data into both volumes, so the rebuilding will take a while.
    And Write 4 GB data to volume 0
    And Write 4 GB data to volume 1

    # Delete replica of volume 1 and replica on the same node of volume 2 to trigger (concurrent) rebuilding.
    And Delete volume 0 replica on replica node
    And Delete volume 1 replica on replica node
    Then Only one replica rebuilding on replica node will start at a time, either for volume 0 or volume 1
    And Wait until volume 0 replica rebuilding completed on replica node
    And Wait until volume 1 replica rebuilding completed on replica node

    Given Setting concurrent-replica-rebuild-per-node-limit is set to 2
    When Delete volume 0 replica on replica node
    And Delete volume 1 replica on replica node
    Then Both volume 0 and volume 1 replica rebuilding on replica node will start at the same time
    And Wait until volume 0 replica rebuilding completed on replica node
    And Wait until volume 1 replica rebuilding completed on replica node

    Given Setting concurrent-replica-rebuild-per-node-limit is set to 1
    When Delete volume 0 replica on replica node
    And Wait until volume 0 replica rebuilding started on replica node
    And Delete volume 1 replica on replica node
    And Delete volume 0 replica on replica node
    And Wait until volume 0 replica rebuilding stopped on replica node
    Then Only one replica rebuilding on replica node will start at a time, either for volume 0 or volume 1
    And Wait until volume 0 replica rebuilding completed on replica node
    And Wait until volume 1 replica rebuilding completed on replica node

    # Test the setting won't intervene normal attachment.
    Given Setting concurrent-replica-rebuild-per-node-limit is set to 1
    When Detach volume 1
    And Wait for volume 1 detached
    And Delete volume 0 replica on replica node
    And Wait until volume 0 replica rebuilding started on replica node
    And Attach volume 1
    And Wait for volume 1 healthy
    And Wait until volume 0 replica rebuilding completed on replica node
    And Wait for volume 0 healthy
    Then Check volume 0 data is intact
    And Check volume 1 data is intact

Test Setting Network For RWX Volume Endpoint
    [Tags]    setting    volume    rwx    storage-network    sharemanager
    [Documentation]    Test if setting endpoint-network-for-rwx-volume works correctly.
    ...
    ...                Issues:
    ...                    - https://github.com/longhorn/longhorn/issues/10269
    ...                    - https://github.com/longhorn/longhorn/issues/8184
    ...
    ...                Precondition: NAD network configured.

    Given Setting endpoint-network-for-rwx-volume is set to ${EMPTY}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=3
    When Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0 with max replicaset
    Then Check Longhorn workload pods not running with CNI interface lhnet2
        ...    longhorn-csi-plugin
        ...    longhorn-share-manager
    And Check sharemanager not using headless service

    And Delete deployment 0
    And Delete persistentvolumeclaim 0
    And Wait for all sharemanager to be deleted

    When Setting endpoint-network-for-rwx-volume is set to kube-system/demo-172-16-0-0
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 1 with persistentvolumeclaim 1 with max replicaset
    Then Check Longhorn workload pods is running with CNI interface lhnet2
        ...    longhorn-csi-plugin
        ...    longhorn-share-manager
    And Check sharemanager is using headless service

Test Setting Csi Components Resource Limits
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12224
    When Setting system-managed-csi-components-resource-limits is set to {"csi-attacher":{"requests":{"cpu":"100m","memory":"128Mi"},"limits":{"cpu":"200m","memory":"256Mi"}},"node-driver-registrar":{"requests":{"cpu":"100m","memory":"128Mi"},"limits":{"cpu":"200m","memory":"256Mi"}},"longhorn-csi-plugin":{"requests":{"cpu":"150m","memory":"128Mi"},"limits":{"cpu":"250m","memory":"256Mi"}}}
    And Wait for Longhorn components all running
    Then Run command and wait for output
    ...    kubectl get pod -l app=csi-attacher -o jsonpath='{.items[0].spec.containers[*].resources.requests}' -n longhorn-system
    ...    {"cpu":"100m","memory":"128Mi"}
    And Run command and wait for output
    ...    kubectl get pod -l app=csi-attacher -o jsonpath='{.items[0].spec.containers[*].resources.limits}' -n longhorn-system
    ...    {"cpu":"200m","memory":"256Mi"}
    And Run command and wait for output
    ...    kubectl get pod -l app=longhorn-csi-plugin -o jsonpath='{.items[0].spec.containers[0].resources.requests}' -n longhorn-system
    ...    {"cpu":"100m","memory":"128Mi"}
    And Run command and wait for output
    ...    kubectl get pod -l app=longhorn-csi-plugin -o jsonpath='{.items[0].spec.containers[0].resources.limits}' -n longhorn-system
    ...    {"cpu":"200m","memory":"256Mi"}
    And Run command and wait for output
    ...    kubectl get pod -l app=longhorn-csi-plugin -o jsonpath='{.items[0].spec.containers[2].resources.requests}' -n longhorn-system
    ...    {"cpu":"150m","memory":"128Mi"}
    And Run command and wait for output
    ...    kubectl get pod -l app=longhorn-csi-plugin -o jsonpath='{.items[0].spec.containers[2].resources.limits}' -n longhorn-system
    ...    {"cpu":"250m","memory":"256Mi"}

Test Setting Blacklist For Auto Delete Pod
    [Tags]    setting
    [Documentation]    Test if setting blacklist-for-auto-delete-pod-when-volume-detached-unexpectedly works correctly.
    ...                Issues:
    ...                    - https://github.com/longhorn/longhorn/issues/12120
    ...                    - https://github.com/longhorn/longhorn/issues/12121
    IF    '${DATA_ENGINE}' == 'v2'
        Skip    Test case not support for v2 data engine
    END

    Given Setting blacklist-for-auto-delete-pod-when-volume-detached-unexpectedly is set to apps/ReplicaSet;apps/DaemonSet
    When Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0 and liveness probe

    When Kill volume engine process for deployment 0
    And Wait for deployment 0 pod stuck in CrashLoopBackOff

    When Setting blacklist-for-auto-delete-pod-when-volume-detached-unexpectedly is set to apps/DaemonSet
    And Wait for deployment 0 pods stable

Test Default Settings Quoting
    [Tags]    setting    uninstall
    [Documentation]    Verify that Longhorn correctly handles quoted and unquoted values in default
    ...                settings during installation, for both helm and manifest install methods.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/11854
    ...
    ...                Test steps:
    ...                1. Uninstall Longhorn.
    ...                2. If install method is helm, patch values.yaml with:
    ...                       defaultSettings.defaultReplicaCount: '{"v1":"4","v2":"2"}' (with quotes)
    ...                       defaultSettings.deletingConfirmationFlag: true (no quotes)
    ...                   If install method is manifest, append to default-setting.yaml section of
    ...                   longhorn.yaml:
    ...                       default-replica-count: '{"v1":"4","v2":"2"}'
    ...                       deleting-confirmation-flag: true
    ...                   then install Longhorn.
    ...                3. Wait for Longhorn to be running.
    ...                4. Check that default-replica-count is {"v1":"4","v2":"2"} and
    ...                   deleting-confirmation-flag is true.

    Given Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check all Longhorn CRD removed

    ${LONGHORN_INSTALL_METHOD} =    Get Environment Variable    LONGHORN_INSTALL_METHOD    default=manifest
    IF    '${LONGHORN_INSTALL_METHOD}' == 'helm'
        # Patch values.yaml: defaultReplicaCount with a quoted JSON string, deletingConfirmationFlag without quotes.
        # The custom_cmd outputs a values.yaml file used by helm install via -f values.yaml.
        ${patch} =    Set Variable
        ...    .defaultSettings.defaultReplicaCount = "{\\"v1\\":\\"4\\",\\"v2\\":\\"2\\"}" | .defaultSettings.deletingConfirmationFlag = true
        ${helm_cmd} =    Set Variable    yq eval \'${patch}\' ${LONGHORN_REPO_DIR}/chart/values.yaml > values.yaml
        Install Longhorn    custom_cmd=${helm_cmd}
    ELSE
        # Append two settings lines after the "default-setting.yaml" key in the longhorn.yaml ConfigMap,
        # using sed append. Second sed inserts default-replica-count first so it appears before
        # deleting-confirmation-flag in the block (sed /pattern/a inserts immediately after the match).
        ${manifest_cmd} =    Set Variable
        ...    sed -i "/default-setting\\.yaml: |-/a\\${SPACE * 4}deleting-confirmation-flag: true" longhorn.yaml && sed -i "/default-setting\\.yaml: |-/a\\${SPACE * 4}default-replica-count: '{\\"v1\\":\\"4\\",\\"v2\\":\\"2\\"}'" longhorn.yaml
        Install Longhorn    custom_cmd=${manifest_cmd}
    END

    Then Wait for longhorn ready
    And Setting default-replica-count should be {"v1":"4","v2":"2"}
    And Setting deleting-confirmation-flag should be true

Test TooManySnapshots Volume Condition
    [Tags]    snapshot
    [Documentation]    Test TooManySnapshots volume condition when snapshot count reaches warning threshold.
    ...    Issue: https://github.com/longhorn/longhorn/issues/12396
    ...    1. Set snapshot-max-count to 10
    ...    2. Set snapshot-count-warning-threshold to 5
    ...    3. Create a volume without setting snapshotMaxCount
    ...    4. Create 5 snapshots for the volume
    ...    5. Check TooManySnapshots volume condition is True
    ...    6. Check TooManySnapshots volume condition message contains
    ...       "at or over the warning threshold 5"
    ...    7. Remove all snapshots
    ...    8. Check TooManySnapshots volume condition is False
    ...    9. Check TooManySnapshots volume condition message is empty
    ...
    ...    Repeat the above steps with different combinations
    [Template]    Verify TooManySnapshots Condition After Creating Snapshots
    # snapshot-max-count    warning-threshold    volume snapshotMaxCount    expected warning snapshot count
    # warning at min(10, 5, -) (5)
    snapshot_max_count=10    warning_threshold=5    volume_snapshot_max_count=0    expected_warning_snapshot_count=5
    # warning at min(10, 5, 15) (5)
    snapshot_max_count=10    warning_threshold=5    volume_snapshot_max_count=15    expected_warning_snapshot_count=5
    # warning at min(10, 5, 5) (5)
    snapshot_max_count=10    warning_threshold=5    volume_snapshot_max_count=5    expected_warning_snapshot_count=5
    # warning at min(10, 5, 3) (3)
    snapshot_max_count=10    warning_threshold=5    volume_snapshot_max_count=3    expected_warning_snapshot_count=3
    # warning at min(3, 5, -) (3)
    snapshot_max_count=3    warning_threshold=5    volume_snapshot_max_count=0    expected_warning_snapshot_count=3
    # warning at min(10, 15, -) (10)
    snapshot_max_count=10    warning_threshold=15    volume_snapshot_max_count=0    expected_warning_snapshot_count=10
