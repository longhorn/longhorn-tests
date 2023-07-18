*** Settings ***
Documentation     Test the Longhorn resillence if cluster node kubelet restart

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
${volume_type}=    RWO

*** Test Cases ***
Node with replica and 3 replica volume attached
    [Tags]    RestartKubelet    3Replicas    AttachHasReplica    AttachReplicaSameNode    AbnormalAttachedNode    AbnormalReplicaNode
    # Recover: After restart the node, volume should be detached and replica is failed. Need manual to do reattached.
    Given A ${volume_size_gb} GB ${volume_type} volume with 3 replicas
    And Attach volume to node 1
    And Write data into mount point

    When Restart Kubelet node 1

    Then Node 1 should have 1 volume replica
    And Node 1 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with replica but not 3 replica volume attached
    [Tags]    RestartKubelet    3Replicas    AttachHasReplica    AttachReplicaDiffNode    AbnormalNonAttachedNode    AbnormalReplicaNode
    # Recover: After restart the node, delete the stopped replica, and re-update the replica count to do rebuilding
    Given A ${volume_size_gb} GB ${volume_type} volume with 3 replicas
    And Attach volume to node 1
    And Write data into mount point

    When Restart Kubelet node 2

    Then Node 1 should have 1 volume replica
    And Node 2 should have 1 volume replica
    And Node 2 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with no replica and non-2 replica volume attached and the volume attach on no replica node
    [Tags]    RestartKubelet    3Replicas    AttachHasReplica    AttachReplicaSameNode    AbnormalNonAttachedNode    AbnormalNonReplicaNode
    Given A ${volume_size_gb} GB ${volume_type} volume with 2 replicas
    And Attach volume to node 3
    And Write data into mount point

    When Restart Kubelet node 3

    Then Node 3 should have 0 volume replica
    And Node 3 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with replica but non-2 replica volume attached and the volume attach on replica node
    [Tags]    RestartKubelet    2Replicas    AttachNoReplica    AttachReplicaDiffNode    AbnormalNonAttachedNode    AbnormalReplicaNode
    Given A ${volume_size_gb} GB ${volume_type} volume with 2 replicas
    And Attach volume to node 3
    And Write data into mount point

    When Restart Kubelet node 1

    Then Node 1 should have 1 volume replica
    And Node 3 should have 0 volume replica
    And Node 1 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with replica and 2 replica volume attached
    [Tags]    RestartKubelet    2Replicas    AttachHasReplica    AttachReplicaSameNode    AbnormalAttachedNode    AbnormalReplicaNode
    Given A ${volume_size_gb} GB ${volume_type} volume with 2 replicas
    And Attach volume to node 1
    And Write data into mount point

    When Restart Kubelet node 1

    Then Node 1 should have 1 volume replica
    And Node 1 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with no replica and non-2 replica volume attached and the volume attach on replica node
    [Tags]    RestartKubelet    2Replicas    AttachHasReplica    AttachReplicaDiffNode    AbnormalNonAttachedNode    AbnormalNonReplicaNode
    Given A ${volume_size_gb} GB ${volume_type} volume with 2 replicas
    And Attach volume to node 1
    And Write data into mount point

    When Restart Kubelet node 3

    Then Node 1 should have 1 volume replica
    And Node 3 should have 0 volume replica
    And Node 3 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with replica but non-2 replica volume attached and the volume attach on no replica node
    [Tags]    RestartKubelet    2Replicas    AttachHasReplica    AttachReplicaDiffNode    AbnormalNonAttachedNode    AbnormalReplicaNode
    Given A ${volume_size_gb} GB ${volume_type} volume with 2 replicas
    And Attach volume to node 1
    And Write data into mount point

    When Restart Kubelet node 2

    Then Node 1 should have 1 volume replica
    And Node 2 should have 1 volume replica
    And Node 2 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with replica and 3 replica volume attached timeout
    [Tags]    RestartKubelet    3Replicas    AttachHasReplica    AttachReplicaSameNode    AbnormalAttachedNode    AbnormalReplicaNode    Timeout
    # Recover: After restart the node, volume should be detached and replica is failed. Need manual to do reattached.
    Given A ${volume_size_gb} GB ${volume_type} volume with 3 replicas
    And Attach volume to node 1
    And Write data into mount point

    When Restart Kubelet timeout on node 1

    Then Node 1 should have 1 volume replica
    And Node 1 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with replica but not 3 replica volume attached timeout
    [Tags]    RestartKubelet    3Replicas    AttachHasReplica    AttachReplicaDiffNode    AbnormalNonAttachedNode    AbnormalReplicaNode    Timeout
    # Recover: After restart the node, delete the stopped replica, and re-update the replica count to do rebuilding
    Given A ${volume_size_gb} GB ${volume_type} volume with 3 replicas
    And Attach volume to node 1
    And Write data into mount point

    When Restart Kubelet timeout on node 2

    Then Node 1 should have 1 volume replica
    And Node 2 should have 1 volume replica
    And Node 2 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with no replica and non-2 replica volume attached and the volume attach on no replica node timeout
    [Tags]    RestartKubelet    3Replicas    AttachHasReplica    AttachReplicaSameNode    AbnormalNonAttachedNode    AbnormalNonReplicaNode    Timeout
    Given A ${volume_size_gb} GB ${volume_type} volume with 2 replicas
    And Attach volume to node 3
    And Write data into mount point

    When Restart Kubelet timeout on node 3

    Then Node 3 should have 0 volume replica
    And Node 3 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with replica but non-2 replica volume attached and the volume attach on replica node timeout
    [Tags]    RestartKubelet    2Replicas    AttachNoReplica    AttachReplicaDiffNode    AbnormalNonAttachedNode    AbnormalReplicaNode    Timeout
    Given A ${volume_size_gb} GB ${volume_type} volume with 2 replicas
    And Attach volume to node 3
    And Write data into mount point

    When Restart Kubelet timeout on node 1

    Then Node 1 should have 1 volume replica
    And Node 3 should have 0 volume replica
    And Node 1 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with replica and 2 replica volume attached timeout
    [Tags]    RestartKubelet    2Replicas    AttachHasReplica    AttachReplicaSameNode    AbnormalAttachedNode    AbnormalReplicaNode    Timeout
    Given A ${volume_size_gb} GB ${volume_type} volume with 2 replicas
    And Attach volume to node 1
    And Write data into mount point

    When Restart Kubelet timeout on node 1

    Then Node 1 should have 1 volume replica
    And Node 1 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with no replica and non-2 replica volume attached and the volume attach on replica node timeout
    [Tags]    RestartKubelet    2Replicas    AttachHasReplica    AttachReplicaDiffNode    AbnormalNonAttachedNode    AbnormalNonReplicaNode    Timeout
    Given A ${volume_size_gb} GB ${volume_type} volume with 2 replicas
    And Attach volume to node 1
    And Write data into mount point

    When Restart Kubelet timeout on node 3

    Then Node 1 should have 1 volume replica
    And Node 3 should have 0 volume replica
    And Node 3 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown

Node with replica but non-2 replica volume attached and the volume attach on no replica node timeout
    [Tags]    RestartKubelet    2Replicas    AttachHasReplica    AttachReplicaDiffNode    AbnormalNonAttachedNode    AbnormalReplicaNode    Timeout
    Given A ${volume_size_gb} GB ${volume_type} volume with 2 replicas
    And Attach volume to node 1
    And Write data into mount point

    When Restart Kubelet timeout on node 2

    Then Node 1 should have 1 volume replica
    And Node 2 should have 1 volume replica
    And Node 2 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    And Data should be intact
    [Teardown]    Teardown
