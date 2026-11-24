*** Settings ***
Documentation    Negative Test Cases

Test Tags    replica-rebuilding    negative

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/host.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/longhorn.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Delete Replica While Replica Rebuilding
    Given Create volume 0 with    size=2Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete volume 0 replica on node 0
        And Wait until volume 0 replica rebuilding started on node 0
        And Delete volume 0 replica on node 1
        And Wait until volume 0 replica rebuilding completed on node 0
        And Delete volume 0 replica on node 2

        Then Wait until volume 0 replicas rebuilding completed
        And Wait for volume 0 healthy
        And Check volume 0 data is intact
    END

Reboot Volume Node While Replica Rebuilding
    Given Create volume 0 with    size=5Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete volume 0 replica on volume node
        And Wait until volume 0 replica rebuilding started on volume node
        And Reboot volume 0 volume node

        Then Wait until volume 0 replica rebuilding completed on volume node
        And Wait for volume 0 healthy
        And Check volume 0 data is intact
    END

Reboot Replica Node While Replica Rebuilding
    Given Create volume 0 with    size=5Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete volume 0 replica on replica node
        And Wait until volume 0 replica rebuilding started on replica node
        And Reboot volume 0 replica node

        Then Wait until volume 0 replica rebuilding completed on replica node
        And Wait for volume 0 healthy
        And Check volume 0 data is intact
    END

Reboot Replica Node While Offline Replica Rebuilding
    [Tags]    offline-rebuilding
    [Documentation]    Reboot a replica node during offline replica rebuilding is in progress.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/8443
    Given Create volume 0 with    size=5Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    And Write 4 GB data to volume 0
    And Detach volume 0
    And Wait for volume 0 detached

    When Delete volume 0 replica on node 0
    Then Enable volume 0 offline replica rebuilding
    And Wait until volume 0 replica rebuilding started on node 0

    When Reboot volume 0 replica node
    And Wait for volume 0 detached
    And Volume 0 should have 3 replicas when detached

Delete Replicas One By One After The Volume Is Healthy
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 attached
    And Write 2048 MB data to file data.txt in deployment 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica of deployment 0 volume on node 0
        And Wait for volume of deployment 0 attached and degraded
        And Wait for volume of deployment 0 healthy

        Then Delete replica of deployment 0 volume on node 1
        And Wait for volume of deployment 0 attached and degraded
        And Wait for volume of deployment 0 healthy

        Then Delete replica of deployment 0 volume on node 2
        And Wait for volume of deployment 0 attached and degraded
        And Wait for volume of deployment 0 healthy

        And Wait for deployment 0 pods stable
        Then Check deployment 0 data in file data.txt is intact
    END

Delete Replicas One By One Regardless Of The Volume Health
    [Documentation]    Currently v2 data engine have a chance to hit
    ...                https://github.com/longhorn/longhorn/issues/9216 and will be fixed
    ...                in v1.9.0
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 attached
    And Get deployment 0 pod name
    And Write 2048 MB data to file data.txt in deployment 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica of deployment 0 volume on node 0
        And And Wait until volume of deployment 0 replica rebuilding started on node 0

        Then Delete replica of deployment 0 volume on node 1
        And And Wait until volume of deployment 0 replica rebuilding started on node 1

        Then Delete replica of deployment 0 volume on node 2
        And And Wait until volume of deployment 0 replica rebuilding started on node 2
    END

    And Wait for deployment 0 pods stable
    And Check deployment 0 pod not restarted
    Then Check deployment 0 data in file data.txt is intact

Kill Instance Manager Should Not Expand Volumes By Wrong Replica Rebuilding
    [Tags]    instance-manager    expansion
    [Documentation]    Verify that killing an instance manager does not trigger a replica rebuilding
    ...                to a wrong replica, which would unexpectedly expand the volume.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/5709
    ...
    ...                1. Create 25 deployments that use RWO volumes of 512Mi.
    ...                2. Create 25 deployments that use RWX volumes of 512Mi.
    ...                3. Forcefully kill an instance manager.
    ...                4. Verify that all volumes are healthy.
    ...                5. Verify that all workload pods are running.
    ...                6. Verify that engine.spec.volumeSize = engine.status.currentSize = 512Mi for all volumes.
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    FOR    ${i}    IN RANGE    25
        And Create persistentvolumeclaim ${i}    volume_type=RWO    sc_name=longhorn-test    storage_size=512Mi
        And Create deployment ${i} with persistentvolumeclaim ${i}
    END
    FOR    ${i}    IN RANGE    25    50
        And Create persistentvolumeclaim ${i}    volume_type=RWX    sc_name=longhorn-test    storage_size=512Mi
        And Create deployment ${i} with persistentvolumeclaim ${i}
    END

    When Delete ${DATA_ENGINE} instance manager on node 0

    FOR    ${i}    IN RANGE    50
        Then Wait for volume of deployment ${i} healthy
        And Wait for deployment ${i} pods running
        And Wait for volume engine of deployment ${i} size to be 512Mi
    END
