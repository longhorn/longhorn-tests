*** Settings ***
Documentation    Negative Test Cases

Test Tags    negative

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/setting.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Kubelet Restart Immediately Test
    [Arguments]    ${numberOfReplicas}
    Given Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=${numberOfReplicas}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass
    And Create statefulset 1 using RWX volume with longhorn-test storageclass
    And Write 100 MB data to file data in statefulset 0
    And Write 100 MB data to file data in statefulset 1

    When Stop volume nodes kubelet for 5 seconds    statefulset 0    statefulset 1
    Check statefulset 0 pods did not restart
    Check statefulset 1 pods did not restart
    And Check statefulset 0 data in file data is intact
    Then Check statefulset 1 data in file data is intact

    And Scale down statefulset 0 to detach volume
    And Scale down statefulset 1 to detach volume
    And Scale up statefulset 0 to attach volume
    And Scale up statefulset 1 to attach volume

    And Check statefulset 0 data in file data is intact
    Then Check statefulset 1 data in file data is intact

Kubelet Restart After Temporary Downtime
    [Arguments]    ${numberOfReplicas}
    Given Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=${numberOfReplicas}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass
    And Create statefulset 1 using RWX volume with longhorn-test storageclass
    And Write 100 MB data to file data in statefulset 0
    And Write 100 MB data to file data in statefulset 1

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Stop volume nodes kubelet for 120 seconds    statefulset 0    statefulset 1
        And Wait for volume of statefulset 0 attached and unknown
        And Wait for volume of statefulset 1 attached and degraded
        And Wait for volume of statefulset 0 healthy
        And Wait for volume of statefulset 1 healthy
        Then Wait for workloads pods stable    statefulset 0    statefulset 1

        And Scale down statefulset 0 to detach volume
        And Scale down statefulset 1 to detach volume
        And Scale up statefulset 0 to attach volume
        And Scale up statefulset 1 to attach volume

        And Check statefulset 0 data in file data is intact
        Then Check statefulset 1 data in file data is intact
    END

*** Test Cases ***
Restart Volume Node Kubelet While Workload Heavy Writing
    Given Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass
    And Create statefulset 1 using RWX volume with longhorn-test storageclass

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of statefulset 0
        And Keep writing data to pod of statefulset 1

        When Stop volume nodes kubelet for 10 seconds    statefulset 0    statefulset 1
        And Wait for volume of statefulset 0 healthy
        And Wait for volume of statefulset 1 healthy
        And Wait for workloads pods stable    statefulset 0    statefulset 1

        Then Check statefulset 0 works
        And Check statefulset 1 works
    END

Stop Volume Node Kubelet For More Than Pod Eviction Timeout While Workload Heavy Writing
    Given Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass
    And Create statefulset 1 using RWX volume with longhorn-test storageclass

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of statefulset 0
        And Keep writing data to pod of statefulset 1

        When Stop volume nodes kubelet for 360 seconds    statefulset 0    statefulset 1
        And Wait for volume of statefulset 0 healthy
        And Wait for volume of statefulset 1 healthy
        And Wait for workloads pods stable    statefulset 0    statefulset 1

        Then Check statefulset 0 works
        And Check statefulset 1 works
    END

Restart Volume Node Kubelet Immediately
    Kubelet Restart Immediately Test    numberOfReplicas=3

Restart Volume Node Kubelet Immediately On Single Node Cluster
    Given Cordon node 1
    And Cordon node 2
    Then Kubelet Restart Immediately Test    numberOfReplicas=1

Restart Volume Node Kubelet After Temporary Downtime
    Given Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass
    And Create statefulset 1 using RWX volume with longhorn-test storageclass
    And Write 100 MB data to file data in statefulset 0
    And Write 100 MB data to file data in statefulset 1

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Stop volume nodes kubelet for 120 seconds    statefulset 0    statefulset 1
        And Wait for volume of statefulset 0 attached and unknown
        And Wait for volume of statefulset 1 attached and degraded
        And Wait for volume of statefulset 0 healthy
        And Wait for volume of statefulset 1 healthy
        Then Wait for workloads pods stable    statefulset 0    statefulset 1

        And Scale down statefulset 0 to detach volume
        And Scale down statefulset 1 to detach volume
        And Scale up statefulset 0 to attach volume
        And Scale up statefulset 1 to attach volume

        And Check statefulset 0 data in file data is intact
        Then Check statefulset 1 data in file data is intact
    END
    
Restart Volume Node Kubelet After Temporary Downtime On Single Node Cluster
    Given Cordon node 1
    And Cordon node 2
    When Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}        numberOfReplicas=1
    And Create statefulset 0 using RWO volume with longhorn-test storageclass
    And Create statefulset 1 using RWX volume with longhorn-test storageclass
    And Write 100 MB data to file data in statefulset 0
    And Write 100 MB data to file data in statefulset 1

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Stop volume nodes kubelet for 120 seconds    statefulset 0    statefulset 1
        And Wait for volume of statefulset 0 attached and unknown
        And Wait for statefulset 1 volume detached
        And Wait for volume of statefulset 0 healthy
        And Wait for volume of statefulset 1 healthy
        Then Wait for workloads pods stable    statefulset 0    statefulset 1

        And Scale down statefulset 0 to detach volume
        And Scale down statefulset 1 to detach volume
        And Scale up statefulset 0 to attach volume
        And Scale up statefulset 1 to attach volume

        And Check statefulset 0 data in file data is intact
        Then Check statefulset 1 data in file data is intact
    END
