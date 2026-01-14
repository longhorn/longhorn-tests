*** Settings ***
Documentation    Negative Test Cases

Test Tags    kubelet-restart    negative

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/node.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Restart Volume Node Kubelet While Workload Heavy Writing
    [Arguments]    ${RWX_VOLUME_FAST_FAILOVER}
    Given Setting rwx-volume-fast-failover is set to ${RWX_VOLUME_FAST_FAILOVER}
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
    [Arguments]    ${RWX_VOLUME_FAST_FAILOVER}
    Given Setting rwx-volume-fast-failover is set to ${RWX_VOLUME_FAST_FAILOVER}
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

Kubelet Restart Immediately Test
    [Arguments]    ${numberOfReplicas}    ${RWX_VOLUME_FAST_FAILOVER}
    Given Setting rwx-volume-fast-failover is set to ${RWX_VOLUME_FAST_FAILOVER}

    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=${numberOfReplicas}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass
    And Create statefulset 1 using RWX volume with longhorn-test storageclass
    And Write 100 MB data to file data in statefulset 0
    And Write 100 MB data to file data in statefulset 1

    When Stop volume nodes kubelet for 5 seconds    statefulset 0    statefulset 1
    And Check statefulset 0 pods did not restart
    And Check statefulset 1 pods did not restart
    And Check statefulset 0 data in file data is intact
    Then Check statefulset 1 data in file data is intact

    And Scale down statefulset 0 to detach volume
    And Scale down statefulset 1 to detach volume
    And Scale up statefulset 0 to attach volume
    And Scale up statefulset 1 to attach volume

    And Check statefulset 0 data in file data is intact
    Then Check statefulset 1 data in file data is intact

Kubelet Restart After Temporary Downtime
    [Arguments]    ${numberOfReplicas}    ${RWX_VOLUME_FAST_FAILOVER}
    Given Setting rwx-volume-fast-failover is set to ${RWX_VOLUME_FAST_FAILOVER}
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

Restart Volume Node Kubelet After Temporary Downtime
    [Arguments]    ${RWX_VOLUME_FAST_FAILOVER}
    Given Setting rwx-volume-fast-failover is set to ${RWX_VOLUME_FAST_FAILOVER}
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
    [Arguments]    ${RWX_VOLUME_FAST_FAILOVER}
    Given Cordon node 1
    And Cordon node 2
    When Setting rwx-volume-fast-failover is set to ${RWX_VOLUME_FAST_FAILOVER}
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

*** Test Cases ***
Restart Volume Node Kubelet While Workload Heavy Writing With RWX Fast Failover Enabled
    Restart Volume Node Kubelet While Workload Heavy Writing    RWX_VOLUME_FAST_FAILOVER=true

Restart Volume Node Kubelet While Workload Heavy Writing With RWX Fast Failover Disabled
    Restart Volume Node Kubelet While Workload Heavy Writing    RWX_VOLUME_FAST_FAILOVER=false

Stop Volume Node Kubelet For More Than Pod Eviction Timeout While Workload Heavy Writing With RWX Fast Failover Enabled
    Stop Volume Node Kubelet For More Than Pod Eviction Timeout While Workload Heavy Writing    RWX_VOLUME_FAST_FAILOVER=true

Stop Volume Node Kubelet For More Than Pod Eviction Timeout While Workload Heavy Writing With RWX Fast Failover Disabled
    Stop Volume Node Kubelet For More Than Pod Eviction Timeout While Workload Heavy Writing    RWX_VOLUME_FAST_FAILOVER=false

Restart Control Plane Kubelet While Workload Heavy Writing
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create statefulset 0    volume_type=RWO    sc_name=longhorn-test
    And Create statefulset 1    volume_type=RWX    sc_name=longhorn-test

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of statefulset 0
        And Keep writing data to pod of statefulset 1

        When Stop control plane kubelet for 10 seconds
        And Wait for volume of statefulset 0 healthy
        And Wait for volume of statefulset 1 healthy
        And Wait for workloads pods stable    statefulset 0    statefulset 1

        Then Check statefulset 0 works
        And Check statefulset 1 works
    END

Restart Volume Node Kubelet Immediately With RWX Fast Failover Enabled
    Kubelet Restart Immediately Test    numberOfReplicas=3    RWX_VOLUME_FAST_FAILOVER=true

Restart Volume Node Kubelet Immediately With RWX Fast Failover Disabled
    Kubelet Restart Immediately Test    numberOfReplicas=3    RWX_VOLUME_FAST_FAILOVER=false

Restart Volume Node Kubelet Immediately On Single Node Cluster With RWX Fast Failover Enabled
    Given Cordon node 1
    And Cordon node 2
    Then Kubelet Restart Immediately Test    numberOfReplicas=1    RWX_VOLUME_FAST_FAILOVER=true

Restart Volume Node Kubelet Immediately On Single Node Cluster With RWX Fast Failover Disabled
    Given Cordon node 1
    And Cordon node 2
    Then Kubelet Restart Immediately Test    numberOfReplicas=1    RWX_VOLUME_FAST_FAILOVER=false

Restart Volume Node Kubelet After Temporary Downtime With RWX Fast Failover Enabled
    Restart Volume Node Kubelet After Temporary Downtime    RWX_VOLUME_FAST_FAILOVER=true

Restart Volume Node Kubelet After Temporary Downtime With RWX Fast Failover Disabled
    Restart Volume Node Kubelet After Temporary Downtime    RWX_VOLUME_FAST_FAILOVER=false
    
Restart Volume Node Kubelet After Temporary Downtime On Single Node Cluster With RWX Fast Failover Enabled
    Restart Volume Node Kubelet After Temporary Downtime On Single Node Cluster    RWX_VOLUME_FAST_FAILOVER=true

Restart Volume Node Kubelet After Temporary Downtime On Single Node Cluster With RWX Fast Failover Disabled
    Restart Volume Node Kubelet After Temporary Downtime On Single Node Cluster    RWX_VOLUME_FAST_FAILOVER=false
