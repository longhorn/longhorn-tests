*** Settings ***
Documentation    Negative Test Cases

Test Tags    service-restart    negative

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/node.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/sharemanager.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/host.resource

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

Restart Volume Node Kubelet After Temporary Downtime
    [Arguments]    ${RWX_VOLUME_FAST_FAILOVER}
    Given Setting rwx-volume-fast-failover is set to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass
    And Create statefulset 1 using RWX volume with longhorn-test storageclass
    And Write 100 MB data to file data in statefulset 0
    And Write 100 MB data to file data in statefulset 1

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Stop volume nodes kubelet for 120 seconds    statefulset 0    statefulset 1    wait=False
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
        When Stop volume nodes kubelet for 120 seconds    statefulset 0    statefulset 1    wait=False
        And Wait for volume of statefulset 0 attached and unknown
        And Wait for volume of statefulset 1 detached
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
    [Tags]    kubelet-restart
    Restart Volume Node Kubelet While Workload Heavy Writing    RWX_VOLUME_FAST_FAILOVER=true

Restart Volume Node Kubelet While Workload Heavy Writing With RWX Fast Failover Disabled
    [Tags]    kubelet-restart
    Restart Volume Node Kubelet While Workload Heavy Writing    RWX_VOLUME_FAST_FAILOVER=false

Stop Volume Node Kubelet For More Than Pod Eviction Timeout While Workload Heavy Writing With RWX Fast Failover Enabled
    [Tags]    kubelet-restart
    Stop Volume Node Kubelet For More Than Pod Eviction Timeout While Workload Heavy Writing    RWX_VOLUME_FAST_FAILOVER=true

Stop Volume Node Kubelet For More Than Pod Eviction Timeout While Workload Heavy Writing With RWX Fast Failover Disabled
    [Tags]    kubelet-restart
    Stop Volume Node Kubelet For More Than Pod Eviction Timeout While Workload Heavy Writing    RWX_VOLUME_FAST_FAILOVER=false

Restart Control Plane Kubelet While Workload Heavy Writing
    [Tags]    kubelet-restart
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
    [Tags]    kubelet-restart
    Kubelet Restart Immediately Test    numberOfReplicas=3    RWX_VOLUME_FAST_FAILOVER=true

Restart Volume Node Kubelet Immediately With RWX Fast Failover Disabled
    [Tags]    kubelet-restart
    Kubelet Restart Immediately Test    numberOfReplicas=3    RWX_VOLUME_FAST_FAILOVER=false

Restart Volume Node Kubelet Immediately On Single Node Cluster With RWX Fast Failover Enabled
    [Tags]    kubelet-restart    single-replica
    Given Cordon node 1
    And Cordon node 2
    Then Kubelet Restart Immediately Test    numberOfReplicas=1    RWX_VOLUME_FAST_FAILOVER=true

Restart Volume Node Kubelet Immediately On Single Node Cluster With RWX Fast Failover Disabled
    [Tags]    kubelet-restart    single-replica
    Given Cordon node 1
    And Cordon node 2
    Then Kubelet Restart Immediately Test    numberOfReplicas=1    RWX_VOLUME_FAST_FAILOVER=false

Restart Volume Node Kubelet After Temporary Downtime With RWX Fast Failover Enabled
    [Tags]    kubelet-restart
    Restart Volume Node Kubelet After Temporary Downtime    RWX_VOLUME_FAST_FAILOVER=true

Restart Volume Node Kubelet After Temporary Downtime With RWX Fast Failover Disabled
    [Tags]    kubelet-restart
    Restart Volume Node Kubelet After Temporary Downtime    RWX_VOLUME_FAST_FAILOVER=false
    
Restart Volume Node Kubelet After Temporary Downtime On Single Node Cluster With RWX Fast Failover Enabled
    [Tags]    kubelet-restart    single-replica
    Restart Volume Node Kubelet After Temporary Downtime On Single Node Cluster    RWX_VOLUME_FAST_FAILOVER=true

Restart Volume Node Kubelet After Temporary Downtime On Single Node Cluster With RWX Fast Failover Disabled
    [Tags]    kubelet-restart    single-replica
    Restart Volume Node Kubelet After Temporary Downtime On Single Node Cluster    RWX_VOLUME_FAST_FAILOVER=false

Test Best Effort Auto Balance In Unstable Cluster
    [Documentation]    Test replica best effort auto balance with unstable node
    [Tags]    kubelet-restart    long-running
    ...    Issue: https://github.com/longhorn/longhorn/issues/12926
    ...
    ...    1. In a 3-node cluster, tag node 0 and node 1 with zone-a, node 2 with zone-b.
    ...    2. Stop kubelet on node 2, wait 35 minutes, then restart it so its Ready
    ...       condition lastTransitionTime is >30 min later than zone-a nodes.
    ...       Ready condition lastTransitionTime updates only when the status changes.
    ...       Cordoning a node doesn't make the node NotReady, but it only makes the node Unschedulable,
    ...       so it's not suitable for this case.
    ...    3. Verify the lastTransitionTime gap between node 2 and node 0/1 is >30 min.
    ...    4. Set Replica Auto Balance to best-effort.
    ...    5. Disable scheduling for node 2.
    ...    6. Create and attach a 2-replica volume. Replicas go to zone-a nodes.
    ...    7. Wait for volume attached and healthy.
    ...    8. Enable scheduling for node 2.
    ...    9. Wait for a replica to be auto balanced to node 2.
    ...    10. Verify replicas are stable: one in zone-a and one in zone-b for a sufficient time.

    # Step 1: Set up zones
    Given Set k8s node 0 zone zone-a
    And Set k8s node 1 zone zone-a
    And Set k8s node 2 zone zone-b

    # Step 2: Create unstable node condition on node 2
    And Stop kubelet on node 2 for 2100 seconds
    And Wait for node 2 ready

    # Step 3: Verify lastTransitionTime of node 2 is 30 minutes later than node 0 and node 1
    ${node2_ts}=    Run command
    ...    kubectl get node ${NODE_2} -o jsonpath='{.status.conditions[?(@.type=="Ready")].lastTransitionTime}' | xargs -I{} date -d "{}" +%s
    ${node0_ts}=    Run command
    ...    kubectl get node ${NODE_0} -o jsonpath='{.status.conditions[?(@.type=="Ready")].lastTransitionTime}' | xargs -I{} date -d "{}" +%s
    ${node1_ts}=    Run command
    ...    kubectl get node ${NODE_1} -o jsonpath='{.status.conditions[?(@.type=="Ready")].lastTransitionTime}' | xargs -I{} date -d "{}" +%s
    Run command and expect output
    ...    echo $(( ${node2_ts} - ${node0_ts} > 1800 && ${node2_ts} - ${node1_ts} > 1800 ))
    ...    1

    # Step 4: Set Replica Auto Balance to best-effort
    When Setting replica-auto-balance is set to best-effort

    # Step 5: Disable scheduling for node 2
    And Disable node 2 scheduling

    # Step 6: Create and attach a 2-replica volume
    And Create volume 0 with    numberOfReplicas=2    dataEngine=${DATA_ENGINE}
    And Attach volume 0

    # Step 7: Wait for volume attached and healthy
    Then Wait for volume 0 attached
    And Wait for volume 0 healthy

    # Step 8: Enable scheduling for node 2
    When Enable node 2 scheduling

    # Step 9: Wait for a replica to auto balance to node 2
    Then Volume 0 should have running replicas on node 2

    # Step 10: Verify replicas are stable - one in zone-a, one in zone-b
    And Volume 0 should have 1 running replicas on node 2 and no additional scheduling occurs
    And Volume 0 should have 2 replicas and no additional scheduling occurs

Test Least Effort Auto Balance In Unstable Cluster
    [Documentation]    Test replica least effort auto balance with unstable node
    [Tags]    kubelet-restart    long-running
    ...    Issue: https://github.com/longhorn/longhorn/issues/11730
    ...
    ...    1. Set Replica Auto Balance to least-effort.
    ...    2. Disable node 2 scheduling. Create and attach a 2-replica volume.
    ...       Replicas go to node 0 and node 1. Re-enable node 2 scheduling.
    ...    3. Stop kubelet on node 1 (a replica node) for 35 mins so its Ready
    ...       condition lastTransitionTime is >30 min later than other nodes.
    ...    4. Verify the lastTransitionTime gap between node 1 and other nodes is >30 min.
    ...    5. Wait for the replica rebuilding to complete.
    ...    6. The volume should have 2 running replicas on node 0 and node 2. There should be no running replica on node 1.
    # Step 1: Set Replica Auto Balance to least-effort
    # Step 2: Create and attach a 2-replica volume with replicas on node 0 and node 1
    And Disable node 2 scheduling
    And Create volume 0 with    numberOfReplicas=2    replicaAutoBalance=least-effort    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 attached
    And Wait for volume 0 healthy
    And Enable node 2 scheduling

    # Step 3: Stop kubelet on node 1 for 35 minutes
    And Stop kubelet on node 1 for 2100 seconds
    And Wait for node 1 ready

    # Step 4: Verify lastTransitionTime gap between node 1 and other nodes is >30 min
    ${node1_ts}=    Run command
    ...    kubectl get node ${NODE_1} -o jsonpath='{.status.conditions[?(@.type=="Ready")].lastTransitionTime}' | xargs -I{} date -d "{}" +%s
    ${node0_ts}=    Run command
    ...    kubectl get node ${NODE_0} -o jsonpath='{.status.conditions[?(@.type=="Ready")].lastTransitionTime}' | xargs -I{} date -d "{}" +%s
    ${node2_ts}=    Run command
    ...    kubectl get node ${NODE_2} -o jsonpath='{.status.conditions[?(@.type=="Ready")].lastTransitionTime}' | xargs -I{} date -d "{}" +%s
    Run command and expect output
    ...    echo $(( ${node1_ts} - ${node0_ts} > 1800 && ${node1_ts} - ${node2_ts} > 1800 ))
    ...    1

    # Step 5: Wait for the replica rebuilding to complete
    Then Wait until volume 0 replicas rebuilding completed
    And Wait for volume 0 healthy

    # Step 6: The volume should have 2 running replicas on node 0 and node 2, and no running replica on node 1
    And Volume 0 should have 2 running replicas and no additional scheduling occurs
    And Volume 0 should have 1 running replicas on node 0
    And Volume 0 should have 0 running replicas on node 1
    And Volume 0 should have 1 running replicas on node 2

Test Volume Expansion After Iscsid Restart
    [Tags]    expansion
    [Documentation]    Verify that volumes can still be expanded correctly after iscsid
    ...                is restarted on all worker nodes.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/10544
    ...
    ...                Steps:
    ...                1. Create a RWO and a RWX deployment, each with a 1GiB volume.
    ...                2. Write data to both deployments.
    ...                3. Restart iscsid on every worker node.
    ...                4. Expand the RWO deployment volume to 2GiB.
    ...                5. Wait for the RWO volume size to be expanded.
    ...                6. Assert the filesystem size in the RWO deployment is 2GiB.
    ...                7. Check RWO data integrity.
    ...                8. Expand the RWX deployment volume to 2GiB.
    ...                9. Wait for the RWX volume size to be expanded.
    ...                10. Assert the filesystem size in the RWX deployment is 2GiB.
    ...                11. Assert the disk size in the sharemanager pod is 2GiB.
    ...                12. Check RWX data integrity.
    IF    '${DATA_ENGINE}' == 'v2'
        Skip    v2 volume doesn't rely on iscsid
    END

    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test    storage_size=1GiB
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-test    storage_size=1GiB
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Write 512 MB data to file data.txt in deployment 0
    And Write 512 MB data to file data.txt in deployment 1

    # Restart iscsid on all worker nodes
    When SSH into node 0 and run command    sudo systemctl restart iscsid
    And SSH into node 1 and run command    sudo systemctl restart iscsid
    And SSH into node 2 and run command    sudo systemctl restart iscsid

    # Expand RWO deployment and verify
    And Expand deployment 0 volume to 2GiB
    Then Wait for deployment 0 volume size expanded
    And Assert filesystem size in deployment 0 is 2GiB
    And Check deployment 0 data in file data.txt is intact

    # Expand RWX deployment and verify
    When Expand deployment 1 volume to 2GiB
    Then Wait for deployment 1 volume size expanded
    And Assert filesystem size in deployment 1 is 2GiB
    And Assert disk size in sharemanager pod for deployment 1 is 2GiB
    And Check deployment 1 data in file data.txt is intact
