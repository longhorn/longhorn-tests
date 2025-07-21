*** Settings ***
Documentation    Negative Test Cases

Test Tags    cluster    negative

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/host.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/metrics.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Restart Cluster While Workload Heavy Writing
    Given Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create storageclass strict-local with    numberOfReplicas=1    dataLocality=strict-local    dataEngine=${DATA_ENGINE}
    And Create storageclass nfs-4-2 with    nfsOptions=vers=4.2,noresvport,timeo=450,retrans=8    dataEngine=${DATA_ENGINE}
    And Create storageclass nfs-hard-mount with    nfsOptions=hard,timeo=50,retrans=1    dataEngine=${DATA_ENGINE}
    And Create storageclass nfs-soft-mount with    nfsOptions=soft,timeo=250,retrans=5    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-test
    And Create persistentvolumeclaim 2    volume_type=RWO    sc_name=strict-local
    And Create persistentvolumeclaim 3    volume_type=RWX    sc_name=nfs-4-2
    And Create persistentvolumeclaim 4    volume_type=RWX    sc_name=nfs-hard-mount
    And Create persistentvolumeclaim 5    volume_type=RWX    sc_name=nfs-soft-mount
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

Check If Nodes Are Under Memory Pressure After Cluster Restart
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create storageclass strict-local with    numberOfReplicas=1    dataLocality=strict-local    dataEngine=${DATA_ENGINE}
    And Create storageclass nfs-4-2 with    nfsOptions=vers=4.2,noresvport,timeo=450,retrans=8    dataEngine=${DATA_ENGINE}
    And Create storageclass nfs-hard-mount with    nfsOptions=hard,timeo=50,retrans=1    dataEngine=${DATA_ENGINE}
    And Create storageclass nfs-soft-mount with    nfsOptions=soft,timeo=250,retrans=5    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass
    And Create statefulset 1 using RWX volume with longhorn-test storageclass
    And Create statefulset 2 using RWO volume with strict-local storageclass
    And Create statefulset 3 using RWX volume with nfs-4-2 storageclass
    And Create statefulset 4 using RWX volume with nfs-hard-mount storageclass
    And Create statefulset 5 using RWX volume with nfs-soft-mount storageclass
    And Write 1024 MB data to file data.bin in statefulset 0
    And Write 1024 MB data to file data.bin in statefulset 1
    And Write 1024 MB data to file data.bin in statefulset 2
    And Write 1024 MB data to file data.bin in statefulset 3
    And Write 1024 MB data to file data.bin in statefulset 4
    And Write 1024 MB data to file data.bin in statefulset 5

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}

        And Create snapshot ${i} for statefulset 0 volume
        And Create snapshot ${i} for statefulset 1 volume
        And Create snapshot ${i} for statefulset 2 volume
        And Create snapshot ${i} for statefulset 3 volume
        And Create snapshot ${i} for statefulset 4 volume
        And Create snapshot ${i} for statefulset 5 volume

        When Restart cluster
        And Wait for longhorn ready
        And Wait for workloads pods stable
        ...    statefulset 0    statefulset 1    statefulset 2    statefulset 3    statefulset 4    statefulset 5

        Then Check statefulset 0 works
        And Check statefulset 1 works
        And Check statefulset 2 works
        And Check statefulset 3 works
        And Check statefulset 4 works
        And Check statefulset 5 works
        And Check if nodes are under memory pressure
    END

Scale Down Workloads Before Restarting Cluster
    [Documentation]    https://github.com/longhorn/longhorn/issues/7258
    ...                1. Create some deployments
    ...                2. Scale down the deployments without waiting for the volumes completedly detached
    ...                3. Restart the cluster
    ...                4. After the cluster restarted, scale up the deployments to check if the volumes
    ...                   can still be attached, and the workloads work
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create storageclass strict-local with    numberOfReplicas=1    dataLocality=strict-local    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-test
    And Create persistentvolumeclaim 2    volume_type=RWO    sc_name=strict-local
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Create deployment 2 with persistentvolumeclaim 2
    And Write 128 MB data to file data.bin in deployment 0
    And Write 128 MB data to file data.bin in deployment 1
    And Write 128 MB data to file data.bin in deployment 2

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Scale deployment 0 to 0
        And Scale deployment 1 to 0
        And Scale deployment 2 to 0
        And Restart cluster
        And Wait for longhorn ready

        Then Scale deployment 0 to 1
        And Scale deployment 1 to 1
        And Scale deployment 2 to 1
        And Wait for volume of deployment 0 attached
        And Wait for volume of deployment 1 attached
        And Wait for volume of deployment 2 attached
        And Wait for volume of deployment 0 healthy
        And Wait for volume of deployment 1 healthy
        And Wait for volume of deployment 2 healthy
        And Wait for workloads pods stable
        ...    deployment 0    deployment 1    deployment 2
        And Check deployment 0 data in file data.bin is intact
        And Check deployment 1 data in file data.bin is intact
        And Check deployment 2 data in file data.bin is intact
    END
