*** Settings ***
Documentation    Storage Network Test Cases

Test Tags    regression    storage-network

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/sharemanager.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/volume.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Storage Network Should Not Restart Migratable RWX Volume Workload Pods
    [Tags]    setting    volume    migratable-rwx    csi
    [Documentation]    Verifies that when the `storage-network-for-rwx-volume-enabled`
    ...                setting is set to `true`, workload pods using migratable
    ...                RWX volumes do not restart unexpectedly.
    ...
    ...                This test ensures that restarting the `longhorn-csi-plugin`
    ...                pods does not impact workloads attached to migratable RWX
    ...                volumes.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/11158
    ...
    ...                Precondition: Storage network configured.
    Given Setting endpoint-network-for-rwx-volume is set to kube-system/demo-192-168-0-0
    And Wait for Longhorn workloads pods stable
        ...    longhorn-csi-plugin
    And Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Create persistentvolume for volume 0
    And Create persistentvolumeclaim for volume 0
    And Create deployment 0 using volume 0    num_replicaset=1
    And Record deployment 0 pod UIDs

    When Delete Longhorn DaemonSet longhorn-csi-plugin pod on all nodes

    Then Assert pod UIDs of deployment 0 remain unchanged    num_checks=60

Test Updating RWX Volume Endpoint Network When There Are Migratable RWX Volumes Attached
    [Tags]    setting
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12644
    ...    Verifies that updating the `endpoint-network-for-rwx-volume`
    ...    setting should succeed when there are migratable RWX volumes attached.
    ...    1. Create a migratable RWX volume and attach it to a node
    ...    2. Update the `endpoint-network-for-rwx-volume` setting to kube-system/demo-192-168-0-0
    ...    3. Create a RWX PVC and a deployment using the PVC, and verify the workload pod is running with CNI interface lhnet2
    Given Setting storage-network should be kube-system/demo-192-168-0-0
    And Setting endpoint-network-for-rwx-volume is set to ${EMPTY}

    # a normal rwx migratable volume that is manually attached to nodes without being mounted to a workload
    # there is no share manager pod involved, so it won't be affected by the endpoint network change
    And Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy

    When Setting endpoint-network-for-rwx-volume is set to kube-system/demo-192-168-0-0
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    Then Check Longhorn workload pods is running with CNI interface lhnet2
        ...    longhorn-csi-plugin
        ...    longhorn-share-manager

Test RWX Volume Endpoint Network With Storage Network Enabled
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
    [Tags]    upgrade
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
    [Tags]    upgrade
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
