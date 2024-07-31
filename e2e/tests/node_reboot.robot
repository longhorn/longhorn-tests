*** Settings ***
Documentation    Negative Test Cases

Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/host.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/recurringjob.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/setting.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1
${VOLUME_TYPE}    RWO
${CONTROL_PLANE_NODE_NETWORK_LATENCY_IN_MS}    0
${RWX_VOLUME_FAST_FAILOVER}    false

*** Test Cases ***
Reboot Node One By One While Workload Heavy Writing
    [Tags]    reboot
    Given Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass strict-local with    numberOfReplicas=1    dataLocality=strict-local
    And Create persistentvolumeclaim 0 using RWO volume
    And Create persistentvolumeclaim 1 using RWX volume
    And Create persistentvolumeclaim 2 using RWO volume with strict-local storageclass

    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Create deployment 2 with persistentvolumeclaim 2

    And Create statefulset 0 using RWO volume
    And Create statefulset 1 using RWX volume
    And Create statefulset 2 using RWO volume with strict-local storageclass

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of deployment 0
        And Keep writing data to pod of deployment 1
        And Keep writing data to pod of deployment 2
        And Keep writing data to pod of statefulset 0
        And Keep writing data to pod of statefulset 1
        And Keep writing data to pod of statefulset 2

        When Reboot node 0
        And Reboot node 1
        And Reboot node 2
        And Wait for longhorn ready
        And Wait for workloads pods stable
        ...    deployment 0    deployment 1    deployment 2
        ...    statefulset 0    statefulset 1    statefulset 2

        Then Check deployment 0 works
        And Check deployment 1 works
        And Check deployment 2 works
        And Check statefulset 0 works
        And Check statefulset 1 works
        And Check statefulset 2 works
    END

Power Off Node One By Once For More Than Pod Eviction Timeout While Workload Heavy Writing
    [Tags]    reboot
    Given Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass strict-local with    numberOfReplicas=1    dataLocality=strict-local
    And Create persistentvolumeclaim 0 using RWO volume
    And Create persistentvolumeclaim 1 using RWX volume
    And Create persistentvolumeclaim 2 using RWO volume with strict-local storageclass

    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Create deployment 2 with persistentvolumeclaim 2

    And Create statefulset 0 using RWO volume
    And Create statefulset 1 using RWX volume
    And Create statefulset 2 using RWO volume with strict-local storageclass

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of deployment 0
        And Keep writing data to pod of deployment 1
        And Keep writing data to pod of deployment 2
        And Keep writing data to pod of statefulset 0
        And Keep writing data to pod of statefulset 1
        And Keep writing data to pod of statefulset 2

        When Power off node 0 for 6 mins
        And Power off node 1 for 6 mins
        And Power off node 2 for 6 mins
        And Wait for longhorn ready
        And Wait for workloads pods stable
        ...    deployment 0    deployment 1    deployment 2
        ...    statefulset 0    statefulset 1    statefulset 2

        Then Check deployment 0 works
        And Check deployment 1 works
        And Check deployment 2 works
        And Check statefulset 0 works
        And Check statefulset 1 works
        And Check statefulset 2 works
    END

Reboot All Worker Nodes While Workload Heavy Writing
    [Tags]    reboot
    Given Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass strict-local with    numberOfReplicas=1    dataLocality=strict-local
    And Create persistentvolumeclaim 0 using RWO volume
    And Create persistentvolumeclaim 1 using RWX volume
    And Create persistentvolumeclaim 2 using RWO volume with strict-local storageclass

    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Create deployment 2 with persistentvolumeclaim 2

    And Create statefulset 0 using RWO volume
    And Create statefulset 1 using RWX volume
    And Create statefulset 2 using RWO volume with strict-local storageclass

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of deployment 0
        And Keep writing data to pod of deployment 1
        And Keep writing data to pod of deployment 2
        And Keep writing data to pod of statefulset 0
        And Keep writing data to pod of statefulset 1
        And Keep writing data to pod of statefulset 2

        When Restart all worker nodes
        And Wait for longhorn ready
        And Wait for workloads pods stable
        ...    deployment 0    deployment 1    deployment 2
        ...    statefulset 0    statefulset 1    statefulset 2

        Then Check deployment 0 works
        And Check deployment 1 works
        And Check deployment 2 works
        And Check statefulset 0 works
        And Check statefulset 1 works
        And Check statefulset 2 works
    END

Power Off All Worker Nodes For More Than Pod Eviction Timeout While Workload Heavy Writing
    [Tags]    reboot
    Given Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass strict-local with    numberOfReplicas=1    dataLocality=strict-local
    And Create persistentvolumeclaim 0 using RWO volume
    And Create persistentvolumeclaim 1 using RWX volume
    And Create persistentvolumeclaim 2 using RWO volume with strict-local storageclass

    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Create deployment 2 with persistentvolumeclaim 2

    And Create statefulset 0 using RWO volume
    And Create statefulset 1 using RWX volume
    And Create statefulset 2 using RWO volume with strict-local storageclass

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of deployment 0
        And Keep writing data to pod of deployment 1
        And Keep writing data to pod of deployment 2
        And Keep writing data to pod of statefulset 0
        And Keep writing data to pod of statefulset 1
        And Keep writing data to pod of statefulset 2

        When Power off all worker nodes for 6 mins
        And Wait for longhorn ready
        And Wait for workloads pods stable
        ...    deployment 0    deployment 1    deployment 2
        ...    statefulset 0    statefulset 1    statefulset 2

        Then Check deployment 0 works
        And Check deployment 1 works
        And Check deployment 2 works
        And Check statefulset 0 works
        And Check statefulset 1 works
        And Check statefulset 2 works
    END

Reboot Volume Node While Workload Heavy Writing
    [Tags]    reboot
    Given Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create statefulset 0 using ${VOLUME_TYPE} volume
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of statefulset 0

        When Reboot volume node of statefulset 0
        And Wait for volume of statefulset 0 healthy
        And Wait for statefulset 0 pods stable

        Then Check statefulset 0 works
    END

Power Off Volume Node For More Than Pod Eviction Timeout While Workload Heavy Writing
    [Tags]    reboot
    Given Create statefulset 0 using RWO volume

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of statefulset 0

        When Power off volume node of statefulset 0 for 6 minutes
        And Wait for volume of statefulset 0 healthy
        And Wait for statefulset 0 pods stable

        Then Check statefulset 0 works
    END

Reboot Volume Node While Heavy Writing And Recurring Jobs Exist
    [Tags]    recurring_job
    Given Create volume 0 with    size=2Gi    numberOfReplicas=1
    And Create volume 1 with    size=2Gi    numberOfReplicas=3
    And Attach volume 0
    And Attach volume 1
    And Keep writing data to volume 0
    And Keep writing data to volume 1
    And Create snapshot and backup recurringjob for volume 0
    And Create snapshot and backup recurringjob for volume 1

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Reboot volume 0 volume node
        And Wait for volume 0 healthy

        Then Check recurringjobs for volume 0 work
        And Check recurringjobs for volume 1 work
        And Check volume 0 works
        And Check volume 1 works
    END

Reboot Replica Node While Heavy Writing And Recurring Jobs Exist
    [Tags]    recurring_job
    Given Create volume 0 with    size=2Gi    numberOfReplicas=1
    And Create volume 1 with    size=2Gi    numberOfReplicas=3
    And Attach volume 0
    And Attach volume 1
    And Keep writing data to volume 0
    And Keep writing data to volume 1
    And Create snapshot and backup recurringjob for volume 0
    And Create snapshot and backup recurringjob for volume 1

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Reboot volume 1 replica node
        And Wait for volume 1 healthy

        Then Check recurringjobs for volume 0 work
        And Check recurringjobs for volume 1 work
        And Check volume 0 works
        And Check volume 1 works
    END

Power Off Replica Node Should Not Rebuild New Replica On Same Node
    [Tags]    replica   reboot
    [Documentation]    Ensures that no new replica is created and rebuilt on the
    ...                same node if the node is powered off for a duration longer
    ...                than the replica-replenishment-wait-interval. When the node
    ...                is powered on, the existing replica should be reused.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/1992

    Given Set setting replica-replenishment-wait-interval to 30
    And Set setting replica-soft-anti-affinity to false
    And Create volume 0 with    size=1Gi    numberOfReplicas=3
    And Attach volume 0 to node 0
    And Record volume 0 replica names

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Power off node 1 for 1 mins
        And Wait for longhorn ready
        And Wait for volume 0 healthy

        Then Check volume 0 replica names are as recorded
    END
