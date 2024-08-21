*** Settings ***
Documentation    Negative Test Cases

Test Tags    negative    cluster

Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/host.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/setting.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1
${CONTROL_PLANE_NODE_NETWORK_LATENCY_IN_MS}    0
${RWX_VOLUME_FAST_FAILOVER}    false
${DATA_ENGINE}    v1


*** Test Cases ***
Restart Cluster While Workload Heavy Writing
    Given Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create storageclass strict-local with    numberOfReplicas=1    dataLocality=strict-local    dataEngine=${DATA_ENGINE}
    And Create storageclass nfs-4-2 with    nfsOptions=vers=4.2,noresvport,timeo=450,retrans=8    dataEngine=${DATA_ENGINE}
    And Create storageclass nfs-hard-mount with    nfsOptions=hard,timeo=50,retrans=1    dataEngine=${DATA_ENGINE}
    And Create storageclass nfs-soft-mount with    nfsOptions=soft,timeo=250,retrans=5    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0 using RWO volume with longhorn-test storageclass
    And Create persistentvolumeclaim 1 using RWX volume with longhorn-test storageclass
    And Create persistentvolumeclaim 2 using RWO volume with strict-local storageclass
    And Create persistentvolumeclaim 3 using RWX volume with nfs-4-2 storageclass
    And Create persistentvolumeclaim 4 using RWX volume with nfs-hard-mount storageclass
    And Create persistentvolumeclaim 5 using RWX volume with nfs-soft-mount storageclass
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Create deployment 2 with persistentvolumeclaim 2
    And Create deployment 3 with persistentvolumeclaim 3
    And Create deployment 4 with persistentvolumeclaim 4
    And Create deployment 5 with persistentvolumeclaim 5
    And Create statefulset 0 using RWO volume with longhorn-test storageclass
    And Create statefulset 1 using RWX volume with longhorn-test storageclass
    And Create statefulset 2 using RWO volume with strict-local storageclass
    And Create statefulset 3 using RWX volume with nfs-4-2 storageclass
    And Create statefulset 4 using RWX volume with nfs-hard-mount storageclass
    And Create statefulset 5 using RWX volume with nfs-soft-mount storageclass

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of deployment 0
        And Keep writing data to pod of deployment 1
        And Keep writing data to pod of deployment 2
        And Keep writing data to pod of deployment 3
        And Keep writing data to pod of deployment 4
        And Keep writing data to pod of deployment 5
        And Keep writing data to pod of statefulset 0
        And Keep writing data to pod of statefulset 1
        And Keep writing data to pod of statefulset 2
        And Keep writing data to pod of statefulset 3
        And Keep writing data to pod of statefulset 4
        And Keep writing data to pod of statefulset 5

        When Restart cluster
        And Wait for longhorn ready
        And Wait for workloads pods stable
        ...    deployment 0    deployment 1    deployment 2    deployment 3    deployment 4    deployment 5
        ...    statefulset 0    statefulset 1    statefulset 2    statefulset 3    statefulset 4    statefulset 5

        Then Check deployment 0 works
        And Check deployment 1 works
        And Check deployment 2 works
        And Check deployment 3 works
        And Check deployment 4 works
        And Check deployment 5 works
        And Check statefulset 0 works
        And Check statefulset 1 works
        And Check statefulset 2 works
        And Check statefulset 3 works
        And Check statefulset 4 works
        And Check statefulset 5 works
    END
