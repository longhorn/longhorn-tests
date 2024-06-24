---
title: HA Volume Migration
---

## Basic instructions

1. Deploy a migratable StorageClass. E.g.:

```yaml
kind: StorageClass
apiVersion: storage.k8s.io/v1
metadata:
  name: test-sc
provisioner: driver.longhorn.io
allowVolumeExpansion: true
parameters:
  numberOfReplicas: "3"
  migratable: "true"
```

2. Create a migratable Volume. E.g.:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-pvc
  namespace: default
spec:
  accessModes:
    - ReadWriteMany
  volumeMode: Block
  storageClassName: test-sc
  resources:
    requests:
      storage: 1Gi
```

3. Attach the volume to a node and wait for it to become running. E.g.:

```yaml
apiVersion: storage.k8s.io/v1
kind: VolumeAttachment
metadata:
  name: test-va-1
spec:
  attacher: driver.longhorn.io
  nodeName: <old_node>
  source:
    persistentVolumeName: <volume_name>
```

4. Write some data into the volume.
5. Start the migration by attaching the volume to a second node.

```yaml
apiVersion: storage.k8s.io/v1
kind: VolumeAttachment
metadata:
  name: test-va-2
spec:
  attacher: driver.longhorn.io
  nodeName: <new_node>
  source:
    persistentVolumeName: <volume_name>
```

4. Trigger the scenarios described below with commands like the:

```bash
# Attempt to confirm the migration by detaching from <old_node>.
kubectl -n longhorn-system delete -f va-1.yaml

# Attempt to roll back the migration by detaching from <new_node>.
kubectl -n longhorn-system delete -f va-2.yaml

# Check the migration status of the volume.
kubectl -n longhorn-system get volume -oyaml | grep -i nodeid

# View migration related logs.
kubetail -n longhorn-system -l 'app in (longhorn-manager,longhorn-csi-plugin)'

# Watch volume to check if it becomes detached or faulted.
kubectl -n longhorn-system get volume -oyaml -w | grep -e state -e robustness
```

5. Before a test, verify the volume migration is ready. Logs should indicate "Volume migration engine is ready", and:

```
kubectl -n longhorn-system get volume -oyaml | grep -i nodeid
    migrationNodeID: eweber-v126-worker-9c1451b4-6464j
    nodeID: eweber-v126-worker-9c1451b4-kgxdq
    currentMigrationNodeID: eweber-v126-worker-9c1451b4-6464j
    currentNodeID: eweber-v126-worker-9c1451b4-kgxdq
    pendingNodeID: ""
```

## Scenarios

### 1. New engine crash

Crash the engine on the migration node by killing its instance-manager pod.

#### 1.1. Confirmation immediately after crash

Migration engine and replicas are recreated. Then, confirmation succeeds.

```bash
kl delete --wait=false pod instance-manager-ea5f8778d6c99e747289ff09c322d75a && sleep 0.5 && k delete -f va-1.yaml
# OR
kl delete --wait=false pod instance-manager-ea5f8778d6c99e747289ff09c322d75a && sleep 1 && k delete -f va-1.yaml
```

- "Waiting to confirm migration until migration engine is ready"
- "Confirming migration"
- No detachment
- New engine and replicas

#### 1.2. Confirmation immediately before crash

Confirmation succeeds. Then, the volume detaches from and reattaches to the new node.

```bash
k delete --wait=false -f va-1.yaml && sleep 0.5 && kl delete pod instance-manager-ea5f8778d6c99e747289ff09c322d75a
# OR
k delete --wait=false -f va-1.yaml && sleep 1 && kl delete pod instance-manager-ea5f8778d6c99e747289ff09c322d75a
```

- "Confirming migration"
- "...selected to detach from <new>"
- "...selected to attach to <new>"
- New engine and replicas

#### 1.3. Rollback immediately before or after crash

Rollback succeeds.

```bash
kl delete --wait=false pod instance-manager-ea5f8778d6c99e747289ff09c322d75a && sleep 0.5 && k delete -f va-2.yaml
# OR
kl delete --wait=false pod instance-manager-ea5f8778d6c99e747289ff09c322d75a && sleep 1 && k delete -f va-2.yaml
# OR
k delete --wait=false -f va-2.yaml && sleep 0.5 && kl delete pod instance-manager-ea5f8778d6c99e747289ff09c322d75a
# OR
k delete --wait=false -f va-2.yaml && sleep 1 && kl delete pod instance-manager-ea5f8778d6c99e747289ff09c322d75a
```

- "Rolling back migration"
- No detachment
- Same engine and replicas

### 2. Old engine crash

Crash the engine on the old node by killing its instance-manager pod.

#### 2.1 No immediate confirmation or rollback

The volume completely detaches and remains detached. Logs indicate next steps. Deleting either of the two
VolumeAttachments gets the volume unstuck.

```bash
kl delete pod instance-manager-699da83c0e9d22726e667344227e096b
```

- "...selected to detach from <old>"
- "Cancelling migration for detached volume..."
- MigrationFailed event
- "Volume migration between <old> and <new> failed; detach volume from extra node to resume"

```
kubectl -n longhorn-system get volume -oyaml | grep -i nodeid
    migrationNodeID: ""
    nodeID: ""
    currentMigrationNodeID: ""
    currentNodeID: ""
    pendingNodeID: ""
```

```bash
kl delete -f va-2.yaml
```

```
kubectl -n longhorn-system get volume -oyaml | grep -i nodeid
    migrationNodeID: ""
    nodeID: eweber-v126-worker-9c1451b4-kgxdq
    currentMigrationNodeID: ""
    currentNodeID: eweber-v126-worker-9c1451b4-kgxdq
    pendingNodeID: ""
```

#### 2.2 Confirmation immediately after crash

The volume automatically detaches from the old node. Then, it reattaches to the new node.

```bash
kl delete --wait=false pod instance-manager-699da83c0e9d22726e667344227e096b && sleep 0.5 && k delete -f va-1.yaml
# OR
kl delete --wait=false pod instance-manager-699da83c0e9d22726e667344227e096b && sleep 1 && k delete -f va-1.yaml
```

- "...selected to detach from <old>"
- "Cancelling migration for detached volume..."
- MigrationFailed event
- "...selected to attach to <new>"
- Same engine and replicas

#### 2.3 Confirmation immediately before crash

Confirmation succeeds.

```bash
k delete --wait=false -f va-1.yaml && sleep 0.5 && kl delete pod instance-manager-699da83c0e9d22726e667344227e096b
# OR
k delete --wait=false -f va-1.yaml && sleep 1 && kl delete pod instance-manager-699da83c0e9d22726e667344227e096b
```

- "Confirming migration..."
- No detachment
- New engine and replicas

#### 2.4 Rollback immediately after crash

The volume automatically detaches from the old node. Then, it reattaches to the new node.

```bash
kl delete --wait=false pod instance-manager-699da83c0e9d22726e667344227e096b && sleep 0.5 && k delete -f va-2.yaml
kl delete --wait=false pod instance-manager-699da83c0e9d22726e667344227e096b && sleep 1 && k delete -f va-2.yaml
```

- "...selected to detach from <old>"
- "Cancelling migration for detached volume..."
- MigrationFailed event
- "...selected to attach to <old>"
- Same engine and replicas

#### 2.5 Rollback immediately before crash

Confirmation succeeds. Then, the volume detaches from and reattaches to the old node.

```bash
k delete --wait=false -f va-2.yaml && sleep 0.5 && kl delete pod instance-manager-699da83c0e9d22726e667344227e096b
# OR
k delete --wait=false -f va-2.yaml && sleep 1 && kl delete pod instance-manager-699da83c0e9d22726e667344227e096b
```

- "Rolling back migration"
- "...selected to detach from <old>"
- "...selected to attach to <old>"
- Same engine and replicas (rolled back)

### 3. Single replica crash

Crash the replica on a node that is neither the old or migration node by cordoning the node and killing its
instance-manager pod.

#### 3.1 Degraded before migration and confirmation

Migration starts while the volume is degraded. Confirmation succeeds.

```bash
k cordon eweber-v126-worker-9c1451b4-rw5hf
kl delete pod instance-manager-6852914a55e4566d3ddea43529df22e0
k delete -f va-1.yaml
```

- "Confirming migration"
- No detachment
- New engine and replicas

#### 3.2 Degraded before migration and rollback

Migration starts while the volume is degraded. Rollback succeeds.

```bash
k cordon eweber-v126-worker-9c1451b4-rw5hf
kl delete pod instance-manager-6852914a55e4566d3ddea43529df22e0

k apply -f va-1.yaml
k apply -f va-2.yaml
k delete -f va-2.yaml
```

- "Rolling back migration"
- No detachment
- Same engine and replicas

#### 3.3 Degraded between migration start and confirmation

Confirmation succeeds.

```bash
k apply -f va-1.yaml
k apply -f va-2.yaml

k cordon eweber-v126-worker-9c1451b4-rw5hf
kl delete pod instance-manager-6852914a55e4566d3ddea43529df22e0

k delete -f va-1.yaml
```

- "Confirming migration"
- New engine and replicas

#### 3.4 Degraded between migration start and rollback

Rollback succeeds.

```bash
k apply -f va-1.yaml
k apply -f va-2.yaml

k cordon eweber-v126-worker-9c1451b4-rw5hf
kl delete pod instance-manager-6852914a55e4566d3ddea43529df22e0

k delete -f va-2.yaml
```

- Rolling back migration
- Same engine and replicas

### 4. Attempt to attach to three nodes

The third attachment fails.

```bash
kl apply -f va-1.yaml
kl apply -f va-2.yaml
kl apply -f va-3.yaml
```

- test-va-1 attached
- test-va-2 attached
- test-va-3 not attached
- "...cannot attach migratable volume to more than two nodes..."

### 5. New engine node down

1. Hard shut down the node running the migration engine.
2. Wait until Kubernetes recognizes the node is down. (This is IMPORTANT! Otherwise, it is a different test case.)
3. Attempt a confirmation or rollback.

#### 5.1 Confirmation

The volume is allowed to detach from the old node (special logic in code). It attempts to attach to cleanly attach to
the migration node, but is stuck until it comes back.

- "Waiting to confirm migration until migration engine is ready"
- "Detaching volume for attempted migration to down node"
- "...selected to attach to <new>"
- Same engine and replicas
- Stuck in attaching waiting for node to come back

```
kubectl -n longhorn-system get volume -oyaml | grep -i nodeid
    migrationNodeID: ""
    nodeID: eweber-v126-worker-9c1451b4-6464j
    currentMigrationNodeID: ""
    currentNodeID: ""
    pendingNodeID: ""
```

#### 5.2 Rollback

Rollback succeeds.

- "Rolling back migration"
- No detachment
- Same engine and replicas

### 6. Old engine node down

1. Hard shut down the node running the old engine.
2. Wait until Kubernetes recognizes the node is down. (This is IMPORTANT! Otherwise, it is a different test case.)
3. Attempt a confirmation or rollback.

#### 6.1 Confirmation

The migration is stuck until the Kubernetes pod eviction controller decides to terminate the instance-manager pod that
was running on the old node. Then, Longhorn detaches the volume and cleanly reattaches it to the migration node.

- "Waiting to confirm migration..." (new engine crashes when old one does)
- Eventually...
- "...selected to detach from <old>"
- "Cancelling migration for detached volume..."
- "...selected to attach to <new>"
- Same engine and replicas

#### 6.2 Rollback

The migration is stuck until the Kubernetes pod eviction controller decides to terminate the instance-manager pod that
was running on the old node. Then, Longhorn detaches the volume and attempts to cleanly reattach it to the old node, but
it is stuck until the node comes back.

- "Rolling back migration"
- Stuck in attached with engine and one replica unknown
- Eventually...
- "...selected to detach from <old>"
- "...selected to attach to <old>"
- Stuck in attaching waiting for node to come back
- Same engine and replicas
