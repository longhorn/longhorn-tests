*** Settings ***
Documentation    Scheduling Test Cases

Test Tags    regression    replica    scheduling

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/replica.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/node.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/engine_image.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Soft Anti Affinity Scheduling
    [Tags]    coretest
    [Documentation]    Test that volumes with Soft Anti-Affinity work as expected.
    ...
    ...    With Soft Anti-Affinity, a new replica should still be scheduled on a node
    ...    with an existing replica, which will result in "Healthy" state but limited
    ...    redundancy.
    ...
    ...    1. Create a volume and attach to the current node
    ...    2. Generate and write `data` to the volume.
    ...    3. Set `soft anti-affinity` to true
    ...    4. Disable current node's scheduling.
    ...    5. Remove the replica on the current node
    ...    6. Wait for the volume to complete rebuild. Volume should have 3 replicas.
    ...    7. Verify `data`
    Given Create volume 0 with    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    When Setting replica-soft-anti-affinity is set to true
    # disabling scheduling on a node only sets the node status to "Disable", not "Unschedulable"
    # therefore disabling scheduling doesn't alter the node["conditions"]["Schedulable"]["status"] field
    # only cordoning a node can set it to "Unschedulable"
    And Cordon node 1
    And Delete volume 0 replica on node 1

    Then Wait until volume 0 replicas rebuilding completed
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Test Replica Auto Balance Disk In Pressure
    [Tags]    coretest
    [Documentation]    Test replica auto balance disk in pressure
    ...    This test simulates a scenario where a disk reaches a certain
    ...    pressure threshold (80%), triggering the replica auto balance
    ...    to rebuild the replicas to another disk with enough available
    ...    space. Replicas should not be rebuilt at the same time.
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/4105
    ${DISK0}=    Generate random disk name
    ${DISK1}=    Generate random disk name

    Given Setting replica-soft-anti-affinity is set to false
    And Setting replica-auto-balance-disk-pressure-percentage is set to 80

    IF    "${DATA_ENGINE}" == "v1"
        And Create 1 Gi filesystem type disk ${DISK0} on node 0
        And Create 1 Gi filesystem type disk ${DISK1} on node 0
    ELSE IF    "${DATA_ENGINE}" == "v2"
        And Create 1 Gi block type disk ${DISK0} on node 0
        And Create 1 Gi block type disk ${DISK1} on node 0
    END
    And Disable disk ${DISK1} scheduling on node 0
    And Disable disk block-disk scheduling on node 0
    And Disable node 0 default disk
    And Disable node 1 scheduling
    And Disable node 2 scheduling

    And Create storageclass one-replica with    numberOfReplicas=1    dataEngine=${DATA_ENGINE}
    # 1 Gi disk, but only 950 Mi available, 950 Mi / 3 = 316 Mi
    And Create statefulset 0 using RWO volume with one-replica storageclass and size 316 Mi
    And Create statefulset 1 using RWO volume with one-replica storageclass and size 316 Mi
    And Create statefulset 2 using RWO volume with one-replica storageclass and size 316 Mi
    And Check volume of statefulset 0 replica on node 0 disk ${DISK0}
    And Check volume of statefulset 1 replica on node 0 disk ${DISK0}
    And Check volume of statefulset 2 replica on node 0 disk ${DISK0}

    # Write 950 Mi * 80% / 3 = 254 Mi data to disk 0 to make it in pressure
    And Write 254 MB data to file data.bin in statefulset 0
    And Write 254 MB data to file data.bin in statefulset 1
    And Write 254 MB data to file data.bin in statefulset 2
    And Check node 0 disk ${DISK0} is in pressure

    When Enable disk ${DISK1} scheduling on node 0
    And Setting replica-auto-balance is set to best-effort

    # auto balance should happen
    Then Check node 0 disk ${DISK0} is not in pressure
    And Check node 0 disk ${DISK1} is not in pressure
    And There should be running replicas on node 0 disk ${DISK0}
    And There should be running replicas on node 0 disk ${DISK1}

    And Wait for volume of statefulset 0 healthy
    And Wait for volume of statefulset 1 healthy
    And Wait for volume of statefulset 2 healthy
    And Check statefulset 0 data in file data.bin is intact
    And Check statefulset 1 data in file data.bin is intact
    And Check statefulset 2 data in file data.bin is intact

Test Replica Auto Balance Disk In Pressure With Stopped Volume Should Not Block
    [Tags]    auto-balance    single-replica
    [Documentation]    Verify that stopped volumes with alphabetically smaller names
    ...    no not block auto-balancing of running volumes when the disk is under
    ...    pressure.
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/10837
    Given Setting replica-soft-anti-affinity is set to false

    ${DISK0}=    Generate random disk name
    ${DISK1}=    Generate random disk name
    IF    "${DATA_ENGINE}" == "v1"
        And Create 1 Gi filesystem type disk ${DISK0} on node 0
        And Create 1 Gi filesystem type disk ${DISK1} on node 0
    ELSE IF    "${DATA_ENGINE}" == "v2"
        And Create 1 Gi block type disk ${DISK0} on node 0
        And Create 1 Gi block type disk ${DISK1} on node 0
    END
    And Disable disk ${DISK1} scheduling on node 0
    And Disable disk block-disk scheduling on node 0
    And Disable node 0 default disk
    And Disable node 1 scheduling
    And Disable node 2 scheduling

    # Disable auto balance disk pressure initially
    And Setting replica-auto-balance-disk-pressure-percentage is set to 0

    # Create two volumes with single replica on disk 0
    And Create volume aaa with    size=450Mi    numberOfReplicas=1    dataEngine=${DATA_ENGINE}
    And Attach volume aaa to node 0
    And Wait for volume aaa healthy
    And Create volume bbb with    size=450Mi    numberOfReplicas=1    dataEngine=${DATA_ENGINE}
    And Attach volume bbb to node 0
    And Wait for volume bbb healthy

    # Write data to trigger disk pressure
    And Write 400 Mi data to volume aaa
    And Write 400 Mi data to volume bbb

    # Stop the alphabetically first volume (aaa)
    When Detach volume aaa from attached node
    And Wait for volume aaa detached

    # Enable auto-balance under disk pressure
    And Setting replica-auto-balance-disk-pressure-percentage is set to 70
    And Enable disk ${DISK1} scheduling on node 0
    And Setting replica-auto-balance is set to best-effort

    # The running replica (bbb) should be auto-balanced to disk 1,
    # ignoring the stopped volume (aaa).
    Then Check node 0 disk ${DISK1} is not in pressure
    And There should be 1 replicas of volume aaa on node 0 disk ${DISK0}
    And There should be 1 replicas of volume bbb on node 0 disk ${DISK1}

    And Wait for volume bbb healthy
    And Check volume bbb data is intact

Test Replica Auto Balance Node Least Effort
    [Tags]    coretest
    [Documentation]    Scenario: replica auto-balance nodes with `least_effort`
    Given Setting replica-soft-anti-affinity is set to true
    And Setting replica-auto-balance is set to least-effort

    When Disable node 1 scheduling
    And Disable node 2 scheduling
    And Create volume 0 with    numberOfReplicas=6    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    Then Volume 0 should have 6 running replicas on node 0
    And Volume 0 should have 0 running replicas on node 1
    And Volume 0 should have 0 running replicas on node 2

    When Enable node 1 scheduling
    # wait for auto balance
    Then Volume 0 should have running replicas on node 1
    And Volume 0 should have 6 running replicas
    # loop 3 times with 5-second wait and compare the replica count to:
    # ensure no additional scheduling occurs
    # the replica count remains unchanged
    And Volume 0 should have running replicas on node 0 and no additional scheduling occurs
    And Volume 0 should have running replicas on node 1 and no additional scheduling occurs
    # 1 or 2 replicas, but not 3 replicas, on node 0 could be reschduled to node 1
    # replica count on each node could be:
    # 5, 1, 0
    # or
    # 4, 2, 0
    # but not
    # 3, 3, 0
    And Number of volume 0 replicas on node 1 should be less than on node 0
    And Volume 0 should have 0 running replicas on node 2 and no additional scheduling occurs

    When Enable node 2 scheduling
    # wait for auto balance
    Then Volume 0 should have running replicas on node 2
    And Volume 0 should have 6 running replicas
    # loop 3 times with 5-second wait and compare the replica count to:
    # ensure no additional scheduling occurs
    # the replica count remains unchanged
    And Volume 0 should have running replicas on node 0 and no additional scheduling occurs
    And Volume 0 should have running replicas on node 1 and no additional scheduling occurs
    And Volume 0 should have running replicas on node 2 and no additional scheduling occurs
    # replicas on node 0 will be rescheduled to node 2
    # replica counts on each node could be:
    # 4, 1, 1
    # 3, 2, 1
    # so replica count of node 0 should still be greater than that of node 2
    And Number of volume 0 replicas on node 2 should be less than on node 0

    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Test Data Locality
    [Tags]    single-replica
    [Documentation]    Test that Longhorn builds a local replica on the engine node
    Given Create single replica volume 0 with replica on node 0    dataLocality=disabled    dataEngine=${DATA_ENGINE}
    When Attach volume 0 to node 1
    And Write data to volume 0
    Then Volume 0 should have 0 running replicas on node 1

    When Update volume 0 data locality to best-effort
    Then Wait until volume 0 replica rebuilding started on node 1
    And Volume 0 should have 1 running replicas on node 1
    And Volume 0 should have 0 running replicas on node 0

    When Detach volume 0 from node 1
    And Wait for volume 0 detached
    And Attach volume 0 to node 2
    Then Wait until volume 0 replica rebuilding started on node 2
    And Volume 0 should have 1 running replicas on node 2
    And Volume 0 should have 0 running replicas on node 1

Test Replica Deleting Priority With Best-effort Data Locality
    [Documentation]    Test that Longhorn prioritizes deleting replicas on the same node
    Given Set node 0 tags    AVAIL
    And Set node 1 tags    AVAIL

    ${avail_node_selector}=    Create List    AVAIL
    When Create volume 0    numberOfReplicas=3    dataLocality=best-effort    nodeSelector=${avail_node_selector}    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 2
    And Wait for volume 0 degraded
    Then Volume 0 should have running replicas on node 0
    And Volume 0 should have running replicas on node 1
    And Volume 0 should have 0 running replicas on node 2
    And Check volume 0 works

    When Update volume 0 replica count to 2
    And Wait for volume 0 healthy
    # Longhorn will prioritize deleting replicas on the same node to maintain the balance
    # the replica on the node with more replicas than the others will be deleted
    Then Volume 0 should have 1 running replicas on node 0
    And Volume 0 should have 1 running replicas on node 1

Test Unexpected Volume Detachment During Data Locality Maintenance
    [Tags]    single-replica
    [Documentation]    Test that the volume is not corrupted if there is an unexpected
    ...                detachment during building local replica
    Given Setting replica-soft-anti-affinity is set to false

    When Create volume 0    numberOfReplicas=1    dataLocality=best-effort    dataEngine=${DATA_ENGINE}
    Then Attach volume 0 to node 2
    And Wait for volume 0 healthy
    And Volume 0 should have 1 running replicas on node 2
    And Volume 0 should have 0 running replicas on node 1
    And Volume 0 should have 0 running replicas on node 0

    And Write data to volume 0
    And Detach volume 0 from node 2
    And Wait for volume 0 detached
    And Attach volume 0 to node 0

    When Wait until volume 0 replica rebuilding started on node 0
    And Detach volume 0 from node 0
    And Wait for volume 0 detached
    Then Attach volume 0 to node 1
    And Wait for volume 0 healthy
    And Volume 0 should have 0 running replicas on node 0
    And Volume 0 should have 1 running replicas on node 1
    And Volume 0 should have 0 running replicas on node 2
    And Check volume 0 data is intact

Test Data Locality With Failed Scheduled Replica
    [Tags]    single-replica
    [Documentation]    Make sure failed to schedule local replica doesn't block the
    ...                the creation of other replicas.
    Given Disable node 2 scheduling
    And Setting replica-soft-anti-affinity is set to false

    When Create volume 0    numberOfReplicas=1    dataLocality=best-effort    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 2
    And Wait for volume 0 healthy
    Then Volume 0 should have 2 replicas
    And Volume 0 should have 1 running replicas
    And Volume 0 should have stopped replicas
    And Wait for volume 0 condition Scheduled to be false    reason=LocalReplicaSchedulingFailure

    When Update volume 0 replica count to 3
    And Wait for volume 0 degraded
    Then Volume 0 should have 1 running replicas on node 0
    And Volume 0 should have 1 running replicas on node 1
    And Volume 0 should have stopped replicas

    When Update volume 0 replica count to 2
    And Wait for volume 0 healthy
    Then Volume 0 should have 3 replicas
    And Volume 0 should have 1 running replicas on node 0
    And Volume 0 should have 1 running replicas on node 1
    And Volume 0 should have stopped replicas

    When Update volume 0 replica count to 1
    And Wait for volume 0 healthy
    Then Volume 0 should have 2 replicas
    And Volume 0 should have 1 running replicas
    And Volume 0 should have 1 stopped replicas

    When Update volume 0 data locality to disabled
    And Update volume 0 replica count to 2
    Then Volume 0 should have 2 replicas
    And Volume 0 should have 1 running replicas on node 0
    And Volume 0 should have 1 running replicas on node 1
    And Volume 0 should have 0 replicas on node 2

Test No Transient Error In Engine Status During Eviction
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/4294
    ...    1. Create and attach a multi-replica volume.
    ...    2. Prepare one extra disk for a node that contains at least one volume replica.
    ...    3. Evicting the old disk for node. Verify that there is no transient error in
    ...       engine Status during evictionKeep monitoring the engine YAML.
    ...       e.g., watch -n "kubectl -n longhorn-system get lhe <engine name>".
    ${DISK0}=    Generate random disk name

    Given Create volume 0    size=256Mi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 1
    And Wait for volume 0 healthy

    IF    "${DATA_ENGINE}" == "v1"
        When Create 1 Gi filesystem type disk ${DISK0} on node 0
        And Disable node 0 default disk
        And Request eviction on default disk of node 0
        Then There should be 1 replicas of volume 0 on node 0 disk ${DISK0}
        And There should be no replica of volume 0 on node 0 disk default
    ELSE IF    "${DATA_ENGINE}" == "v2"
        When Create 1 Gi block type disk ${DISK0} on node 0
        And Disable disk block-disk scheduling on node 0
        And Request eviction on disk block-disk of node 0
        Then There should be 1 replicas of volume 0 on node 0 disk ${DISK0}
        And There should be no replica of volume 0 on node 0 disk block-disk
    END

    And Wait for volume 0 healthy
    And Run command and not expect output
    ...    kubectl get lhe -n longhorn-system -oyaml
    ...    TransientFailure

Test Storageclass Allowed Topologies With Empty Csi Allowed Topology Keys
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12261
    ...                       https://github.com/longhorn/longhorn/issues/12684
    ...    1. Set csi-allowed-topology-keys to empty
    ...    2. Create storage class with allowedTopologies:
    ...    allowedTopologies:
    ...    - matchLabelExpressions:
    ...      - key: kubernetes.io/hostname
    ...        values:
    ...          - <node-name>
    ...    3. Create a workload with the storage class
    ...    4. Because csi-allowed-topology-keys is empty, allowedTopologies won't take effect,
    ...       the created PV won't have the expected nodeAffinity:
    ...    nodeAffinity:
    ...      required:
    ...        nodeSelectorTerms:
    ...        - matchExpressions:
    ...          - key: kubernetes.io/hostname
    ...            operator: In
    ...            values:
    ...            - <node-name>
    Given Setting csi-allowed-topology-keys is set to ${EMPTY}
    And Rollout restart daemonset longhorn-csi-plugin in namespace longhorn-system
    When Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    allowedTopologies={"kubernetes.io/hostname":"${NODE_2}"}
    And Create persistentvolumeclaim 0    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    Then Run command and not expect output
    ...    kubectl get pv -ojsonpath='{.items[0].spec.nodeAffinity.required.nodeSelectorTerms[*].matchExpressions[*].values[*]}'
    ...    ${NODE_2}

Test Storageclass Allowed Topologies With Csi Allowed Topology Keys
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12261
    ...                       https://github.com/longhorn/longhorn/issues/12684
    ...    1. Set csi-allowed-topology-keys to kubernetes.io/hostname
    ...    2. Create storage class with allowedTopologies:
    ...    allowedTopologies:
    ...    - matchLabelExpressions:
    ...      - key: kubernetes.io/hostname
    ...        values:
    ...          - <node-name>
    ...    3. Create a workload with the storage class
    ...    4. Because csi-allowed-topology-keys matches allowedTopologies,
    ...       the created PV has the expected nodeAffinity:
    ...    nodeAffinity:
    ...      required:
    ...        nodeSelectorTerms:
    ...        - matchExpressions:
    ...          - key: kubernetes.io/hostname
    ...            operator: In
    ...            values:
    ...            - <node-name>
    Given Setting csi-allowed-topology-keys is set to kubernetes.io/hostname
    And Rollout restart daemonset longhorn-csi-plugin in namespace longhorn-system
    When Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    allowedTopologies={"kubernetes.io/hostname":"${NODE_2}"}
    And Create persistentvolumeclaim 0    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    Then Run command and expect output
    ...    kubectl get pv -ojsonpath='{.items[0].spec.nodeAffinity.required.nodeSelectorTerms[*].matchExpressions[*].values[*]}'
    ...    ${NODE_2}
    And Run command and expect output
    ...    kubectl get volumes -n longhorn-system -ojsonpath='{.items[0].spec.nodeID}'
    ...    ${NODE_2}

Test Scheduling Replicas To Different Disks On The Same Node
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12653
    ...    1. Enable replica-soft-anti-affinity
    ...    2. Disable replica-disk-soft-anti-affinity
    ...    3. Create a single-node cluster where a single node has 2 separate disks with the same size (e.g., 1GiB Disk A and Disk B)
    ...    4. Create a 900MiB volume with 2 replicas. The scheduler attempts to place Replica-1 on Disk A and Replica-2 on Disk B (same Node)
    ...    5. Replica-1 is scheduled successfully on Disk A, and Replica-2 is scheduled successfully on Disk B, the scheduler doesn't throw an insufficient storage error
    Given Setting replica-soft-anti-affinity is set to true
    And Setting replica-disk-soft-anti-affinity is set to false

    ${suffix_0}=    Generate Random String    4    [LOWER][NUMBERS]
    ${suffix_1}=    Generate Random String    4    [LOWER][NUMBERS]
    IF    "${DATA_ENGINE}" == "v1"
        And Create 1 Gi filesystem type disk local-disk-${suffix_0} on node 0
        And Create 1 Gi filesystem type disk local-disk-${suffix_1} on node 0
    ELSE IF    "${DATA_ENGINE}" == "v2"
        And Create 1 Gi block type disk local-disk-${suffix_0} on node 0
        And Create 1 Gi block type disk local-disk-${suffix_1} on node 0
    END
    And Disable disk block-disk scheduling on node 0
    And Disable node 0 default disk
    And Disable node 1 scheduling
    And Disable node 2 scheduling

    When Create storageclass two-replicas with    numberOfReplicas=2    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using RWO volume with two-replicas storageclass and size 900 Mi
    Then Wait for volume of statefulset 0 healthy
    And Check volume of statefulset 0 replica on node 0 disk local-disk-${suffix_0}
    And Check volume of statefulset 0 replica on node 0 disk local-disk-${suffix_1}
    And Write 500 MB data to file data.bin in statefulset 0
    And Check statefulset 0 data in file data.bin is intact

Test Longhorn UI Topology Spread Constraints Passthrough And Enforcement
    [Tags]    setting    uninstall    helm
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/13731
    ...
    ...                Verify that longhornUI.topologySpreadConstraints is rendered
    ...                verbatim into the longhorn-ui Deployment pod spec, and that the
    ...                constraint is actually enforced by the scheduler when
    ...                whenUnsatisfiable is DoNotSchedule and eligible topology domains
    ...                are fewer than the replica count.
    ...
    ...                This test case is only applicable for helm installation method.
    ...
    ...                Manual test steps:
    ...                1. Upgrade with
    ...                   --set-json 'longhornUI.topologySpreadConstraints=[{"maxSkew":1,
    ...                   "topologyKey":"kubernetes.io/hostname","whenUnsatisfiable":"ScheduleAnyway",
    ...                   "labelSelector":{"matchLabels":{"app":"longhorn-ui"}}}]'
    ...                2. kubectl -n longhorn-system get deploy longhorn-ui
    ...                   -o jsonpath='{.spec.template.spec.topologySpreadConstraints}'
    ...                3. Expected: the constraint appears verbatim on the pod spec, and
    ...                   both longhorn-ui replicas are Running.
    ...                4. Repeat with whenUnsatisfiable: DoNotSchedule, using a
    ...                   topologyKey whose label value exists on only one node
    ...                   (e.g. a unique label applied to a single node), so the
    ...                   eligible topology domains are fewer than the replica
    ...                   count and the restriction is attributed to
    ...                   topologySpreadConstraints, not node accessibility.
    ...                5. kubectl -n longhorn-system get pods -l app=longhorn-ui
    ...                   kubectl -n longhorn-system describe pod <pending-ui-pod> | tail -20
    ...                6. Expected: one replica is Running, the second replica stays
    ...                   Pending, with a scheduling event citing "didn't satisfy
    ...                   topology spread constraints".
    ${LONGHORN_INSTALL_METHOD} =    Get Environment Variable    LONGHORN_INSTALL_METHOD    default=manifest
    IF    '${LONGHORN_INSTALL_METHOD}' != 'helm'
        Skip    Test case only applicable for helm installation method
    END

    Given Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check all Longhorn CRD removed

    When Install Longhorn
    ...    custom_cmd=yq -i '.longhornUI.topologySpreadConstraints = [{"maxSkew":1,"topologyKey":"kubernetes.io/hostname","whenUnsatisfiable":"ScheduleAnyway","labelSelector":{"matchLabels":{"app":"longhorn-ui"}}}]' values.yaml

    Then Run command and expect output
    ...    kubectl get deploy longhorn-ui -n ${LONGHORN_NAMESPACE} -ojsonpath='{.spec.template.spec.topologySpreadConstraints[*].whenUnsatisfiable}'
    ...    ScheduleAnyway
    And Run command and wait for output
    ...    kubectl get pods -n ${LONGHORN_NAMESPACE} -l app=longhorn-ui --field-selector=status.phase=Running --no-headers | wc -l
    ...    2

    # cordon all but one node so only a single topology domain (kubernetes.io/hostname)
    # is schedulable, which cannot host 2 replicas under maxSkew=1, forcing the
    # 2nd replica to stay Pending
    When Cordon node 1
    And Cordon node 2
    And Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check all Longhorn CRD removed

    And Install Longhorn
    ...    custom_cmd=yq -i '.longhornUI.topologySpreadConstraints = [{"maxSkew":1,"topologyKey":"kubernetes.io/hostname","whenUnsatisfiable":"DoNotSchedule","labelSelector":{"matchLabels":{"app":"longhorn-ui"}}}]' values.yaml

    Then Run command and expect output
    ...    kubectl get deploy longhorn-ui -n ${LONGHORN_NAMESPACE} -ojsonpath='{.spec.template.spec.topologySpreadConstraints[*].whenUnsatisfiable}'
    ...    DoNotSchedule
    And Run command and wait for output
    ...    kubectl get pods -n ${LONGHORN_NAMESPACE} -l app=longhorn-ui --field-selector=status.phase=Running --no-headers | wc -l
    ...    1
    And Run command and wait for output
    ...    kubectl get pods -n ${LONGHORN_NAMESPACE} -l app=longhorn-ui --field-selector=status.phase=Pending --no-headers | wc -l
    ...    1
    And Run command and expect output
    ...    kubectl get events -n ${LONGHORN_NAMESPACE} --field-selector involvedObject.kind=Pod --sort-by='.lastTimestamp'
    ...    didn't match pod topology spread constraints

    And Uncordon node 1
    And Uncordon node 2

    And Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check all Longhorn CRD removed
    And Install Longhorn
    And Wait for longhorn ready

Test System Managed Components Node Selector
    [Tags]    uninstall
    [Documentation]    Test that setting `system-managed-components-node-selector` restricts
    ...    Longhorn system managed components (CSI components, instance managers, engine images)
    ...    to run only on the selected node(s).
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/12834
    ...
    ...    1. Uninstall Longhorn
    ...    2. Reinstall Longhorn with setting `system-managed-components-node-selector` set to
    ...       kubernetes.io/hostname:<node-0> via custom defaultSettings at install time
    ...       (helm: defaultSettings.systemManagedComponentsNodeSelector,
    ...       manifest: system-managed-components-node-selector in default-setting.yaml)
    ...    3. Wait for all CSI component pods (csi-attacher, csi-provisioner, csi-resizer,
    ...       csi-snapshotter) only run on node 0
    ...    4. Enable v2 data engine and wait for v1 and v2 instance manager pods only run on node 0
    ...    5. Wait for engine image pod only run on node 0
    ...    6. Set `system-managed-components-node-selector` to kubernetes.io/hostname:<node-1>
    ...    7. Wait for all CSI component pods, v1 and v2 instance manager pods, and engine image
    ...       pods only run on node 1
    ...    8. Create and attach a v1 and a v2 volume, write and read data to check data integrity
    ...    9. Uninstall and reinstall Longhorn with default settings to restore the test
    ...       environment to the default one
    Given Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check all Longhorn CRD removed

    ${LONGHORN_INSTALL_METHOD} =    Get Environment Variable    LONGHORN_INSTALL_METHOD    default=manifest
    IF    '${LONGHORN_INSTALL_METHOD}' == 'helm'
        Install Longhorn
        ...    custom_cmd=yq -i '.defaultSettings.systemManagedComponentsNodeSelector = "kubernetes.io/hostname:${NODE_0}"' values.yaml
    ELSE
        ${manifest_cmd} =    Set Variable
        ...    sed -i "/default-setting\\.yaml: |-/a\\${SPACE * 4}system-managed-components-node-selector: kubernetes.io/hostname:${NODE_0}" longhorn.yaml
        Install Longhorn    custom_cmd=${manifest_cmd}
    END
    And Enable v2 data engine and add block disks    wait=${False}

    FOR    ${app}    IN    csi-attacher    csi-provisioner    csi-resizer    csi-snapshotter
        Run command and wait for output
        ...    kubectl get pods -n longhorn-system -l app=${app} -o jsonpath='{.items[*].spec.nodeName}'
        ...    ${NODE_0}
        Run command until output is absent
        ...    kubectl get pods -n longhorn-system -l app=${app} -o jsonpath='{.items[*].spec.nodeName}'
        ...    ${NODE_1}
        Run command until output is absent
        ...    kubectl get pods -n longhorn-system -l app=${app} -o jsonpath='{.items[*].spec.nodeName}'
        ...    ${NODE_2}
    END

    When Check v1 instance manager is running on node 0
    Then Check v1 instance manager is not running on node 1
    And Check v1 instance manager is not running on node 2
    And Check v2 instance manager is running on node 0
    And Check v2 instance manager is not running on node 1
    And Check v2 instance manager is not running on node 2
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l longhorn.io/component=engine-image -o jsonpath='{.items[*].spec.nodeName}'
    ...    ${NODE_0}
    And Run command until output is absent
    ...    kubectl get pods -n longhorn-system -l longhorn.io/component=engine-image -o jsonpath='{.items[*].spec.nodeName}'
    ...    ${NODE_1}
    And Run command until output is absent
    ...    kubectl get pods -n longhorn-system -l longhorn.io/component=engine-image -o jsonpath='{.items[*].spec.nodeName}'
    ...    ${NODE_2}

    When Setting system-managed-components-node-selector is set to kubernetes.io/hostname:${NODE_1}
    FOR    ${app}    IN    csi-attacher    csi-provisioner    csi-resizer    csi-snapshotter
        Run command and wait for output
        ...    kubectl get pods -n longhorn-system -l app=${app} -o jsonpath='{.items[*].spec.nodeName}'
        ...    ${NODE_1}
        Run command until output is absent
        ...    kubectl get pods -n longhorn-system -l app=${app} -o jsonpath='{.items[*].spec.nodeName}'
        ...    ${NODE_0}
        Run command until output is absent
        ...    kubectl get pods -n longhorn-system -l app=${app} -o jsonpath='{.items[*].spec.nodeName}'
        ...    ${NODE_2}
    END
    And Check v1 instance manager is running on node 1
    And Check v1 instance manager is not running on node 0
    And Check v1 instance manager is not running on node 2
    And Check v2 instance manager is running on node 1
    And Check v2 instance manager is not running on node 0
    And Check v2 instance manager is not running on node 2
    And Run command and wait for output
    ...    kubectl get pods -n longhorn-system -l longhorn.io/component=engine-image -o jsonpath='{.items[*].spec.nodeName}'
    ...    ${NODE_1}
    And Run command until output is absent
    ...    kubectl get pods -n longhorn-system -l longhorn.io/component=engine-image -o jsonpath='{.items[*].spec.nodeName}'
    ...    ${NODE_0}
    And Run command until output is absent
    ...    kubectl get pods -n longhorn-system -l longhorn.io/component=engine-image -o jsonpath='{.items[*].spec.nodeName}'
    ...    ${NODE_2}

    When Create volume 0 with    numberOfReplicas=1    dataEngine=v1
    And Attach volume 0 to node 1
    And Wait for volume 0 healthy
    And Write data to volume 0
    Then Check volume 0 data is intact

    When Create volume 1 with    numberOfReplicas=1    dataEngine=v2
    And Attach volume 1 to node 1
    And Wait for volume 1 healthy
    And Write data to volume 1
    Then Check volume 1 data is intact

    # Restore the test environment to the default state
    Given Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check all Longhorn CRD removed
    And Install Longhorn
