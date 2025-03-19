---
title: Test Migrate v1beta1 To v1beta2
---

## Related issue
https://github.com/longhorn/longhorn/issues/10250

## Test Steps

**Given** A single-server K3s cluster
> Ref: https://docs.k3s.io/architecture?_highlight=single&_highlight=server#single-server-setup-with-an-embedded-db
> Example: https://github.com/k3s-io/vagrant-k3s

**And** Install necessary command line tools on master node
```bash
sudo zypper in jq sqlite3
sudo snap install kubectl --classic
```

**And** Longhorn v1.2.x installed

**And** Create a RWX volume
```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: longhorn-share
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 5Mi
  storageClassName: longhorn
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hello-world
  labels:
    app: hello-world
spec:
  replicas: 1
  selector:
    matchLabels:
      app: hello-world
  template:
    metadata:
      labels:
        app: hello-world
    spec:
      containers:
        - name: hello-world
          image: busybox
          command: ['sh', '-c', 'while true ; do now=$(date +%s) ; echo $now ; echo $now >>/mnt/data/share/log || echo $now >/mnt/data/share/log ; ls -l /mnt/data/share/log ; sleep 1 ; done']
          volumeMounts:
            - mountPath: /mnt/data/share
              name: share
      volumes:
        - name: share
          persistentVolumeClaim:
            claimName: longhorn-share
EOF
```

**And** Create a backup target
> Ref: https://longhorn.io/docs/1.9.0/snapshots-and-backups/backup-and-restore/set-backup-target/

**And** Create a recurring job to backup the volume
> Ref: https://longhorn.io/docs/1.9.0/snapshots-and-backups/scheduling-backups-and-snapshots/

**And** Create a backing image from the volume
> Ref: https://longhorn.io/docs/1.9.0/advanced-resources/backing-image/backing-image/#create-a-v1-backing-image-using-yaml

**When** Upgrade Longhorn to v1.9.x through valid upgrade path
> 1.2.x -> 1.3.x -> 1.4.x -> 1.5.x -> 1.6.x -> 1.7.x -> 1.8.x -> 1.9.x (master)
> Ref: https://longhorn.io/docs/1.9.0/deploy/upgrade/

**And** Wait until Longhorn components are running

**Then** Log in to K3s master node with root permission

**And** Check storage version of Longhorn node object is `v1beta2`
```bash
sqlite3 /var/lib/rancher/k3s/server/db/state.db <<SQL | jq -c '. | {"apiVersion": .apiVersion, "kind": .kind, "name": .metadata.name}'
SELECT kine.value
FROM kine
JOIN (
  SELECT name, MAX(id) AS max_id
  FROM kine
  WHERE name
  LIKE '/registry/longhorn.io/nodes/longhorn-system/%'
  GROUP BY name
) k
ON kine.name = k.name AND kine.id = k.max_id
SQL
```

**And** Check storage version of Longhorn instance manager object is `v1beta2`
```bash
sqlite3 /var/lib/rancher/k3s/server/db/state.db <<SQL | jq -c '. | {"apiVersion": .apiVersion, "kind": .kind, "name": .metadata.name}'
SELECT kine.value
FROM kine
JOIN (
  SELECT name, MAX(id) AS max_id
  FROM kine
  WHERE name
  LIKE '/registry/longhorn.io/instancemanagers/longhorn-system/%'
  GROUP BY name
) k
ON kine.name = k.name AND kine.id = k.max_id
SQL
```

**And** Check storage version of Longhorn volume object is `v1beta2`
```bash
sqlite3 /var/lib/rancher/k3s/server/db/state.db <<SQL | jq -c '. | {"apiVersion": .apiVersion, "kind": .kind, "name": .metadata.name}'
SELECT kine.value
FROM kine
JOIN (
  SELECT name, MAX(id) AS max_id
  FROM kine
  WHERE name
  LIKE '/registry/longhorn.io/volumes/longhorn-system/%'
  GROUP BY name
) k
ON kine.name = k.name AND kine.id = k.max_id
SQL
```

**And** Check storage version of Longhorn engine object is `v1beta2`
```bash
sqlite3 /var/lib/rancher/k3s/server/db/state.db <<SQL | jq -c '. | {"apiVersion": .apiVersion, "kind": .kind, "name": .metadata.name}'
SELECT kine.value
FROM kine
JOIN (
  SELECT name, MAX(id) AS max_id
  FROM kine
  WHERE name
  LIKE '/registry/longhorn.io/engines/longhorn-system/%'
  GROUP BY name
) k
ON kine.name = k.name AND kine.id = k.max_id
SQL
```

**And** Check storage version of Longhorn replica object is `v1beta2` 
```bash
sqlite3 /var/lib/rancher/k3s/server/db/state.db <<SQL | jq -c '. | {"apiVersion": .apiVersion, "kind": .kind, "name": .metadata.name}'
SELECT kine.value
FROM kine
JOIN (
  SELECT name, MAX(id) AS max_id
  FROM kine
  WHERE name
  LIKE '/registry/longhorn.io/replicas/longhorn-system/%'
  GROUP BY name
) k
ON kine.name = k.name AND kine.id = k.max_id
SQL
```

**And** Check storage version of Longhorn share manager object is `v1beta2` 
```bash
sqlite3 /var/lib/rancher/k3s/server/db/state.db <<SQL | jq -c '. | {"apiVersion": .apiVersion, "kind": .kind, "name": .metadata.name}'
SELECT kine.value
FROM kine
JOIN (
  SELECT name, MAX(id) AS max_id
  FROM kine
  WHERE name
  LIKE '/registry/longhorn.io/sharemanagers/longhorn-system/%'
  GROUP BY name
) k
ON kine.name = k.name AND kine.id = k.max_id
SQL
```

**And** Check storage version of Longhorn backup target object is `v1beta2`
```bash
sqlite3 /var/lib/rancher/k3s/server/db/state.db <<SQL | jq -c '. | {"apiVersion": .apiVersion, "kind": .kind, "name": .metadata.name}'
SELECT kine.value
FROM kine
JOIN (
  SELECT name, MAX(id) AS max_id
  FROM kine
  WHERE name
  LIKE '/registry/longhorn.io/backuptargets/longhorn-system/%'
  GROUP BY name
) k
ON kine.name = k.name AND kine.id = k.max_id
SQL
```

**And** Check storage version of Longhorn setting object is `v1beta2` 
```bash
sqlite3 /var/lib/rancher/k3s/server/db/state.db <<SQL | jq -c '. | {"apiVersion": .apiVersion, "kind": .kind, "name": .metadata.name}'
SELECT kine.value
FROM kine
JOIN (
  SELECT name, MAX(id) AS max_id
  FROM kine
  WHERE name
  LIKE '/registry/longhorn.io/settings/longhorn-system/%'
  GROUP BY name
) k
ON kine.name = k.name AND kine.id = k.max_id
SQL
```

**And** Check storage version of Longhorn recurring job object is `v1beta2`
```bash
sqlite3 /var/lib/rancher/k3s/server/db/state.db <<SQL | jq -c '. | {"apiVersion": .apiVersion, "kind": .kind, "name": .metadata.name}'
SELECT kine.value
FROM kine
JOIN (
  SELECT name, MAX(id) AS max_id
  FROM kine
  WHERE name
  LIKE '/registry/longhorn.io/recurringjobs/longhorn-system/%'
  GROUP BY name
) k
ON kine.name = k.name AND kine.id = k.max_id
SQL
```

**And** Check storage version of Longhorn backups object is `v1beta2` 
```bash
sqlite3 /var/lib/rancher/k3s/server/db/state.db <<SQL | jq -c '. | {"apiVersion": .apiVersion, "kind": .kind, "name": .metadata.name}'
SELECT kine.value
FROM kine
JOIN (
  SELECT name, MAX(id) AS max_id
  FROM kine
  WHERE name
  LIKE '/registry/longhorn.io/backups/longhorn-system/%'
  GROUP BY name
) k
ON kine.name = k.name AND kine.id = k.max_id
SQL
```

**And** Check storage version of Longhorn backing image object is `v1beta2`
```bash
sqlite3 /var/lib/rancher/k3s/server/db/state.db <<SQL | jq -c '. | {"apiVersion": .apiVersion, "kind": .kind, "name": .metadata.name}'
SELECT kine.value
FROM kine
JOIN (
  SELECT name, MAX(id) AS max_id
  FROM kine
  WHERE name
  LIKE '/registry/longhorn.io/backingimages/longhorn-system/%'
  GROUP BY name
) k
ON kine.name = k.name AND kine.id = k.max_id
SQL
```

**And** Check storage version of Longhorn backing image data source object is `v1beta2`
```bash
sqlite3 /var/lib/rancher/k3s/server/db/state.db <<SQL | jq -c '. | {"apiVersion": .apiVersion, "kind": .kind, "name": .metadata.name}'
SELECT kine.value
FROM kine
JOIN (
  SELECT name, MAX(id) AS max_id
  FROM kine
  WHERE name
  LIKE '/registry/longhorn.io/backingimagedatasources/longhorn-system/%'
  GROUP BY name
) k
ON kine.name = k.name AND kine.id = k.max_id
SQL
```

**And** Check storage version of Longhorn backing image manager object is `v1beta2`
```bash
sqlite3 /var/lib/rancher/k3s/server/db/state.db <<SQL | jq -c '. | {"apiVersion": .apiVersion, "kind": .kind, "name": .metadata.name}'
SELECT kine.value
FROM kine
JOIN (
  SELECT name, MAX(id) AS max_id
  FROM kine
  WHERE name
  LIKE '/registry/longhorn.io/backingimagemanagers/longhorn-system/%'
  GROUP BY name
) k
ON kine.name = k.name AND kine.id = k.max_id
SQL
```
