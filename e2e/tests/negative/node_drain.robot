*** Settings ***
Documentation    Negative Test Cases

Test Tags    negative

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/host.resource
Resource    ../keywords/node.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Force Drain Volume Node While Replica Rebuilding
    Given Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0 using RWO volume with longhorn-test storageclass
    And Create persistentvolumeclaim 1 using RWX volume with longhorn-test storageclass
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Write 2048 MB data to file data.txt in deployment 0
    And Write 2048 MB data to file data.txt in deployment 1

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica of deployment 0 volume on volume node
        And Wait until volume of deployment 0 replica rebuilding started on volume node
        And Force drain volume of deployment 0 volume node

        Then Wait for volume of deployment 0 attached to another node and degraded
        And Uncordon the drained node
        And Wait for volume of deployment 0 attached and healthy
        And Wait for deployment 0 pods stable
        And Check deployment 0 data in file data.txt is intact

        When Delete replica of deployment 1 volume on volume node
        And Wait until volume of deployment 1 replica rebuilding started on volume node
        And Force drain volume of deployment 1 volume node

        Then Wait for volume of deployment 1 attached to another node and degraded
        And Uncordon the drained node
        And Wait for volume of deployment 1 attached and healthy
        And Wait for deployment 1 pods stable
        And Check deployment 1 data in file data.txt is intact
    END

Force Drain Replica Node While Replica Rebuilding
    Given Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0 using RWO volume with longhorn-test storageclass
    And Create persistentvolumeclaim 1 using RWX volume with longhorn-test storageclass
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Write 2048 MB data to file data.txt in deployment 0
    And Write 2048 MB data to file data.txt in deployment 1

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica of deployment 0 volume on replica node
        And Wait until volume of deployment 0 replica rebuilding started on replica node
        And Force drain volume of deployment 0 replica node

        Then Wait for volume of deployment 0 attached to the original node and degraded
        And Uncordon the drained node
        And Wait for volume of deployment 0 attached and healthy
        And Wait for deployment 0 pods stable
        And Check deployment 0 data in file data.txt is intact

        When Delete replica of deployment 1 volume on replica node
        And Wait until volume of deployment 1 replica rebuilding started on replica node
        And Force drain volume of deployment 1 replica node

        Then Wait for volume of deployment 1 attached to the original node and degraded
        And Uncordon the drained node
        And Wait for volume of deployment 1 attached and healthy
        And Wait for deployment 1 pods stable
        And Check deployment 1 data in file data.txt is intact
    END

Drain node with force
    [Documentation]    Drain node with force
    ...    1. Deploy a cluster contains 3 worker nodes N1, N2, N3.
    ...    2. Deploy Longhorn.
    ...    3. Create a 1-replica deployment with a 3-replica Longhorn volume. The volume is attached to N1.
    ...    4. Write some data to the volume and get the md5sum.
    ...    5. Force drain and remove N2, which contains one replica only.
    ...        kubectl drain <Node name> --delete-emptydir-data=true --force=true --grace-period=-1 --ignore-daemonsets=true --timeout=<Desired timeout in secs>
    ...    6. Wait for the volume Degraded.
    ...    7. Force drain and remove N1, which is the node the volume is attached to.
    ...        kubectl drain <Node name> --delete-emptydir-data=true --force=true --grace-period=-1 --ignore-daemonsets=true --timeout=<Desired timeout in secs>
    ...
    ...    8. Wait for the volume detaching then being recovered. Will get attached to the workload/node.
    ...    9. Verify the instance manager pods are gone and not recreated after the drain.
    ...    10. Validate the volume content. The data is intact.
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0 using RWO volume with longhorn-test storageclass
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 2048 MB data to file data.txt in deployment 0

    And Force drain volume of deployment 0 replica node
    Then Wait for volume of deployment 0 attached to the original node and degraded

    And Force drain volume of deployment 0 volume node
    And Wait for volume of deployment 0 attached to another node and degraded
    And Check instance-manager pod is not running on drained node
    Then Check deployment 0 data in file data.txt is intact

Drain node without force
    [Documentation]    Drain node without force
    ...    1. Cordon the node. Longhorn will automatically disable the node scheduling when a Kubernetes node is cordoned.
    ...    2. Evict all the replicas from the node.
    ...    3. Run the following command to drain the node with force flag set to false.
    ...        kubectl drain <Node name> --delete-emptydir-data --force=false --grace-period=-1 --ignore-daemonsets=true --timeout=<Desired timeout in secs>
    ...    4. Observe that the workloads move to another node. The volumes should first detach and attach to workloads once they move to another node.
    ...    5. One by one all the pods should get evicted.
    ...    6. Verify the instance manager pods are gone and not recreated after the drain.
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0 using RWO volume with longhorn-test storageclass
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 2048 MB data to file data.txt in deployment 0

    When Cordon deployment 0 volume node
    And Delete replica of deployment 0 volume on volume node
    And Drain volume of deployment 0 volume node
    And Wait for volume of deployment 0 attached to another node and degraded
    And Check instance-manager pod is not running on drained node
    Then Check deployment 0 data in file data.txt is intact

Test kubectl drain nodes for PVC/PV/LHV is created through Longhorn API
    [Documentation]    Test kubectl drain nodes for PVC/PV/LHV is created through Longhorn API
    ...    Given 1 PVC/PV/LHV created through Longhorn API And LHV is not yet attached/replicated.
    ...    When kubectl drain nodes.
    ...        NODE=centos-worker-0
    ...        kubectl cordon ${NODE}
    ...        kubectl drain --force --ignore-daemonsets --delete-emptydir-data --grace-period=10 ${NODE}
    ...    Then all node should successfully drain.
    When Create volume 0 with   dataEngine=${DATA_ENGINE}
    And Wait for volume 0 detached
    And Create persistentvolume for volume 0
    And Create persistentvolumeclaim for volume 0
    And Force drain all nodes

Stopped replicas on deleted nodes should not be counted as healthy replicas when draining nodes
    [Documentation]    Stopped replicas on deleted nodes should not be counted as healthy replicas when draining nodes
    ...    When draining a node, the node will be set as unscheduled and all pods should be evicted.
    ...    By Longhorn’s default settings, the replica will only be evicted if there is another healthy replica on the running node.
    ...    Related Issue:
    ...    - https://github.com/longhorn/longhorn/issues/2237
    ...
    ...    Given Longhorn with 2 nodes cluster: Node_1, Node_2
    ...    And Update the Node Drain Policy setting to block-if-contains-last-replica
    ...    And Create a 5Gi detached volume with 2 replicas.
    ...    And Stop Node_1 that contains one of the replicas.
    ...    When Attempts to drain Node_2 that contains remaining replica.
    ...        kubectl drain <Node_2 name> --delete-emptydir-data=true --force=true --grace-period=-1 --ignore-daemonsets=true
    ...    Then The Node_2 becomes cordoned.
    ...    And All pods on Node_2 are evicted except the replica instance manager pod.
    ...        kubectl get pods --field-selector spec.nodeName=<Node_2 name> -o wide -n longhorn-system
    ...    And The last healthy replica exists on the Node_2.
    Given Disable node 0 scheduling
    And Set setting node-drain-policy to block-if-contains-last-replica
    And Given Create volume 0 with    size=5Gi    numberOfReplicas=2    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 1
    And Wait for volume 0 healthy
    And Write data to volume 0
    And Detach volume 0 from attached node
    And Wait for volume 0 detached
    And Power off node 1

    When Force drain node 2 and expect failure
    And Check instance-manager pod is running on node 2
    And Check volume 0 replica on node 2 exist

Setting Allow Node Drain with the Last Healthy Replica protects the last healthy replica with Pod Disruption Budget (PDB)
    [Documentation]    Setting Allow Node Drain with the Last Healthy Replica protects the last healthy replica with Pod Disruption Budget (PDB) 
    ...    Related Issue:
    ...    - https://github.com/longhorn/longhorn/issues/2237
    ...
    ...    Given Longhorn with 2 nodes cluster: Node_1, Node_2
    ...    And Update the Node Drain Policy setting to block-if-contains-last-replica and confirm with following command:
    ...        kubectl get settings.longhorn.io/node-drain-policy -n longhorn-system
    ...    And Create a 5Gi detached volume with 2 replicas.
    ...    And Stop Node_1 that contains one of the replicas.
    ...    And Drain Node_2 so that all pods on Node_2 are evicted, but the replica instance manager pod is still on Node_2 because it is protected by PDB.
    ...        kubectl drain <Node_2 name> --delete-emptydir-data=true --force=true --grace-period=-1 --ignore-daemonsets=true
    ...    And Update the Node Drain Policy setting to always-allow and confirm with following command:
    ...        kubectl get settings.longhorn.io/node-drain-policy -n longhorn-system
    ...    Then The pod longhorn-system/instance-manager-r-xxxxxxxx will be evicted successfully and the following command can be used to ensure that only daemonset pods such as engine-image, longhorn-csi-plugin and longhorn-manager daemonset pods are running on Node_2:
    ...        kubectl get pods --field-selector spec.nodeName=<Node_2 name> -o wide -n longhorn-system
    ...    And The PDB will be deleted and can be verified with the following command:
    ...        kubectl get pdb <replica name, e.g., instance-manager-r-xxxxxxxx> -n longhorn-system
    Given Disable node 0 scheduling
    And Set setting node-drain-policy to block-if-contains-last-replica
    And Given Create volume 0 with    size=5Gi    numberOfReplicas=2        dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 1
    And Wait for volume 0 healthy
    And Write data to volume 0
    And Detach volume 0 from attached node
    And Wait for volume 0 detached
    And Power off node 1

    When Force drain node 2 and expect failure
    And Check instance-manager pod is running on node 2

    When Set setting node-drain-policy to always-allow
    And Force drain node 2 and expect success
    And Check PDB not exist    instance_manger=${instance_manager_name}
