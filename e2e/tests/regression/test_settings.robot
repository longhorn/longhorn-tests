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
Resource    ../keywords/sharemanager.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Setting Concurrent Rebuild Limit
    [Documentation]    Test if setting Concurrent Replica Rebuild Per Node Limit works correctly.
    Given Set setting concurrent-replica-rebuild-per-node-limit to 1

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

    Given Set setting concurrent-replica-rebuild-per-node-limit to 2
    When Delete volume 0 replica on replica node
    And Delete volume 1 replica on replica node
    Then Both volume 0 and volume 1 replica rebuilding on replica node will start at the same time
    And Wait until volume 0 replica rebuilding completed on replica node
    And Wait until volume 1 replica rebuilding completed on replica node

    Given Set setting concurrent-replica-rebuild-per-node-limit to 1
    When Delete volume 0 replica on replica node
    And Wait until volume 0 replica rebuilding started on replica node
    And Delete volume 1 replica on replica node
    And Delete volume 0 replica on replica node
    And Wait until volume 0 replica rebuilding stopped on replica node
    Then Only one replica rebuilding on replica node will start at a time, either for volume 0 or volume 1
    And Wait until volume 0 replica rebuilding completed on replica node
    And Wait until volume 1 replica rebuilding completed on replica node

    # Test the setting won't intervene normal attachment.
    Given Set setting concurrent-replica-rebuild-per-node-limit to 1
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

Test Setting Storage Network For RWX Volume Enabled
    [Tags]    setting    volume    rwx    storage-network
    [Documentation]    Test if setting Storage Network For RWX Volume Enabled works correctly.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/8184
    ...
    ...                Precondition: Storage network configured.

    Given Set setting storage-network-for-rwx-volume-enabled to false
    When Create persistentvolumeclaim 0 using RWX volume
    And Create deployment 0 with persistentvolumeclaim 0 with max replicaset
    Then Check Longhorn workload pods not annotated with k8s.v1.cni.cncf.io/networks
        ...    longhorn-csi-plugin
        ...    longhorn-share-manager
    And Check sharemanager not using headless service

    And Delete deployment 0
    And Delete persistentvolumeclaim 0
    And Wait for all sharemanager to be deleted

    When Set setting storage-network-for-rwx-volume-enabled to true
    And Create persistentvolumeclaim 1 using RWX volume
    And Create deployment 1 with persistentvolumeclaim 1 with max replicaset
    Then Check Longhorn workload pods is annotated with k8s.v1.cni.cncf.io/networks
        ...    longhorn-csi-plugin
        ...    longhorn-share-manager
    And Check sharemanager is using headless service
