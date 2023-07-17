*** Settings ***
Documentation       Test the Longhorn resillence if cluster node powering off

Resource            ../../keywords/common.resource
Resource            ../../keywords/engine.resource
Resource            ../../keywords/replica.resource
Resource            ../../keywords/node.resource
Resource            ../../keywords/volume.resource

Suite Setup         set_test_suite_environment
Test Setup          set_test_environment    ${TEST NAME}
Test Teardown       Cleanup resource and resume state


*** Variables ***
${Gi}=                  2**30
${volume_size_gb}=      1
${sleep_interval}=      300
${volume_type}=         RWO


*** Test Cases ***
Node power off with replica-VA
    [Documentation]    | =node 1= | =node 2= | =node 3= |
    ...    | replica | replica | replica |
    ...    | attached | | |
    ...    | *power off* | | |
    ${number_of_replicas}=    Convert To Integer    3
    Set Test Variable    ${number_of_replicas}

    ${volume_type}=    Evaluate    "${volume_type}".lower()

    ${field1}=    Convert To String    {"spec": {"size": "${${volume_size_gb} * ${Gi}}"}}
    ${field2}=    Convert To String    {"spec": {"numberOfReplicas": ${number_of_replicas}}}
    ${field3}=    Convert To String    {"spec": {"accessMode": "${volume_type}"}}
    @{list_of_fields}=    Create List    ${field1}    ${field2}    ${field3}

    Given Create Volume With Fields    ${list_of_fields}
    And Attach volume to node 1
    And Write data into mount point

    When Power off node 1

    Then Node 1 should have 1 volume replica
    And Node 1 state should eventually be NotReady
    And Volume state should eventually be unknown
    And Engine state should eventually be unknown
    And Replica state on node 1 should eventually be unknown
    And Replica on node 2 state should be running
    And Replica on node 3 state should be running

    When Power on node 1

    Then Node 1 state should eventually be Ready
    And Volume state should eventually be healthy
    And Engine state should eventually be running
    And All replicas state should eventually be running
    And Data should be intact
    [Teardown]    Teardown

Node power off with replica
    [Documentation]    | =node 1= | =node 2= | =node 3= |
    ...    | replica | replica | replica |
    ...    | attached | *power off* | |
    ${number_of_replicas}=    Convert To Integer    3
    Set Test Variable    ${number_of_replicas}

    ${volume_type}=    Evaluate    "${volume_type}".lower()

    ${field1}=    Convert To String    {"spec": {"size": "${${volume_size_gb} * ${Gi}}"}}
    ${field2}=    Convert To String    {"spec": {"numberOfReplicas": ${number_of_replicas}}}
    ${field3}=    Convert To String    {"spec": {"accessMode": "${volume_type}"}}
    @{list_of_fields}=    Create List    ${field1}    ${field2}    ${field3}

    Given Create Volume With Fields    ${list_of_fields}
    And Attach volume to node 1
    And Write data into mount point

    When Power off node 2

    Then Node 1 should have 1 volume replica
    And Node 2 should have 1 volume replica
    And Node 2 state should eventually be NotReady
    And Volume state should eventually be degraded
    And Engine state should eventually be running
    And Replica state on node 2 should eventually be stopped
    And Replica on node 1 state should be running
    And Replica on node 3 state should be running
    And Data should be intact

    When Power on node 2

    Then Node 2 state should eventually be Ready
    And Volume state should eventually be healthy
    And Engine state should be running
    And All replicas state should eventually be running
    And Data should be intact
    [Teardown]    Teardown

Node power off with VA
    [Documentation]    | =node 1= | =node 2= | =node 3= |
    ...    | replica | replica | |
    ...    | | | attached |
    ...    | | | *power off* |
    ${number_of_replicas}=    Convert To Integer    2
    Set Test Variable    ${number_of_replicas}

    ${volume_type}=    Evaluate    "${volume_type}".lower()

    ${field1}=    Convert To String    {"spec": {"size": "${${volume_size_gb} * ${Gi}}"}}
    ${field2}=    Convert To String    {"spec": {"numberOfReplicas": ${number_of_replicas}}}
    ${field3}=    Convert To String    {"spec": {"accessMode": "${volume_type}"}}
    @{list_of_fields}=    Create List    ${field1}    ${field2}    ${field3}

    Given Create Volume With Fields    ${list_of_fields}
    And Attach volume to node 3
    And Write data into mount point

    When Power off node 3

    Then Node 3 should have 0 volume replica
    And Node 3 state should eventually be NotReady
    And Volume state should eventually be unknown
    And Engine state should eventually be unknown
    And All replicas state should eventually be running

    When Power on node 3

    Then Node 3 state should eventually be Ready
    And Volume state should eventually be healthy
    And Engine state should eventually be running
    And All replicas state should eventually be running
    And Data should be intact
    [Teardown]    Teardown

Node power off with replica and 1 node with VA no replica
    [Documentation]    | =node 1= | =node 2= | =node 3= |
    ...    | replica | replica | |
    ...    | | | attached |
    ...    | *power off* | | |
    ${number_of_replicas}=    Convert To Integer    2
    Set Test Variable    ${number_of_replicas}

    ${volume_type}=    Evaluate    "${volume_type}".lower()

    ${field1}=    Convert To String    {"spec": {"size": "${${volume_size_gb} * ${Gi}}"}}
    ${field2}=    Convert To String    {"spec": {"numberOfReplicas": ${number_of_replicas}}}
    ${field3}=    Convert To String    {"spec": {"accessMode": "${volume_type}"}}
    @{list_of_fields}=    Create List    ${field1}    ${field2}    ${field3}

    Given Create Volume With Fields    ${list_of_fields}
    And Attach volume to node 3
    And Write data into mount point

    When Power off node 1

    Then Node 1 should have 1 volume replica
    And Node 3 should have 0 volume replica
    And Node 1 state should eventually be NotReady
    And Volume state should eventually be degraded
    And Engine state should eventually be running
    And Replica state on node 1 should eventually be stopped
    And Replica on node 2 state should be running

    When Power on node 1

    Then Node 1 state should eventually be Ready
    And Volume state should eventually be healthy
    And Engine state should be running
    And All replicas state should eventually be running
    And Data should be intact
    [Teardown]    Teardown

Node power off with replica-VA and 1 node with no replica
    [Documentation]    | =node 1= | =node 2= | =node 3= |
    ...    | replica | replica | |
    ...    | attached | | |
    ...    | *power off* | | |
    ${number_of_replicas}=    Convert To Integer    2
    Set Test Variable    ${number_of_replicas}

    ${volume_type}=    Evaluate    "${volume_type}".lower()

    ${field1}=    Convert To String    {"spec": {"size": "${${volume_size_gb} * ${Gi}}"}}
    ${field2}=    Convert To String    {"spec": {"numberOfReplicas": ${number_of_replicas}}}
    ${field3}=    Convert To String    {"spec": {"accessMode": "${volume_type}"}}
    @{list_of_fields}=    Create List    ${field1}    ${field2}    ${field3}

    Given Create Volume With Fields    ${list_of_fields}
    And Attach volume to node 1
    And Write data into mount point

    When Power off node 1

    Then Node 1 should have 1 volume replica
    And Node 1 state should eventually be NotReady
    And Volume state should eventually be unknown
    And Engine state should eventually be unknown
    And Replica state on node 1 should eventually be unknown
    And Replica on node 2 state should be running

    When Power on node 1

    Then Node 1 state should eventually be Ready
    And Volume state should eventually be healthy
    And Engine state should eventually be running
    And All replicas state should eventually be running
    And Data should be intact
    [Teardown]    Teardown

Node power off with no replica-VA
    [Documentation]    | =node 1= | =node 2= | =node 3= |
    ...    | replica | replica | |
    ...    | attached | | |
    ...    | | | *power off* |
    ${number_of_replicas}=    Convert To Integer    2
    Set Test Variable    ${number_of_replicas}

    ${volume_type}=    Evaluate    "${volume_type}".lower()

    ${field1}=    Convert To String    {"spec": {"size": "${${volume_size_gb} * ${Gi}}"}}
    ${field2}=    Convert To String    {"spec": {"numberOfReplicas": ${number_of_replicas}}}
    ${field3}=    Convert To String    {"spec": {"accessMode": "${volume_type}"}}
    @{list_of_fields}=    Create List    ${field1}    ${field2}    ${field3}

    Given Create Volume With Fields    ${list_of_fields}
    And Attach volume to node 1
    And Write data into mount point

    When Power off node 3

    Then Node 1 should have 1 volume replica
    And Node 3 should have 0 volume replica
    And Node 3 state should eventually be NotReady
    And Volume state should eventually be healthy
    And Engine state should eventually be running
    And All replicas state should eventually be running

    When Power on node 3

    Then Node 3 state should eventually be Ready
    And Volume state should eventually be healthy
    And Engine state should be running
    And All replicas state should eventually be running
    And Data should be intact
    [Teardown]    Teardown

Node power off with replica and 1 node with no replica-VA
    [Documentation]    | =node 1= | =node 2= | =node 3= |
    ...    | replica | replica | |
    ...    | attached | *power off* | |
    ${number_of_replicas}=    Convert To Integer    2
    Set Test Variable    ${number_of_replicas}

    ${volume_type}=    Evaluate    "${volume_type}".lower()

    ${field1}=    Convert To String    {"spec": {"size": "${${volume_size_gb} * ${Gi}}"}}
    ${field2}=    Convert To String    {"spec": {"numberOfReplicas": ${number_of_replicas}}}
    ${field3}=    Convert To String    {"spec": {"accessMode": "${volume_type}"}}
    @{list_of_fields}=    Create List    ${field1}    ${field2}    ${field3}

    Given Create Volume With Fields    ${list_of_fields}
    And Attach volume to node 1
    And Write data into mount point

    When Power off node 2

    Then Node 1 should have 1 volume replica
    And Node 2 should have 1 volume replica
    And Node 2 state should eventually be NotReady
    And Volume state should eventually be healthy
    And Engine state should be running
    And Replica on node 1 state should be running
    And Replica state on node 2 should eventually be stopped
    And Data should be intact

    When Power on node 2

    Then Node 2 state should eventually be Ready
    And Volume state should eventually be healthy
    And Engine state should be running
    And Replica on node 1 state should be running
    And Replica state on node 2 should eventually be stopped
    And Data should be intact
    [Teardown]    Teardown

Node power off timeout with replica-VA
    [Documentation]    | =node 1= | =node 2= | =node 3= |
    ...    | replica | replica | replica |
    ...    | attached | | |
    ...    | *power off & all pods evicted* | | |
    ${number_of_replicas}=    Convert To Integer    3
    Set Test Variable    ${number_of_replicas}

    ${volume_type}=    Evaluate    "${volume_type}".lower()

    ${field1}=    Convert To String    {"spec": {"size": "${${volume_size_gb} * ${Gi}}"}}
    ${field2}=    Convert To String    {"spec": {"numberOfReplicas": ${number_of_replicas}}}
    ${field3}=    Convert To String    {"spec": {"accessMode": "${volume_type}"}}
    @{list_of_fields}=    Create List    ${field1}    ${field2}    ${field3}

    Given Create Volume With Fields    ${list_of_fields}
    And Attach volume to node 1
    And Write data into mount point

    When Power off node 1
    And Waiting for pods on node 1 to be evicted

    Then Node 1 should have 1 volume replica
    And Node 1 state should eventually be NotReady
    And Volume state should eventually be unknown
    And Engine state should eventually be unknown
    And Replica state on node 1 should eventually be unknown
    And Replica on node 2 state should be running
    And Replica on node 3 state should be running

    When Power on node 1

    Then Node 1 state should eventually be Ready
    And Volume state should eventually be healthy
    And Engine state should eventually be running
    And All replicas state should eventually be running
    [Teardown]    Teardown

Node power off timeout with replica
    [Documentation]    | =node 1= | =node 2= | =node 3= |
    ...    | replica | replica | replica |
    ...    | attached | *power off & all pods evicted* | |
    ${number_of_replicas}=    Convert To Integer    3
    Set Test Variable    ${number_of_replicas}

    ${volume_type}=    Evaluate    "${volume_type}".lower()

    ${field1}=    Convert To String    {"spec": {"size": "${${volume_size_gb} * ${Gi}}"}}
    ${field2}=    Convert To String    {"spec": {"numberOfReplicas": ${number_of_replicas}}}
    ${field3}=    Convert To String    {"spec": {"accessMode": "${volume_type}"}}
    @{list_of_fields}=    Create List    ${field1}    ${field2}    ${field3}

    Given Create Volume With Fields    ${list_of_fields}
    And Attach volume to node 1
    And Write data into mount point

    When Power off node 2
    And Waiting for pods on node 2 to be evicted

    Then Node 1 should have 1 volume replica
    And Node 2 should have 1 volume replica
    And Node 2 state should eventually be NotReady
    And Volume state should eventually be degraded
    And Engine state should be running
    And Replica on node 1 state should be running
    And Replica state on node 2 should eventually be stopped
    And Replica on node 3 state should be running

    When Power on node 2

    Then Node 2 state should eventually be Ready
    And Volume state should eventually be healthy
    And Engine state should be running
    And All replicas state should eventually be running
    And Data should be intact
    [Teardown]    Teardown

Node power off timeout with VA
    [Documentation]    | =node 1= | =node 2= | =node 3= |
    ...    | replica | replica | |
    ...    | | | attached |
    ...    | | | *power off & all pods evicted* |
    ${number_of_replicas}=    Convert To Integer    2
    Set Test Variable    ${number_of_replicas}

    ${volume_type}=    Evaluate    "${volume_type}".lower()

    ${field1}=    Convert To String    {"spec": {"size": "${${volume_size_gb} * ${Gi}}"}}
    ${field2}=    Convert To String    {"spec": {"numberOfReplicas": ${number_of_replicas}}}
    ${field3}=    Convert To String    {"spec": {"accessMode": "${volume_type}"}}
    @{list_of_fields}=    Create List    ${field1}    ${field2}    ${field3}

    Given Create Volume With Fields    ${list_of_fields}
    And Attach volume to node 3
    And Write data into mount point

    When Power off node 3
    And Waiting for pods on node 3 to be evicted

    Then Node 3 should have 0 volume replica
    And Node 3 state should eventually be NotReady
    And Volume state should eventually be unknown
    And Engine state should eventually be unknown
    And All replicas state should eventually be running

    When Power on node 3

    Then Node 3 state should eventually be Ready
    And Volume state should eventually be healthy
    And Engine state should eventually be running
    And All replicas state should eventually be running
    [Teardown]    Teardown

Node power off timeout with replica and 1 node with VA no replica
    [Documentation]    | =node 1= | =node 2= | =node 3= |
    ...    | replica | replica | |
    ...    | | | attached |
    ...    | *power off & all pods evicted* | | |
    ${number_of_replicas}=    Convert To Integer    2
    Set Test Variable    ${number_of_replicas}

    ${volume_type}=    Evaluate    "${volume_type}".lower()

    ${field1}=    Convert To String    {"spec": {"size": "${${volume_size_gb} * ${Gi}}"}}
    ${field2}=    Convert To String    {"spec": {"numberOfReplicas": ${number_of_replicas}}}
    ${field3}=    Convert To String    {"spec": {"accessMode": "${volume_type}"}}
    @{list_of_fields}=    Create List    ${field1}    ${field2}    ${field3}

    Given Create Volume With Fields    ${list_of_fields}
    And Attach volume to node 3
    And Write data into mount point

    When Power off node 1
    And Waiting for pods on node 1 to be evicted

    Then Node 1 should have 1 volume replica
    And Node 3 should have 0 volume replica
    And Node 1 state should eventually be NotReady
    And Volume state should eventually be degraded
    And Engine state should be running
    And Replica state on node 1 should eventually be stopped
    And Replica on node 2 state should be running

    When Power on node 1

    Then Node 1 state should eventually be Ready
    And Volume state should eventually be healthy
    And Engine state should be running
    And All replicas state should eventually be running
    And Data should be intact
    [Teardown]    Teardown

Node power off timeout with replica-VA and 1 node no replica-VA
    [Documentation]    | =node 1= | =node 2= | =node 3= |
    ...    | replica | replica | |
    ...    | attached | | |
    ...    | *power off & all pods evicted* | | |
    ${number_of_replicas}=    Convert To Integer    2
    Set Test Variable    ${number_of_replicas}

    ${volume_type}=    Evaluate    "${volume_type}".lower()

    ${field1}=    Convert To String    {"spec": {"size": "${${volume_size_gb} * ${Gi}}"}}
    ${field2}=    Convert To String    {"spec": {"numberOfReplicas": ${number_of_replicas}}}
    ${field3}=    Convert To String    {"spec": {"accessMode": "${volume_type}"}}
    @{list_of_fields}=    Create List    ${field1}    ${field2}    ${field3}

    Given Create Volume With Fields    ${list_of_fields}
    And Attach volume to node 1
    And Write data into mount point

    When Power off node 1
    And Waiting for pods on node 1 to be evicted

    Then Node 1 should have 1 volume replica
    And Node 1 state should eventually be NotReady
    And Volume state should eventually be unknown
    And Engine state should eventually be unknown
    And Replica state on node 1 should eventually be unknown
    And Replica on node 2 state should be running

    When Power on node 1

    Then Node 1 state should eventually be Ready
    And Volume state should eventually be healthy
    And Engine state should eventually be running
    And All replicas state should eventually be running
    [Teardown]    Teardown

Node power off timeout with no replica-VA
    [Documentation]    | =node 1= | =node 2= | =node 3= |
    ...    | replica | replica | |
    ...    | attached | | *power off & all pods evicted* |
    ${number_of_replicas}=    Convert To Integer    2
    Set Test Variable    ${number_of_replicas}

    ${volume_type}=    Evaluate    "${volume_type}".lower()

    ${field1}=    Convert To String    {"spec": {"size": "${${volume_size_gb} * ${Gi}}"}}
    ${field2}=    Convert To String    {"spec": {"numberOfReplicas": ${number_of_replicas}}}
    ${field3}=    Convert To String    {"spec": {"accessMode": "${volume_type}"}}
    @{list_of_fields}=    Create List    ${field1}    ${field2}    ${field3}

    Given Create Volume With Fields    ${list_of_fields}
    And Attach volume to node 1
    And Write data into mount point

    When Power off node 3
    And Waiting for pods on node 3 to be evicted

    Then Node 1 should have 1 volume replica
    And Node 3 should have 0 volume replica
    And Node 3 state should eventually be NotReady
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should eventually be running

    When Power on node 3

    Then Node 3 state should eventually be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should eventually be running
    And Data should be intact
    [Teardown]    Teardown

Node power off timeout with replica and 1 node with no replica-VA
    [Documentation]    | =node 1= | =node 2= | =node 3= |
    ...    | replica | replica | |
    ...    | attached | *power off & all pods evicted* | |
    ${number_of_replicas}=    Convert To Integer    2
    Set Test Variable    ${number_of_replicas}

    ${volume_type}=    Evaluate    "${volume_type}".lower()

    ${field1}=    Convert To String    {"spec": {"size": "${${volume_size_gb} * ${Gi}}"}}
    ${field2}=    Convert To String    {"spec": {"numberOfReplicas": ${number_of_replicas}}}
    ${field3}=    Convert To String    {"spec": {"accessMode": "${volume_type}"}}
    @{list_of_fields}=    Create List    ${field1}    ${field2}    ${field3}

    Given Create Volume With Fields    ${list_of_fields}
    And Attach volume to node 1
    And Write data into mount point

    When Power off node 2
    And Waiting for pods on node 2 to be evicted

    Then Node 1 should have 1 volume replica
    And Node 1 should have 1 volume replica
    And Node 2 state should eventually be NotReady
    And Volume state should be healthy
    And Engine state should be running
    And Replica on node 1 state should be running
    And Replica state on node 2 should eventually be stopped

    When Power on node 2

    Then Node 2 state should eventually be Ready
    And Volume state should be healthy
    And Engine state should be running
    And Replica on node 1 state should be running
    And Replica state on node 2 should eventually be stopped
    And Data should be intact
    [Teardown]    Teardown
