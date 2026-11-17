*** Settings ***
Documentation    Volume Anti-Affinity Test Cases
...              Issue: https://github.com/longhorn/longhorn/issues/6771
...
...              Covers the opt-in `volumeAntiAffinity` StorageClass parameter.
...              Longhorn inherits the node-level spreading rules of the pod that
...              uses a volume, and keeps the replicas of related volumes, the
...              volumes of different pods that carry the same rule, on different
...              nodes.

Test Tags    regression    volume-anti-affinity

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/node.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/statefulset.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Create volume anti-affinity storageclass
    Create storageclass longhorn-test with
    ...    dataEngine=${DATA_ENGINE}
    ...    numberOfReplicas=1
    ...    dataLocality=disabled
    ...    volumeBindingMode=WaitForFirstConsumer
    ...    volumeAntiAffinity=enabled

Volume ${volume_name} should have the inherited term ${field}
    Run command and expect output
    ...    kubectl get volumes.longhorn.io -n longhorn-system ${volume_name} -o jsonpath='{.spec.volumeAntiAffinityFromPod.${field}\[*].labelSelector.matchLabels.app}'
    ...    e2e-test-statefulset-0

Evict the disk of node ${node_id}
    IF    "${DATA_ENGINE}" == "v1"
        Disable node ${node_id} default disk
        Request eviction on default disk of node ${node_id}
    ELSE IF    "${DATA_ENGINE}" == "v2"
        Disable disk block-disk scheduling on node ${node_id}
        Request eviction on disk block-disk of node ${node_id}
    END

Evicted replica moves to a free node
    [Arguments]    ${detached}
    Given Disable node 2 scheduling
    And Create volume anti-affinity storageclass
    And Create statefulset 0    volume_type=RWO    sc_name=longhorn-test    spread=required
    And Scale statefulset 0 to 2
    And Wait for statefulset 0 to have 2 ready replicas
    And Wait for volumes of statefulset 0 to have replicas on 2 different nodes
    And Enable node 2 scheduling
    IF    ${detached}
        And Scale statefulset 0 to 0
        And Wait for volumes of statefulset 0 detached
    END

    When Evict the disk of node 0

    Then Wait for volumes of statefulset 0 to have no replica on node 0
    And Wait for volumes of statefulset 0 to have replicas on 2 different nodes

*** Test Cases ***
Test Volume Anti-Affinity Spreads Volumes With Required Pod Anti-Affinity
    [Documentation]    A statefulset with a required pod anti-affinity rule on
    ...    kubernetes.io/hostname gets volumes that inherit the rule as a
    ...    required term, and the replicas of its volumes are on different
    ...    nodes even though the replicas are not on the pod nodes.
    Given Create volume anti-affinity storageclass
    When Create statefulset 0    volume_type=RWO    sc_name=longhorn-test    spread=required
    And Scale statefulset 0 to 3
    And Wait for statefulset 0 to have 3 ready replicas

    Then Wait for volumes of statefulset 0 to have replicas on 3 different nodes
    FOR    ${ordinal}    IN RANGE    3
        ${volume_name} =    Get volume of statefulset 0 pod ${ordinal}
        Volume ${volume_name} should have the inherited term requiredTerms
        Run command and expect output
        ...    kubectl get volumes.longhorn.io -n longhorn-system ${volume_name} -o jsonpath='{.spec.volumeAntiAffinityFromPod.pod}'
        ...    default/e2e-test-statefulset-0-${ordinal}
    END
    # The volume webhook keeps an enabled volume at one replica.
    And Run command and expect output
    ...    kubectl patch volumes.longhorn.io -n longhorn-system ${volume_name} --type merge -p '{"spec":{"numberOfReplicas":2}}' 2>&1 || true
    ...    replica count should be 1

Test Volume Anti-Affinity Required Term Blocks Placement Without A Free Node
    [Documentation]    With only two nodes schedulable for replicas, the third
    ...    volume of a statefulset with a required rule is not placed. Its
    ...    Scheduled condition names volume anti-affinity, and setting
    ...    spec.volumeAntiAffinity to disabled on that volume places it.
    Given Disable node 2 scheduling
    And Create volume anti-affinity storageclass
    When Create statefulset 0    volume_type=RWO    sc_name=longhorn-test    spread=required
    And Scale statefulset 0 to 3
    And Wait for statefulset 0 to have 2 ready replicas
    ${volume_name} =    Get volume of statefulset 0 pod 2

    Then Run command and wait for output
    ...    kubectl get volumes.longhorn.io -n longhorn-system ${volume_name} -o jsonpath='{.status.conditions[?(@.type=="Scheduled")].message}'
    ...    volume anti-affinity cannot be satisfied
    And Run command and expect output
    ...    kubectl get volumes.longhorn.io -n longhorn-system ${volume_name} -o jsonpath='{.status.conditions[?(@.type=="Scheduled")].status}'
    ...    False

    When Run command
    ...    kubectl patch volumes.longhorn.io -n longhorn-system ${volume_name} --type merge -p '{"spec":{"volumeAntiAffinity":"disabled"}}'
    Then Wait for statefulset 0 to have 3 ready replicas

Test Volume Anti-Affinity Preferred Term Never Blocks Placement
    [Documentation]    A topology spread constraint is inherited as a preferred
    ...    term. With only two nodes schedulable for replicas, the three
    ...    volumes are still placed, and they use both nodes.
    Given Disable node 2 scheduling
    And Create volume anti-affinity storageclass
    When Create statefulset 0    volume_type=RWO    sc_name=longhorn-test    spread=topology-spread
    And Scale statefulset 0 to 3

    Then Wait for statefulset 0 to have 3 ready replicas
    And Wait for volumes of statefulset 0 to have replicas on 2 different nodes
    ${volume_name} =    Get volume of statefulset 0 pod 0
    And Volume ${volume_name} should have the inherited term preferredTerms

Test Volume Anti-Affinity Reports Rules That Are Not Inherited
    [Documentation]    A zone rule is not inherited without the volumeTopology
    ...    parameter. The volume records a VolumeAntiAffinityNotInherited
    ...    event that names the rule, and carries no inherited terms.
    Given Create volume anti-affinity storageclass
    When Create statefulset 0    volume_type=RWO    sc_name=longhorn-test    spread=zone
    ${volume_name} =    Get volume of statefulset 0 pod 0

    Then Run command and wait for output
    ...    kubectl get events -n longhorn-system --field-selector involvedObject.name=${volume_name},reason=VolumeAntiAffinityNotInherited -o jsonpath='{.items[*].message}'
    ...    zone rules are not inherited
    And Run command and not expect output
    ...    kubectl get volumes.longhorn.io -n longhorn-system ${volume_name} -o jsonpath='{.spec.volumeAntiAffinityFromPod}'
    ...    Terms

Test Volume Anti-Affinity StorageClass Validation
    [Documentation]    A StorageClass with volumeAntiAffinity enabled must bind
    ...    volumes when their pod is scheduled, must set one replica, and
    ...    cannot use the EC data layout.
    Run Keyword And Expect Error    *WaitForFirstConsumer*
    ...    Create storageclass longhorn-test with    numberOfReplicas=1    volumeAntiAffinity=enabled
    Run Keyword And Expect Error    *numberOfReplicas*
    ...    Create storageclass longhorn-test with    volumeBindingMode=WaitForFirstConsumer    volumeAntiAffinity=enabled
    Run Keyword And Expect Error    *volumeAntiAffinity*
    ...    Create storageclass longhorn-test with    numberOfReplicas=1    volumeBindingMode=WaitForFirstConsumer    volumeAntiAffinity=required
    ${dataLayout} =    Create Dictionary    type=sharded
    Run Keyword And Expect Error    *dataLayout.type sharded*
    ...    Create storageclass longhorn-test with    numberOfReplicas=1    volumeBindingMode=WaitForFirstConsumer    volumeAntiAffinity=enabled    dataLayout=${dataLayout}

Test Volume Anti-Affinity Blocks Eviction Of A Detached Volume
    [Documentation]    The replicas of three related volumes occupy all three
    ...    nodes. When the volumes are detached and the disk of one node is
    ...    evicted, the volume on that node has no node left. The eviction
    ...    controller does not attach it and records a ReplicaEvictionBlocked
    ...    event that names volume anti-affinity. Setting
    ...    spec.volumeAntiAffinity to disabled on the volume lets the eviction
    ...    finish.
    Given Create volume anti-affinity storageclass
    And Create statefulset 0    volume_type=RWO    sc_name=longhorn-test    spread=required
    And Scale statefulset 0 to 3
    And Wait for statefulset 0 to have 3 ready replicas
    And Wait for volumes of statefulset 0 to have replicas on 3 different nodes
    ${volume_name} =    Get volume of statefulset 0 on node 0

    When Scale statefulset 0 to 0
    And Wait for volumes of statefulset 0 detached
    And Evict the disk of node 0

    Then Run command and wait for output
    ...    kubectl get events -n longhorn-system --field-selector involvedObject.name=${volume_name},reason=ReplicaEvictionBlocked -o jsonpath='{.items[*].message}'
    ...    volume anti-affinity cannot be satisfied

    When Run command
    ...    kubectl patch volumes.longhorn.io -n longhorn-system ${volume_name} --type merge -p '{"spec":{"volumeAntiAffinity":"disabled"}}'
    Then Wait for volumes of statefulset 0 to have no replica on node 0

Test Volume Anti-Affinity Blocks Eviction Of An Attached Volume
    [Documentation]    The replicas of three related volumes occupy all three
    ...    nodes. When the disk of one node is evicted while the pods run, the
    ...    volume on that node has no node left. Its Scheduled condition names
    ...    volume anti-affinity, and setting spec.volumeAntiAffinity to disabled
    ...    on the volume lets the eviction finish.
    Given Create volume anti-affinity storageclass
    And Create statefulset 0    volume_type=RWO    sc_name=longhorn-test    spread=required
    And Scale statefulset 0 to 3
    And Wait for statefulset 0 to have 3 ready replicas
    And Wait for volumes of statefulset 0 to have replicas on 3 different nodes
    ${volume_name} =    Get volume of statefulset 0 on node 0

    When Evict the disk of node 0

    Then Run command and wait for output
    ...    kubectl get volumes.longhorn.io -n longhorn-system ${volume_name} -o jsonpath='{.status.conditions[?(@.type=="Scheduled")].message}'
    ...    volume anti-affinity cannot be satisfied

    When Run command
    ...    kubectl patch volumes.longhorn.io -n longhorn-system ${volume_name} --type merge -p '{"spec":{"volumeAntiAffinity":"disabled"}}'
    Then Wait for volumes of statefulset 0 to have no replica on node 0

Test Volume Anti-Affinity Moves An Evicted Replica Of An Attached Volume To A Free Node
    [Documentation]    Two related volumes are on node 0 and node 1, and node 2
    ...    holds no related replica. When the disk of node 0 is evicted while
    ...    the pods run, the replica moves to node 2, not to node 1.
    Evicted replica moves to a free node    ${False}

Test Volume Anti-Affinity Moves An Evicted Replica Of A Detached Volume To A Free Node
    [Documentation]    Two related volumes are on node 0 and node 1, and node 2
    ...    holds no related replica. When the volumes are detached and the disk
    ...    of node 0 is evicted, the replica moves to node 2, not to node 1.
    Evicted replica moves to a free node    ${True}

Test Volume Anti-Affinity Applies To An Existing Volume That Opts In
    [Documentation]    A volume created without the volumeAntiAffinity
    ...    parameter gets the terms of its pod once spec.volumeAntiAffinity is
    ...    set to enabled on it and the pod or the PV changes.
    Given Create storageclass longhorn-test with
    ...    dataEngine=${DATA_ENGINE}
    ...    numberOfReplicas=1
    ...    dataLocality=disabled
    ...    volumeBindingMode=WaitForFirstConsumer
    And Create statefulset 0    volume_type=RWO    sc_name=longhorn-test    spread=required
    ${volume_name} =    Get volume of statefulset 0 pod 0
    And Run command and not expect output
    ...    kubectl get volumes.longhorn.io -n longhorn-system ${volume_name} -o jsonpath='{.spec.volumeAntiAffinityFromPod}'
    ...    Terms

    When Run command
    ...    kubectl patch volumes.longhorn.io -n longhorn-system ${volume_name} --type merge -p '{"spec":{"volumeAntiAffinity":"enabled"}}'
    And Run command
    ...    kubectl annotate pod -n default e2e-test-statefulset-0-0 test.longhorn.io/volume-anti-affinity=sync --overwrite

    Then Run command and wait for output
    ...    kubectl get volumes.longhorn.io -n longhorn-system ${volume_name} -o jsonpath='{.spec.volumeAntiAffinityFromPod.requiredTerms\[*].labelSelector.matchLabels.app}'
    ...    e2e-test-statefulset-0
