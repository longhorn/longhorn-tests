*** Settings ***
Documentation    Volume Topology Test Cases
...              Issue: https://github.com/longhorn/longhorn/issues/13493
...
...              Covers the opt-in `volumeTopology` StorageClass parameter
...              (any | zonal | regional) that pins a volume's replicas to
...              the failure domain resolved at provisioning time.

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/node.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Volume Topology Zonal Pins Replicas And PV To Resolved Zone
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/13493
    ...
    ...    Environment: a multi-zone cluster with topology.kubernetes.io/zone
    ...    (and optionally topology.kubernetes.io/region) node labels,
    ...    csi-allowed-topology-keys including those keys,
    ...    and StorageClasses with volumeBindingMode: WaitForFirstConsumer.
    ...
    ...    Case 1: volumeTopology: zonal —
    ...    the Volume CR stores a single topologyRequirement term equal to the first consumer pod's zone,
    ...    the PV node affinity is narrowed to the same zone, and all replicas are placed on nodes in that zone.
    ...
    ...    Manual test steps:
    ...    1. Label nodes with topology.kubernetes.io/zone
    ...    2. Set csi-allowed-topology-keys to include topology.kubernetes.io/zone
    ...    3. Create a StorageClass with volumeTopology: zonal and volumeBindingMode: WaitForFirstConsumer
    ...    4. Create a workload using the StorageClass
    ...    5. Determine which zone the workload's first consumer pod landed on
    ...    6. Verify the Volume CR stores a single topologyRequirement term equal to
    ...       that resolved zone
    ...    7. Verify the PV node affinity is narrowed to that same zone
    ...    8. Verify all replicas are placed on nodes in that zone
    ...
    ...    Each of the 3 worker nodes is put in its own zone so that
    ...    whichever node the scheduler picks for the first consumer pod,
    ...    the resolved zone is unambiguous, without assuming in advance
    ...    which zone will be picked.
    ...
    ...    Since each zone therefore only has 1 node, numberOfReplicas=2
    ...    would otherwise get stuck Degraded forever (a second node in the
    ...    resolved zone would never become available for the 2nd replica).
    ...    replicaSoftAntiAffinity=enabled allows both replicas to share the
    ...    same node, so the volume can still reach Healthy within a
    ...    single-node zone.
    Given Setting csi-allowed-topology-keys is set to topology.kubernetes.io/zone
    And Set k8s node 0 zone lh-zone0
    And Set k8s node 1 zone lh-zone1
    And Set k8s node 2 zone lh-zone2
    And Rollout restart daemonset longhorn-csi-plugin in namespace longhorn-system
    And Wait for rollout of daemonset longhorn-csi-plugin in namespace longhorn-system to complete

    When Create storageclass longhorn-test with
    ...    dataEngine=${DATA_ENGINE}
    ...    replicaSoftAntiAffinity=enabled
    ...    volumeBindingMode=WaitForFirstConsumer
    ...    volumeTopology=zonal
    And Create persistentvolumeclaim 0 without waiting for bound    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 100 MB data to file data in deployment 0

    ${resolved_zone} =    Get zone of deployment 0 pod node

    Then Run command and expect output
    ...    kubectl get volumes -n longhorn-system -ojsonpath='{.items[0].spec.topologyRequirement}'
    ...    ${resolved_zone}
    And Run command and expect output
    ...    kubectl get pv -ojsonpath='{.items[0].spec.nodeAffinity.required.nodeSelectorTerms[*].matchExpressions[*].values[*]}'
    ...    ${resolved_zone}
    And Wait for volume of deployment 0 replicas to be in zone ${resolved_zone}
    And Check deployment 0 data in file data is intact

Test Volume Topology Any Is Unconstrained
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/13493
    ...
    ...    Environment: a multi-zone cluster with topology.kubernetes.io/zone
    ...    (and optionally topology.kubernetes.io/region) node labels,
    ...    csi-allowed-topology-keys including those keys,
    ...    and StorageClasses with volumeBindingMode: WaitForFirstConsumer.
    ...
    ...    Case 2: volumeTopology: any (or unset) —
    ...    Regression check: volumeTopology unset (default: any) keeps the
    ...    existing unconstrained behavior. No topologyRequirement is stored
    ...    and PV / replica behavior is unchanged.
    Given Setting csi-allowed-topology-keys is set to topology.kubernetes.io/zone
    And Set k8s node 0 zone lh-zone0
    And Set k8s node 1 zone lh-zone1
    And Set k8s node 2 zone lh-zone2
    And Rollout restart daemonset longhorn-csi-plugin in namespace longhorn-system
    And Wait for rollout of daemonset longhorn-csi-plugin in namespace longhorn-system to complete

    When Create storageclass longhorn-test with
    ...    dataEngine=${DATA_ENGINE}
    ...    volumeBindingMode=WaitForFirstConsumer
    ...    replicaSoftAntiAffinity=enabled    # each zone only has 1 node; allow replicas to share a node so the volume doesn't get stuck Degraded
    And Create persistentvolumeclaim 0 without waiting for bound    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy

    Then Run command and not expect output
    ...    kubectl get volumes -n longhorn-system -ojsonpath='{.items[0].spec.topologyRequirement}'
    ...    zone

Test Volume Topology Zonal Hard Failure Without Fallback
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/13493
    ...
    ...    Environment: a multi-zone cluster with topology.kubernetes.io/zone
    ...    (and optionally topology.kubernetes.io/region) node labels,
    ...    csi-allowed-topology-keys including those keys,
    ...    and StorageClasses with volumeBindingMode: WaitForFirstConsumer.
    ...
    ...    Case 3: Hard failure without fallback —
    ...    When the resolved zone has no schedulable capacity, the volume
    ...    stays Scheduled=False instead of placing replicas in another zone,
    ...    and recovers automatically once capacity is available in the zone.
    ...
    ...    Each of the 3 worker nodes is put in its own zone, so whichever
    ...    zone the first consumer pod resolves to, that zone only has 1
    ...    node. replicaSoftAntiAffinity is intentionally left disabled
    ...    (the default) so replicas cannot share a node — with
    ...    numberOfReplicas=3 (StorageClass default) and only 1 node in the
    ...    resolved zone, at most 1 replica can schedule, so the volume
    ...    must stay Degraded, and the other 2 replicas must NOT fall back
    ...    to nodes in other zones. The zone is only "recovered" once all 3
    ...    nodes are relabeled into the resolved zone, giving the volume
    ...    enough nodes in-zone to schedule all 3 replicas and become
    ...    Healthy.
    Given Setting csi-allowed-topology-keys is set to topology.kubernetes.io/zone
    And Set k8s node 0 zone lh-zone0
    And Set k8s node 1 zone lh-zone1
    And Set k8s node 2 zone lh-zone2
    And Rollout restart daemonset longhorn-csi-plugin in namespace longhorn-system
    And Wait for rollout of daemonset longhorn-csi-plugin in namespace longhorn-system to complete

    When Create storageclass longhorn-test with
    ...    dataEngine=${DATA_ENGINE}
    ...    volumeBindingMode=WaitForFirstConsumer
    ...    volumeTopology=zonal
    And Create persistentvolumeclaim 0 without waiting for bound    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    Then Wait for volume of deployment 0 condition scheduled to be false
    And Wait for volume of deployment 0 degraded

    ${resolved_zone} =    Get zone of deployment 0 pod node
    Wait for volume of deployment 0 replicas to be in zone ${resolved_zone}

    When Set k8s node 0 zone ${resolved_zone}
    And Set k8s node 1 zone ${resolved_zone}
    And Set k8s node 2 zone ${resolved_zone}
    Then Wait for volume of deployment 0 condition scheduled to be true
    And Wait for volume of deployment 0 healthy

    And Run command and expect output
    ...    kubectl get volumes -n longhorn-system -ojsonpath='{.items[0].spec.topologyRequirement}'
    ...    ${resolved_zone}
    And Run command and expect output
    ...    kubectl get pv -ojsonpath='{.items[0].spec.nodeAffinity.required.nodeSelectorTerms[*].matchExpressions[*].values[*]}'
    ...    ${resolved_zone}
    And Wait for volume of deployment 0 replicas to be in zone ${resolved_zone}

Test Volume Topology Zonal Rebuild Keeps Zone
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/13493
    ...
    ...    Environment: a multi-zone cluster with topology.kubernetes.io/zone
    ...    (and optionally topology.kubernetes.io/region) node labels,
    ...    csi-allowed-topology-keys including those keys,
    ...    and StorageClasses with volumeBindingMode: WaitForFirstConsumer.
    ...
    ...    Case 4: Rebuild keeps the zone —
    ...    After a replica is deleted, the replacement replica is scheduled
    ...    in the stored zone.
    Given Setting csi-allowed-topology-keys is set to topology.kubernetes.io/zone
    And Set k8s node 0 zone lh-zone0
    And Set k8s node 1 zone lh-zone1
    And Set k8s node 2 zone lh-zone2
    And Rollout restart daemonset longhorn-csi-plugin in namespace longhorn-system
    And Wait for rollout of daemonset longhorn-csi-plugin in namespace longhorn-system to complete

    When Create storageclass longhorn-test with
    ...    dataEngine=${DATA_ENGINE}
    ...    volumeBindingMode=WaitForFirstConsumer
    ...    volumeTopology=zonal
    ...    replicaSoftAntiAffinity=enabled    # each zone only has 1 node; allow replicas to share a node so the volume doesn't get stuck Degraded
    And Create persistentvolumeclaim 0 without waiting for bound    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy

    ${resolved_zone} =    Get zone of deployment 0 pod node
    Wait for volume of deployment 0 replicas to be in zone ${resolved_zone}

    When Delete 1 replicas of volume of deployment 0
    And Wait until volume of deployment 0 replicas rebuilding completed
    Then Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 0 replicas to be in zone ${resolved_zone}

Test Volume Topology Zonal Replica Count Increase Stays In Zone
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/13493
    ...
    ...    Environment: a multi-zone cluster with topology.kubernetes.io/zone
    ...    (and optionally topology.kubernetes.io/region) node labels,
    ...    csi-allowed-topology-keys including those keys,
    ...    and StorageClasses with volumeBindingMode: WaitForFirstConsumer.
    ...
    ...    Case 5: Replica count increase —
    ...    New replicas from updating numberOfReplicas stay in the stored
    ...    zone.
    Given Setting csi-allowed-topology-keys is set to topology.kubernetes.io/zone
    And Set k8s node 0 zone lh-zone0
    And Set k8s node 1 zone lh-zone1
    And Set k8s node 2 zone lh-zone2
    And Rollout restart daemonset longhorn-csi-plugin in namespace longhorn-system
    And Wait for rollout of daemonset longhorn-csi-plugin in namespace longhorn-system to complete

    When Create storageclass longhorn-test with
    ...    dataEngine=${DATA_ENGINE}
    ...    numberOfReplicas=1
    ...    volumeBindingMode=WaitForFirstConsumer
    ...    volumeTopology=zonal
    ...    replicaSoftAntiAffinity=enabled    # each zone only has 1 node; allow replicas to share a node so the volume doesn't get stuck Degraded when scaled to 2 replicas
    And Create persistentvolumeclaim 0 without waiting for bound    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy

    ${resolved_zone} =    Get zone of deployment 0 pod node
    Wait for volume of deployment 0 replicas to be in zone ${resolved_zone}

    When Update volume of deployment 0 replica count to 2
    Then Volume of deployment 0 should have 2 running replicas
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 0 replicas to be in zone ${resolved_zone}

Test Volume Topology Regional Allows Cross Zone Replicas Within Region
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/13493
    ...
    ...    Environment: a multi-zone cluster with topology.kubernetes.io/zone
    ...    (and optionally topology.kubernetes.io/region) node labels,
    ...    csi-allowed-topology-keys including those keys,
    ...    and StorageClasses with volumeBindingMode: WaitForFirstConsumer.
    ...
    ...    Case 6: volumeTopology: regional —
    ...    volumeTopology: regional stores a region-only term; the PV node
    ...    affinity is narrowed to that region, and replicas may spread
    ...    across zones within the region.
    Given Setting csi-allowed-topology-keys is set to topology.kubernetes.io/region
    And Set k8s node 0 zone lh-zone0
    And Set k8s node 1 zone lh-zone1
    And Set k8s node 2 zone lh-zone2
    And Set k8s node 0 region lh-region0
    And Set k8s node 1 region lh-region1
    And Set k8s node 2 region lh-region2
    And Rollout restart daemonset longhorn-csi-plugin in namespace longhorn-system
    And Wait for rollout of daemonset longhorn-csi-plugin in namespace longhorn-system to complete

    When Create storageclass longhorn-test with
    ...    dataEngine=${DATA_ENGINE}
    ...    volumeBindingMode=WaitForFirstConsumer
    ...    volumeTopology=regional
    ...    replicaSoftAntiAffinity=enabled    # each region only has 1 node; allow replicas to share a node so the volume doesn't get stuck Degraded
    And Create persistentvolumeclaim 0 without waiting for bound    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy

    ${resolved_region} =    Get region of deployment 0 pod node

    Then Run command and expect output
    ...    kubectl get volumes -n longhorn-system -ojsonpath='{.items[0].spec.topologyRequirement}'
    ...    ${resolved_region}
    And Run command and not expect output
    ...    kubectl get volumes -n longhorn-system -ojsonpath='{.items[0].spec.topologyRequirement}'
    ...    lh-zone
    And Run command and expect output
    ...    kubectl get pv -ojsonpath='{.items[0].spec.nodeAffinity.required.nodeSelectorTerms[*].matchExpressions[*].values[*]}'
    ...    ${resolved_region}
    And Wait for volume of deployment 0 replicas to be in region ${resolved_region}

Test Volume Topology Zonal On Cluster Without Zone Labels Is Unconstrained
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/13493
    ...
    ...    Environment: a multi-zone cluster with topology.kubernetes.io/zone
    ...    (and optionally topology.kubernetes.io/region) node labels,
    ...    csi-allowed-topology-keys including those keys,
    ...    and StorageClasses with volumeBindingMode: WaitForFirstConsumer.
    ...
    ...    Case 7: Degenerate cluster —
    ...    On nodes without zone labels, a zonal StorageClass creates an
    ...    unconstrained volume, so the same StorageClass works on
    ...    single-zone/unlabeled clusters.
    Given Setting csi-allowed-topology-keys is set to topology.kubernetes.io/zone
    And Rollout restart daemonset longhorn-csi-plugin in namespace longhorn-system
    And Wait for rollout of daemonset longhorn-csi-plugin in namespace longhorn-system to complete

    When Create storageclass longhorn-test with
    ...    dataEngine=${DATA_ENGINE}
    ...    volumeBindingMode=WaitForFirstConsumer
    ...    volumeTopology=zonal
    ...    replicaSoftAntiAffinity=enabled    # applied uniformly across all cases in this suite to avoid node-not-enough Degraded volumes
    And Create persistentvolumeclaim 0 without waiting for bound    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy

    Then Run command and not expect output
    ...    kubectl get volumes -n longhorn-system -ojsonpath='{.items[0].spec.topologyRequirement}'
    ...    lh-zone

Test Volume Topology Setting Misconfiguration Missing Csi Allowed Topology Key
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/13493
    ...
    ...    Environment: a multi-zone cluster with topology.kubernetes.io/zone
    ...    (and optionally topology.kubernetes.io/region) node labels,
    ...    csi-allowed-topology-keys including those keys,
    ...    and StorageClasses with volumeBindingMode: WaitForFirstConsumer.
    ...
    ...    Case 8: Setting misconfiguration —
    ...    When nodes report the zone label but csi-allowed-topology-keys
    ...    does not include it, CreateVolume is rejected with a message
    ...    naming the missing key and the setting.
    ...
    ...    Volume 0 is created directly (bypassing StorageClass/PVC/CSI
    ...    provisioning) and is expected to fail, since csi-allowed-topology-keys
    ...    does not include the zone key that the nodes report.
    Given Setting csi-allowed-topology-keys is set to ${EMPTY}
    And Set k8s node 0 zone lh-zone0
    And Set k8s node 1 zone lh-zone1
    And Set k8s node 2 zone lh-zone2
    And Rollout restart daemonset longhorn-csi-plugin in namespace longhorn-system
    And Wait for rollout of daemonset longhorn-csi-plugin in namespace longhorn-system to complete

    When Create volume 0 with should fail
    ...    dataEngine=${DATA_ENGINE}
    ...    volumeTopology=zonal
    ...    replicaSoftAntiAffinity=enabled    # applied uniformly across all cases in this suite to avoid node-not-enough Degraded volumes

Test Volume Topology Zonal Rejects Replica Zone Soft Anti Affinity Disabled
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/13493
    ...
    ...    Environment: a multi-zone cluster with topology.kubernetes.io/zone
    ...    (and optionally topology.kubernetes.io/region) node labels,
    ...    csi-allowed-topology-keys including those keys,
    ...    and StorageClasses with volumeBindingMode: WaitForFirstConsumer.
    ...
    ...    Case 9: Invalid combination —
    ...    1. A StorageClass with volumeTopology: zonal and
    ...       replicaZoneSoftAntiAffinity: disabled is rejected at
    ...       provisioning.
    ...    2. Updating a zonal volume's replicaZoneSoftAntiAffinity to
    ...       disabled after creation is rejected by the webhook.
    Given Setting csi-allowed-topology-keys is set to topology.kubernetes.io/zone
    And Set k8s node 0 zone lh-zone0
    And Set k8s node 1 zone lh-zone1
    And Set k8s node 2 zone lh-zone2
    And Rollout restart daemonset longhorn-csi-plugin in namespace longhorn-system
    And Wait for rollout of daemonset longhorn-csi-plugin in namespace longhorn-system to complete

    When Create storageclass longhorn-test with
    ...    dataEngine=${DATA_ENGINE}
    ...    volumeTopology=zonal
    ...    replicaZoneSoftAntiAffinity=disabled
    And Create persistentvolumeclaim 0 without waiting for bound    sc_name=longhorn-test

    Then No volume created

    When Delete deployment 0
    And Delete persistentvolumeclaim 0
    And Delete storageclass longhorn-test

    And Create storageclass longhorn-test with
    ...    dataEngine=${DATA_ENGINE}
    ...    volumeBindingMode=WaitForFirstConsumer
    ...    volumeTopology=zonal
    ...    replicaSoftAntiAffinity=enabled    # applied uniformly across all cases in this suite to avoid node-not-enough Degraded volumes
    And Create persistentvolumeclaim 0 without waiting for bound    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy

    Then Update volume of deployment 0 replicaZoneSoftAntiAffinity to disabled should fail

Test Volume Topology Requirement Is Immutable
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/13493
    ...
    ...    Environment: a multi-zone cluster with topology.kubernetes.io/zone
    ...    (and optionally topology.kubernetes.io/region) node labels,
    ...    csi-allowed-topology-keys including those keys,
    ...    and StorageClasses with volumeBindingMode: WaitForFirstConsumer.
    ...
    ...    Case 10: Immutability —
    ...    spec.topologyRequirement cannot be modified after creation.
    Given Setting csi-allowed-topology-keys is set to topology.kubernetes.io/zone
    And Set k8s node 0 zone lh-zone0
    And Set k8s node 1 zone lh-zone1
    And Set k8s node 2 zone lh-zone2
    And Rollout restart daemonset longhorn-csi-plugin in namespace longhorn-system
    And Wait for rollout of daemonset longhorn-csi-plugin in namespace longhorn-system to complete

    When Create storageclass longhorn-test with
    ...    dataEngine=${DATA_ENGINE}
    ...    volumeBindingMode=WaitForFirstConsumer
    ...    volumeTopology=zonal
    ...    replicaSoftAntiAffinity=enabled    # allow replicas to share a node so the volume doesn't get stuck Degraded
    And Create persistentvolumeclaim 0 without waiting for bound    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy

    Then Update volume of deployment 0 topologyRequirement to lh-zone1 should fail

Test Volume Topology Zonal V2 Volume Shard Placement Respects Zone
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/13493
    ...
    ...    Environment: a multi-zone cluster with topology.kubernetes.io/zone
    ...    (and optionally topology.kubernetes.io/region) node labels,
    ...    csi-allowed-topology-keys including those keys,
    ...    and StorageClasses with volumeBindingMode: WaitForFirstConsumer.
    ...
    ...    Case 11: v2 erasure-coded (sharded) volumes: shard placement respects the
    ...    stored topologyRequirement (same constraint as replicas).
    ...
    ...    Reference StorageClass (requires at least k+m nodes, one shard
    ...    per node via hard anti-affinity; 4+2 tolerates 2 failures at
    ...    1.5x overhead):
    ...    kind: StorageClass
    ...    apiVersion: storage.k8s.io/v1
    ...    metadata:
    ...      name: longhorn-v2-sharded
    ...    provisioner: driver.longhorn.io
    ...    allowVolumeExpansion: true
    ...    reclaimPolicy: Delete
    ...    volumeBindingMode: Immediate
    ...    parameters:
    ...      dataEngine: "v2"
    ...      dataLayout.type: "sharded"
    ...      dataLayout.mode: "erasureCoding"
    ...      dataLayout.dataChunks: "4"        # k: data chunks
    ...      dataLayout.parityChunks: "2"      # m: parity chunks = failures tolerated
    ...      dataLayout.stripSizeKB: "64"      # chunk size in KB; power of two 4-1024, fixed at creation
    ...      numberOfReplicas: "1"             # must be 1 - parity provides fault tolerance, not replicas
    ...      dataLocality: "disabled"          # must be disabled - chunks span k+m nodes
    ...      fsType: "ext4"
    ...
    ...    This test environment only guarantees 3 worker nodes, so a 2+1
    ...    layout (k=2 data + m=1 parity = 3 shards) is used instead of the
    ...    4+2 example above, with volumeBindingMode: WaitForFirstConsumer
    ...    so the zone is resolved from the first consumer pod, consistent
    ...    with the rest of this suite. All 3 shards must land within the
    ...    single pinned zone, so all 3 nodes are labeled into that zone.
    ...
    ...    Note: replicaSoftAntiAffinity is not applicable here since EC
    ...    shard placement uses hard anti-affinity across distinct nodes
    ...    (each of the 3 nodes hosts exactly 1 shard), unlike regular
    ...    volume replicas.
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    v1 data engine does not support sharded volumes
    END
    Given Setting csi-allowed-topology-keys is set to topology.kubernetes.io/zone
    And Set k8s node 0 zone lh-zone0
    And Set k8s node 1 zone lh-zone0
    And Set k8s node 2 zone lh-zone0
    And Rollout restart daemonset longhorn-csi-plugin in namespace longhorn-system
    And Wait for rollout of daemonset longhorn-csi-plugin in namespace longhorn-system to complete

    ${dataLayout} =    Create Dictionary
    ...    type=sharded
    ...    mode=erasureCoding
    ...    dataChunks=2
    ...    parityChunks=1
    ...    stripSizeKB=64

    When Create storageclass longhorn-test with
    ...    dataEngine=v2
    ...    numberOfReplicas=1
    ...    dataLocality=disabled
    ...    fsType=ext4
    ...    volumeBindingMode=WaitForFirstConsumer
    ...    volumeTopology=zonal
    ...    dataLayout=${dataLayout}
    And Create persistentvolumeclaim 0 without waiting for bound    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 100 MB data to file data in deployment 0

    ${resolved_zone} =    Get zone of deployment 0 pod node

    Then Run command and expect output
    ...    kubectl get volumes -n longhorn-system -ojsonpath='{.items[0].spec.topologyRequirement}'
    ...    ${resolved_zone}
    And Run command and expect output
    ...    kubectl get pv -ojsonpath='{.items[0].spec.nodeAffinity.required.nodeSelectorTerms[*].matchExpressions[*].values[*]}'
    ...    ${resolved_zone}
    And Wait for volume of deployment 0 replicas to be in zone ${resolved_zone}
    And Check deployment 0 data in file data is intact
