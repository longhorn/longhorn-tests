*** Settings ***
Documentation     Test the Longhorn resillence if cluster node powering off

Resource          ../../keywords/common.resource
Resource          ../../keywords/engine.resource
Resource          ../../keywords/replica.resource
Resource          ../../keywords/node.resource
Resource          ../../keywords/volume.resource

Suite Setup    set_test_suite_environment

Test setup    set_test_environment    ${TEST NAME}

Test Teardown    cleanup_resources

*** Variable ***
${volume_size_gb}=    1
${pod_eviction_time_out}=    300

*** Test Cases ***

Node with replica and 3 replica volume attached
    [Documentation]    RWO volume with replica on attached node and powering off the volume attached node
    [Tags]    NodePoweringOff    RWO    3Replicas    AttachReplicaSameNode    AbnormalReplicaNode    AbnormalAttachedNode
    # Recover: After restart the node, volume should be detached and replica is failed-Need manual to do reattached.
    Given A ${volume_size_gb} GB RWO volume with 3 replicas
    And Attach volume to node 1
    And Write data into mount point

    When Power off node 1

    Then Node 1 should have 1 volume replica
    And Node 1 state should be NotReady
    And Volume state should be unknown
    And Engine state should be unknown
    And Replica state on node 1 should be unknown

    When Power on node 1

    Then Node 1 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with replica but not 3 replica volume attached
    [Tags]    NodePoweringOff    RWO    3Replicas    AttachReplicaDiffNode    AbnormalReplicaNode    AbnormalNoAttachedNode
    # Recover: After restart the node, delete the stopped replica, and re-update the replica count to do rebuilding
    Given A ${volume_size_gb} GB RWO volume with 3 replicas
    And Attach volume to node 1
    And Write data into mount point

    When Power off node 2

    Then Node 1 should have 1 volume replica
    And Node 2 should have 1 volume replica
    And Node 2 state should be NotReady
    And Volume state should be degraded
    And Engine state should be running
    And Replica state on node 2 should be stopped
    And Data should be intact

    When Power on node 2

    Then Node 2 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with no replica and non-2 replica volume attached and the volume attach on no replica node
    [Documentation]
    [Tags]    NodePoweringOff    RWO    2Replicas    AttachReplicaSameNode    AbnormalNoReplicaNode    AbnormalAttachedNode
    Given A ${volume_size_gb} GB RWO volume with 2 replicas
    And Attach volume to node 3
    And Write data into mount point

    When Power off node 3

    Then Node 3 should have 0 volume replica
    And Node 3 state should be NotReady
    And Volume state should be unknown
    And Engine state should be unknown
    And All replicas state should be running

    When Power on node 3

    Then Node 3 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with replica but non-2 replica volume attached and the volume attach on replica node
    [Documentation]
    [Tags]    NodePoweringOff    RWO    2Replicas    AttachReplicaDiffNode    AbnormalReplicaNode    AbnormalNoAttachedNode
    Given A ${volume_size_gb} GB RWO volume with 2 replicas
    And Attach volume to node 3
    And Write data into mount point

    When Power off node 1

    Then Node 1 should have 1 volume replica
    And Node 3 should have 0 volume replica
    And Node 1 state should be NotReady
    And Volume state should be degraded
    And Engine state should be running
    And Replica state on node 1 should be stopped

    When Power on node 1

    Then Node 1 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with replica and 2 replica volume attached
    [Documentation]
    [Tags]    NodePoweringOff    RWO    2Replicas    AttachReplicaSameNode    AbnormalReplicaNode    AbnormalAttachedNode
    Given A ${volume_size_gb} GB RWO volume with 2 replicas
    And Attach volume to node 1
    And Write data into mount point

    When Power off node 1

    Then Node 1 should have 1 volume replica
    And Node 1 state should be NotReady
    And Volume state should be unknown
    And Engine state should be unknown
    And Replica state on node 1 should be unknown

    When Power on node 1

    Then Node 1 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with no replica and non-2 replica volume attached and the volume attach on replica node
    [Documentation]
    [Tags]    NodePoweringOff    RWO    2Replicas    AttachReplicaDiffNode    AbnormalNoReplicaNode    AbnormalNoAttachedNode
    Given A ${volume_size_gb} GB RWO volume with 2 replicas
    And Attach volume to node 1
    And Write data into mount point

    When Power off node 3

    Then Node 1 should have 1 volume replica
    And Node 3 should have 0 volume replica
    And Node 3 state should be NotReady
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running

    When Power on node 3

    Then Node 3 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with replica but non-2 replica volume attached and the volume attach on no replica node
    [Documentation]
    [Tags]    NodePoweringOff    RWO    2Replicas    AttachReplicaDiffNode    AbnormalReplicaNode    AbnormalNoAttachedNode
    Given A ${volume_size_gb} GB RWO volume with 2 replicas
    And Attach volume to node 1
    And Write data into mount point

    When Power off node 2

    Then Node 1 should have 1 volume replica
    And Node 2 should have 1 volume replica
    And Node 2 state should be NotReady
    And Volume state should be healthy
    And Engine state should be running
    And Replica state on node 1 should be running
    And Replica state on node 2 should be stopped
    And Data should be intact

    When Power on node 2

    Then Node 2 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And Replica state on node 1 should be running
    And Replica state on node 2 should be stopped
    And Data should be intact
    [Teardown]    Teardown

Node with replica and 3 replica volume attached timeout
    [Documentation]    RWO volume with replica on attached node and powering off the volume attached node
    [Tags]    NodePoweringOff    RWO    3Replicas    AttachReplicaSameNode    AbnormalReplicaNode    AbnormalAttachedNode
    # Recover: After restart the node, volume should be detached and replica is failed-Need manual to do reattached.
    Given A ${volume_size_gb} GB RWO volume with 3 replicas
    And Attach volume to node 1
    And Write data into mount point

    When Power off node 1
    And Wait ${pod_eviction_time_out} seconds

    Then Node 1 should have 1 volume replica
    And Node 1 state should be NotReady
    And Volume state should be unknown
    And Engine state should be unknown
    And Replica state on node 1 should be unknown

    When Power on node 1

    Then Node 1 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    [Teardown]    Teardown

Node with replica but not 3 replica volume attached timeout
    [Tags]    NodePoweringOff    RWO    3Replicas    AttachReplicaDiffNode    AbnormalReplicaNode    AbnormalNoAttachedNode
    # Recover: After restart the node, delete the stopped replica, and re-update the replica count to do rebuilding
    Given A ${volume_size_gb} GB RWO volume with 3 replicas
    And Attach volume to node 1
    And Write data into mount point

    When Power off node 2
    And Wait ${pod_eviction_time_out} seconds

    Then Node 1 should have 1 volume replica
    And Node 2 should have 1 volume replica
    And Node 2 state should be NotReady
    And Volume state should be degraded
    And Engine state should be running
    And Replica state on node 1 should be running
    And Replica state on node 2 should be stopped
    And Replica state on node 3 should be running

    When Power on node 2

    Then Node 2 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with no replica and non-2 replica volume attached timeout and the volume attach on no replica node
    [Documentation]
    [Tags]    NodePoweringOff    RWO    2Replicas    AttachReplicaSameNode    AbnormalNoReplicaNode    AbnormalAttachedNode
    Given A ${volume_size_gb} GB RWO volume with 2 replicas
    And Attach volume to node 3
    And Write data into mount point

    When Power off node 3
    And Wait ${pod_eviction_time_out} seconds

    Then Node 3 should have 0 volume replica
    And Node 3 state should be NotReady
    And Volume state should be unknown
    And Engine state should be unknown
    And All replicas state should be running

    When Power on node 3

    Then Node 3 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    [Teardown]    Teardown

Node with replica but non-2 replica volume attached timeout and the volume attach on no replica node
    [Documentation]
    [Tags]    NodePoweringOff    RWO    2Replicas    AttachReplicaDiffNode    AbnormalReplicaNode    AbnormalNoAttachedNode
    Given A ${volume_size_gb} GB RWO volume with 2 replicas
    And Attach volume to node 3
    And Write data into mount point

    When Power off node 1
    And Wait ${pod_eviction_time_out} seconds

    Then Node 1 should have 1 volume replica
    And Node 3 should have 0 volume replica
    And Node 1 state should be NotReady
    And Volume state should be degraded
    And Engine state should be running
    And Replica state on node 1 should be stopped
    And Replica state on node 2 should be running

    When Power on node 1

    Then Node 1 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with replica and 2 replica volume attached timeout
    [Documentation]
    [Tags]    NodePoweringOff    RWO    2Replicas    AttachReplicaSameNode    AbnormalReplicaNode    AbnormalAttachedNode
    Given A ${volume_size_gb} GB RWO volume with 2 replicas
    And Attach volume to node 1
    And Write data into mount point

    When Power off node 1
    And Wait ${pod_eviction_time_out} seconds

    Then Node 1 should have 1 volume replica
    And Node 1 state should be NotReady
    And Volume state should be unknown
    And Engine state should be unknown
    And Replica state on node 1 should be unknown
    And Replica state on node 2 should be running

    When Power on node 1

    Then Node 1 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    [Teardown]    Teardown

Node with no replica and non-2 replica volume attached timeout
    [Documentation]
    [Tags]    NodePoweringOff    RWO    2Replicas    AttachReplicaDiffNode    AbnormalNoReplicaNode    AbnormalNoAttachedNode
    Given A ${volume_size_gb} GB RWO volume with 2 replicas
    And Attach volume to node 1
    And Write data into mount point

    When Power off node 3
    And Wait ${pod_eviction_time_out} seconds

    Then Node 1 should have 1 volume replica
    And Node 3 should have 0 volume replica
    And Node 3 state should be NotReady
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running

    When Power on node 3

    Then Node 3 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with replica but non-2 replica volume attached timeout and the volume attach on replica node
    [Documentation]
    [Tags]    NodePoweringOff    RWO    2Replicas    AttachReplicaDiffNode    AbnormalReplicaNode    AbnormalAttachedNode
    Given A ${volume_size_gb} GB RWO volume with 2 replicas
    And Attach volume to node 1
    And Write data into mount point

    When Power off node 2
    And Wait ${pod_eviction_time_out} seconds

    Then Node 1 should have 1 volume replica
    And Node 1 should have 1 volume replica
    And Node 2 state should be NotReady
    And Volume state should be healthy
    And Engine state should be running
    And Replica state on node 1 should be running
    And Replica state on node 2 should be stopped

    When Power on node 2

    Then Node 2 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And Replica state on node 1 should be running
    And Replica state on node 2 should be stopped
    And Data should be intact
    [Teardown]    Teardown
