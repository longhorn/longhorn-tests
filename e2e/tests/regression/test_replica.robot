*** Settings ***
Documentation    Replica Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/workload.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Replica Rebuilding Per Volume Limit
    [Tags]    coretest
    [Documentation]    Test the volume always only have one replica scheduled for rebuild
    ...
    ...    1. Set soft anti-affinity to `true`.
    ...    2. Create a volume with 1 replica.
    ...    3. Attach the volume and write a few hundreds MB data to it.
    ...    4. Scale the volume replica to 5.
    ...    5. Monitor the volume replica list to make sure there should be only 1 replica in WO state.
    ...    6. Wait for the volume to complete rebuilding. Then remove 4 of the 5 replicas.
    ...    7. Monitoring the volume replica list again.
    ...    8. Once the rebuild was completed again, verify the data checksum.
    Given Set setting replica-soft-anti-affinity to true
    And Create volume 0 with    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    When Update volume 0 replica count to 5
    Then Only one replica rebuilding will start at a time for volume 0
    And Monitor only one replica rebuilding will start at a time for volume 0
    And Wait until volume 0 replicas rebuilding completed

    When Delete 4 replicas of volume 0
    Then Only one replica rebuilding will start at a time for volume 0
    And Monitor only one replica rebuilding will start at a time for volume 0
    And Wait until volume 0 replicas rebuilding completed
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Test Offline Replica Rebuilding
    [Tags]    coretest    offline-rebuilding
    [Documentation]    Test offline replica rebuilding for a volume.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/8443
    Given Create volume 0 with    size=6Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write 5 GB data to volume 0
    And Detach volume 0
    And Wait for volume 0 detached

    When Delete volume 0 replica on node 0
    Then Enable volume 0 offline replica rebuilding
    And Wait until volume 0 replica rebuilding started on node 0
    And Wait for volume 0 detached
    And Volume 0 should have 3 replicas when detached
    And Ignore volume 0 offline replica rebuilding

    When Delete volume 0 replica on node 0
    Then Set setting offline-replica-rebuilding to true
    And Wait until volume 0 replica rebuilding started on node 0
    And Wait for volume 0 detached
    And Volume 0 should have 3 replicas when detached
    And Set setting offline-replica-rebuilding to false

Test Preempt Offline Replica Rebuilding By A Workload
    [Tags]    coretest    offline-rebuilding
    [Documentation]    Test preempt offline replica rebuilding by a workload.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/8443
    Given Create volume 0 with    size=6Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Detach volume 0
    And Wait for volume 0 detached
    And Create deployment 0 with volume 0
    And Wait for volume 0 healthy
    And Write 5120 MB data to file data.txt in deployment 0
    And Scale down deployment 0 to detach volume
    And Wait for volume 0 detached

    # enable offline replica rebuilding.
    When Delete volume 0 replica on node 0
    And Enable volume 0 offline replica rebuilding
    # wait for offline rebuilding to start.
    Then Wait until volume 0 replica rebuilding started on node 0
    And Volume 0 should have 3 replicas running

    # scale up the workload and it will preempt the offline rebuilding.
    When Scale up deployment 0 to attach volume
    # the volume might be detched or not so we only wait for volume becomes healthy.
    # we should try to check if offline rebuilding will be canceled and online rebuilding takes over.
    # then the volume becomes healthy without offline rebuilding.
    And Wait for volume 0 healthy
    # write some data with workload pod to check if the workload works.
    And Write 64 MB data to file data.txt in deployment 0
    Then Check deployment 0 data in file data.txt is intact
