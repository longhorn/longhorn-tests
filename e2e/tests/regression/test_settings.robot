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

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
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
    [Tags]    setting    volume    rwx    storage-network
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

Test RWX Volume Endpoint Network With Storage Network Enabled
    [Tags]    storage-network
    [Documentation]    Issues: https://github.com/longhorn/longhorn/issues/10269
    ...                        https://github.com/longhorn/longhorn/blob/40086933b11383cdcc492b3b1be836dec0c23d81/enhancements/20251017-rwx-volume-endpoint-network.md
    ...    Feature validation: Verify that RWX volume mounts function correctly with the endpoint network setting.
    ...
    ...    Example scenarios:
    ...    storage-network | endpoint-network-for-rwx-volume
    ...         NAD1       |            NAD1
    ...         NAD1       |            NAD2
    ...         NAD1       |             -
    Given Setting storage-network should be kube-system/demo-192-168-0-0
    And Setting endpoint-network-for-rwx-volume is set to kube-system/demo-192-168-0-0
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=3

    When Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    Then Check Longhorn workload pods is running with CNI interface lhnet2
        ...    longhorn-csi-plugin
        ...    longhorn-share-manager
    And Write 100 MB data to file data.txt in deployment 0
    And Check deployment 0 data in file data.txt is intact

    And Delete deployment 0
    And Delete persistentvolumeclaim 0
    And Wait for all sharemanager to be deleted

    Given Setting endpoint-network-for-rwx-volume is set to kube-system/demo-172-16-0-0
    When Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 1 healthy
    Then Check Longhorn workload pods is running with CNI interface lhnet2
        ...    longhorn-csi-plugin
        ...    longhorn-share-manager
    And Write 100 MB data to file data.txt in deployment 1
    And Check deployment 1 data in file data.txt is intact

    And Delete deployment 1
    And Delete persistentvolumeclaim 1
    And Wait for all sharemanager to be deleted

    Given Setting endpoint-network-for-rwx-volume is set to ${EMPTY}
    When Create persistentvolumeclaim 2    volume_type=RWX        sc_name=longhorn-test
    And Create deployment 2 with persistentvolumeclaim 2
    And Wait for volume of deployment 2 healthy
    Then Check Longhorn workload pods not running with CNI interface lhnet2
        ...    longhorn-csi-plugin
        ...    longhorn-share-manager
    And Write 100 MB data to file data.txt in deployment 2
    And Check deployment 2 data in file data.txt is intact

    And Delete deployment 2
    And Delete persistentvolumeclaim 2
    And Wait for all sharemanager to be deleted

Test RWX Volume Endpoint Network With Storage Network Disabled
    [Tags]    storage-network
    [Documentation]    Issues: https://github.com/longhorn/longhorn/issues/10269
    ...                        https://github.com/longhorn/longhorn/blob/40086933b11383cdcc492b3b1be836dec0c23d81/enhancements/20251017-rwx-volume-endpoint-network.md
    ...    Feature validation: Verify that RWX volume mounts function correctly with the endpoint network setting.
    ...
    ...    Example scenarios:
    ...    storage-network | endpoint-network-for-rwx-volume
    ...         -          |            NAD1
    ...         -          |            NAD2
    ...         -          |             -
    Given Setting storage-network is set to ${EMPTY}
    And Setting endpoint-network-for-rwx-volume is set to kube-system/demo-192-168-0-0
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=3

    When Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    Then Check Longhorn workload pods is running with CNI interface lhnet2
        ...    longhorn-csi-plugin
        ...    longhorn-share-manager
    And Write 100 MB data to file data.txt in deployment 0
    And Check deployment 0 data in file data.txt is intact

    And Delete deployment 0
    And Delete persistentvolumeclaim 0
    And Wait for all sharemanager to be deleted

    Given Setting endpoint-network-for-rwx-volume is set to kube-system/demo-172-16-0-0
    When Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 1 healthy
    Then Check Longhorn workload pods is running with CNI interface lhnet2
        ...    longhorn-csi-plugin
        ...    longhorn-share-manager
    And Write 100 MB data to file data.txt in deployment 1
    And Check deployment 1 data in file data.txt is intact

    And Delete deployment 1
    And Delete persistentvolumeclaim 1
    And Wait for all sharemanager to be deleted

    Given Setting endpoint-network-for-rwx-volume is set to ${EMPTY}
    When Create persistentvolumeclaim 2    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 2 with persistentvolumeclaim 2
    And Wait for volume of deployment 2 healthy
    Then Check Longhorn workload pods not running with CNI interface lhnet2
        ...    longhorn-csi-plugin
        ...    longhorn-share-manager
    And Write 100 MB data to file data.txt in deployment 2
    And Check deployment 2 data in file data.txt is intact

    And Delete deployment 2
    And Delete persistentvolumeclaim 2
    And Wait for all sharemanager to be deleted

Test RWX Volume Endpoint Network Upgrade When Storage Network For RWX Volume Enabled
    [Tags]    upgrade    storage-network
    [Documentation]    Issues: https://github.com/longhorn/longhorn/issues/10269
    ...                        https://github.com/longhorn/longhorn/blob/40086933b11383cdcc492b3b1be836dec0c23d81/enhancements/20251017-rwx-volume-endpoint-network.md
    ...    Upgrade from v1.10.x
    ...    Confirm that the storage-network-for-rwx-volume-enabled setting is replaced by
    ...    endpoint-network-for-rwx-volume.
    ...
    ...    If the storage network was previously enabled (true),
    ...    the new endpoint-network-for-rwx-volume setting inherits the storage-network value.
    ...
    ...    Upgrade strategy
    ...    During upgrade, the manager detects the legacy storage-network-for-rwx-volume-enabled setting and performs a one-time migration:
    ...    If storage-network-for-rwx-volume-enabled=true, endpoint-network-for-rwx-volume is set to the storage-network value.
    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Fail    Environment variable LONGHORN_STABLE_VERSION is not set
    ELSE IF    not '${LONGHORN_STABLE_VERSION}'.startswith('v1.10.')
        Skip    This test case is only required when upgrade from v1.10.x
    END

    Given Setting deleting-confirmation-flag is set to true
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=3
    And Uninstall Longhorn
    And Check Longhorn CRD removed
    And Install Longhorn stable version
    And Set default backupstore
    And Enable Storage Network
    And Setting storage-network should be kube-system/demo-192-168-0-0
    And Setting storage-network-for-rwx-volume-enabled is set to true

    When Upgrade Longhorn to custom version
    Then Setting storage-network should be kube-system/demo-192-168-0-0
    And Setting endpoint-network-for-rwx-volume should be kube-system/demo-192-168-0-0

    When Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    Then Check Longhorn workload pods is running with CNI interface lhnet2
        ...    longhorn-csi-plugin
        ...    longhorn-share-manager
    And Write 100 MB data to file data.txt in deployment 0
    And Check deployment 0 data in file data.txt is intact

Test RWX Volume Endpoint Network Upgrade When Storage Network For RWX Volume Disabled
    [Tags]    upgrade    storage-network
    [Documentation]    Issues: https://github.com/longhorn/longhorn/issues/10269
    ...                        https://github.com/longhorn/longhorn/blob/40086933b11383cdcc492b3b1be836dec0c23d81/enhancements/20251017-rwx-volume-endpoint-network.md
    ...    Upgrade from v1.10.x
    ...    Confirm that the storage-network-for-rwx-volume-enabled setting is replaced by
    ...    endpoint-network-for-rwx-volume.
    ...
    ...    Upgrade strategy
    ...    During upgrade, the manager detects the legacy storage-network-for-rwx-volume-enabled setting and performs a one-time migration:
    ...    If the legacy setting is false or absent, endpoint-network-for-rwx-volume is created with the default (empty) value.
    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Fail    Environment variable LONGHORN_STABLE_VERSION is not set
    ELSE IF    not '${LONGHORN_STABLE_VERSION}'.startswith('v1.10.')
        Skip    This test case is only required when upgrade from v1.10.x
    END

    Given Setting deleting-confirmation-flag is set to true
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=3
    And Uninstall Longhorn
    And Check Longhorn CRD removed
    And Install Longhorn stable version
    And Set default backupstore
    And Enable Storage Network
    And Setting storage-network should be kube-system/demo-192-168-0-0
    And Setting storage-network-for-rwx-volume-enabled is set to false

    When Upgrade Longhorn to custom version
    Then Setting storage-network should be kube-system/demo-192-168-0-0
    And Setting endpoint-network-for-rwx-volume should be ${EMPTY}

    When Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    Then Check Longhorn workload pods not running with CNI interface lhnet2
        ...    longhorn-csi-plugin
        ...    longhorn-share-manager
    And Write 100 MB data to file data.txt in deployment 0
    And Check deployment 0 data in file data.txt is intact

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
