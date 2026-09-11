# Longhorn e2e tests

### Requirement

1. A Kubernetes cluster with 3 worker nodes.
   - And control node(s) with following taint:
      - `node-role.kubernetes.io/control-plane:NoSchedule`
1. Longhorn system has already been successfully deployed in the cluster.
1. Run the environment check script to check if each node in the cluster fulfills the requirements:
```
curl -sSfL https://raw.githubusercontent.com/longhorn/longhorn/master/scripts/environment_check.sh | bash
```

### Run the test

1. Deploy all backupstore servers (including `NFS` server and `Minio` as s3 server, `CIFS` and `Azurite` server) for test purposes.

   For Azurite, there are some manual steps need to be done after manifest deployed(https://github.com/longhorn/longhorn-tests/wiki/Setup-Azurite-Backupstore-For-Testing).
```
kubectl create -f https://raw.githubusercontent.com/longhorn/longhorn-tests/master/manager/integration/deploy/backupstores/minio-backupstore.yaml \
               -f https://raw.githubusercontent.com/longhorn/longhorn-tests/master/manager/integration/deploy/backupstores/nfs-backupstore.yaml \
               -f https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/backupstores/cifs-backupstore.yaml \
               -f https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/backupstores/azurite-backupstore.yaml
```

1. Expose Longhorn API:
```
# for example, using nodeport:
kubectl expose --type=NodePort deployment longhorn-ui -n longhorn-system --port 8000 --name longhorn-ui-nodeport --overrides '{ "apiVersion": "v1","spec":{"ports": [{"port":8000,"protocol":"TCP","targetPort":8000,"nodePort":30000}]}}'
# or using port-forward:
kubectl port-forward services/longhorn-frontend 8080:http -n longhorn-system
```

1. Export environment variable `KUBECONFIG`:
```
export KUBECONFIG=/path/to/your/kubeconfig.yaml
```

1. Reconcile the adaptive test NetworkPolicy so Robot test pods in the `default` namespace can access the `longhorn-manager` API only when Longhorn internal NetworkPolicies are present. The NetworkPolicy helper requires `yq` when it applies policies:
```
# from the longhorn-tests repository root
./pipelines/utilities/create_network_policies.sh setup_longhorn_manager_networkpolicy
```

1. Export environment variable `LONGHORN_CLIENT_URL`:
```
# for example, if it's exposed by nodeport:
export LONGHORN_CLIENT_URL=http://node-public-ip:30000
# or exposed by port-forward:
export LONGHORN_CLIENT_URL=http://localhost:8080
```

1. To run backup related test cases, export `LONGHORN_BACKUPSTORE` and `LONGHORN_BACKUPSTORE_POLL_INTERVAL` environment variables:

```
export LONGHORN_BACKUPSTORE='s3://backupbucket@us-east-1/backupstore$minio-secret'
export LONGHORN_BACKUPSTORE_POLL_INTERVAL=30s
```

1. To run node shutdown/reboot related test cases, export `HOST_PROVIDER` environment variable and generate :

```
export HOST_PROVIDER=aws
terraform output -raw instance_mapping | jq 'map({(.name | split(".")[0]): .id}) | add' | jq -s add > /tmp/instance_mapping
# cat /tmp/instance_mapping
# {
#   "ip-10-0-1-30": "i-03f2d24bbb973f52d",
#   "ip-10-0-1-190": "i-08338a75afa61dbba",
#   "ip-10-0-1-183": "i-002c2b23fb08cc00b",
#   "ip-10-0-1-37": "i-09c6c65c9602193c4"
# }
```

1. To determine the block device path for v2 volumes, export `HOST_PROVIDER` and `ARCH` environment variables:

```
export HOST_PROVIDER=aws
export ARCH=amd64
```

   While using `HOST_PROVIDER=vagrant`:

```
export VAGRANT_CWD=/path/to/vagrant/working/dir
```

   And all exported [Vagrant environment variables](https://developer.hashicorp.com/vagrant/docs/other/environmental-variables) are supported.

1. To run upgrade/uninstallation related test cases, export the following environment variables so the test code knows how to re-install Longhorn after the test cases are completed:

```
cd e2e
cp -r ../pipelines/ ./

export LONGHORN_INSTALL_METHOD=manifest
export LONGHORN_REPO_BRANCH=master
export LONGHORN_STABLE_VERSION=v1.8.1
export LONGHORN_TRANSIENT_VERSION=v1.8.2
export LONGHORN_REPO_URI=https://github.com/longhorn/longhorn.git
export CUSTOM_LONGHORN_MANAGER_IMAGE=longhornio/longhorn-manager:master-head
export CUSTOM_LONGHORN_ENGINE_IMAGE=longhornio/longhorn-engine:master-head
export CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE=longhornio/longhorn-instance-manager:master-head
export CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE=longhornio/longhorn-share-manager:master-head
export CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE=longhornio/backing-image-manager:master-head
export LONGHORN_STABLE_VERSION=master-head
```

1. To run kubelet restart related test cases, export the following environment variable so the test code knows how the kubernetes distro is using(support value: k3s, rke2):

```
export K8S_DISTRO=k3s
```

1. Prepare test environment and run the test:
```
cd e2e
python -m venv .
source bin/activate
pip install -r requirements.txt

# to run all the test cases, simply execute:
./run.sh

# to run all the test cases in test_basic.robot for v2 data engine, simply execute:
./run.sh -s test_basic -v DATA_ENGINE:v2

# to run all regression test cases for v2 data engine, simply execute:
./run.sh -i "regression" -v DATA_ENGINE:v2

# to specify the test case you'd like to run, use "-t" option:
./run.sh -t "Reboot Volume Node While Workload Heavy Writing"

# to specify the LOOP_COUNT or any other test variables, use "-v" option:
./run.sh -t "Reboot Volume Node While Workload Heavy Writing" -v LOOP_COUNT:100 -v RETRY_COUNT:259200

# to specify which test suite you'd like to run, use "-s" option:
./run.sh -s "replica_rebuilding"

# to run test cases with a specific tag, use "-i" option:
./run.sh -i "coretest"

# to modify debug level, use "-L" option:
./run.sh -L DEBUG
```

Once the test completed, the test result can be found at /tmp/test-report folder.

### Test tags

Every test suite declares `Test Tags` in its `*** Settings ***` section, and individual test cases may add
more specific tags with `[Tags]`. Tags are how the CI pipelines and `./run.sh -i <tag>` / `-e <tag>` select
which test cases to run.

Conventions:

- Use lower-case and hyphens for new tags (`backing-image`, `node-reboot`), never underscores or spaces.
  A few existing tags (`engine_image`, `system_backup`, `support bundle`) do not follow this, but they are
  kept as they are so the CI job configurations referring to them keep working.
- Every suite must carry at least one *suite* tag (`regression` or `negative`) plus one *feature area* tag.
- Put `[Tags]` **before** `[Documentation]`, otherwise the `...` continuation lines of the documentation are
  parsed as tags by Robot Framework.
- Only add an *issue* tag when the test exists to cover one specific upstream issue.

#### Suite tags

| Tag | Description |
| --- | --- |
| `regression` | Regression test cases under `tests/regression/`. |
| `negative` | Negative / resilience test cases under `tests/negative/`. |
| `coretest` | Subset of essential functionality test cases, used for quick verification. |
| `manual` | Converted from manual test cases; usually needs a special environment or takes long. |
| `pre-release` | Pre-release verification test cases. |
| `robot:skip` | Robot Framework built-in tag, the test case is skipped. |
| `skip` | Marks a test case that is not implemented yet and skips itself at runtime. |

#### Execution characteristic tags

| Tag | Description |
| --- | --- |
| `long-running` | Takes a long time (tens of minutes or more). |
| `large-size` | Uses large volumes / large amount of data. |
| `performance` | Performance oriented test case. |
| `stress` | CPU / memory / filesystem stress test cases. |
| `continuous-io` | Continuously writes IO for the whole test duration. |
| `resource-usage` | Records or compares Longhorn component resource usage. |
| `custom-setting` | Requires Longhorn to be installed with non-default settings. |
| `helm` | Requires Longhorn to be installed / upgraded by Helm. |
| `non-default-namespace` | Longhorn is installed in a namespace other than `longhorn-system`. |
| `environment` | Verifies the test environment / node prerequisites. |
| `appco` | SUSE Application Collection (appco) specific test cases. |

#### Data engine and volume tags

| Tag | Description |
| --- | --- |
| `v1` | v1 data engine specific. |
| `v2` | v2 data engine specific. |
| `block-disk` | Requires a raw block disk (v2 data engine). |
| `volume` | General volume behavior. |
| `basic` | Basic volume life cycle test cases. |
| `rwo` | ReadWriteOnce volume. |
| `rwx` | ReadWriteMany volume. |
| `rwx-fast-failover` | RWX volume fast failover feature. |
| `migratable-rwx` | Migratable RWX volume. |
| `block-volume` | Block mode volume. |
| `encrypted` | Encrypted volume. |
| `single-replica` | Volume with a single replica. |
| `faulted` | Faulted volume behavior. |
| `pvc` | PersistentVolumeClaim behavior. |
| `csi` | CSI driver behavior. |
| `csi-snapshotter` | CSI snapshotter / VolumeSnapshot behavior. |

#### Feature area tags

| Tag | Description |
| --- | --- |
| `backup` | Backup related. |
| `backup-restore` | Backup restoration. |
| `restore` | Volume restoration. |
| `dr-volume` | Disaster recovery volume. |
| `backing-image` | Backing image. |
| `system-backup` | System backup and restore. Note the suite itself is tagged `system_backup`. |
| `system-backup-recurring-job` | System backup created by a recurring job. |
| `recurring-job` | Recurring job. |
| `snapshot` | Volume snapshot. |
| `snapshot-purge` | Snapshot purge. |
| `snapshot-limit` | Maximum snapshot count. |
| `vm-snapshot` | VM (node) level snapshot. |
| `cloning` / `clone` | Volume / backing image cloning. |
| `linked-clone` | Linked clone (v2 data engine). |
| `expansion` | Volume expansion. |
| `migration` | Volume live migration. |
| `ha-migration` | Live migration under HA / failure scenarios. |
| `ha` | High availability behavior. |
| `replica` | Replica behavior. |
| `replica-rebuild` / `replica-rebuilding` | Replica rebuilding. |
| `offline-rebuilding` | Offline replica rebuilding. |
| `scheduling` | Replica scheduling. |
| `anti-affinity` | Replica / zone anti-affinity settings. |
| `auto-balance` | Replica auto balance. |
| `auto-salvage` | Volume auto salvage. |
| `zone` | Zone awareness. |
| `tagging` | Node / disk tag scheduling. |
| `disk` | Disk management. |
| `io-error` | Disk I/O error handling. |
| `orphan` | Orphaned replica / instance. |
| `setting` | Longhorn global settings. |
| `metric` | Longhorn metrics. |
| `support-bundle` | Support bundle. The existing test case also carries the legacy `support bundle` tag. |
| `storage-network` | Storage network. |
| `proxy` | HTTP proxy environment. |
| `component` | Longhorn component (deployment / daemonset) configuration. |
| `instance-manager` | Instance manager. |
| `sharemanager` | Share manager. |
| `engine-image` | Engine image related settings. The engine image suite itself is tagged `engine_image`. |
| `engine-upgrade` / `old-engine` | Engine live upgrade / volume running an old engine image. |
| `node-eviction` | Node eviction. |
| `cluster` | Whole cluster level operation. |

#### Upgrade and uninstallation tags

| Tag | Description |
| --- | --- |
| `upgrade` | Longhorn upgrade. |
| `2-stage-upgrade` | Two stage (stable -> transient -> target) Longhorn upgrade. |
| `kubernetes-upgrade` | Kubernetes cluster upgrade. |
| `uninstall` | Longhorn uninstallation. |

#### Disruption tags (mostly used by `tests/negative/`)

| Tag | Description |
| --- | --- |
| `node-reboot` / `reboot` | Node reboot. |
| `node-down` | Node power off. |
| `node-delete` | Node deletion. |
| `node-drain` | Node drain. |
| `service-restart` | Longhorn / Kubernetes service restart. |
| `kubelet-restart` | Kubelet restart or stop. |
| `network` / `network-disconnect` | Network disruption. |
| `reattach` | Volume reattachment. |

#### Issue tags

Tags named `longhorn-<issue number>` (`longhorn-8355`, `longhorn-9865`, `longhorn-10210`) mark test cases
that were added for a specific [longhorn/longhorn](https://github.com/longhorn/longhorn/issues) issue.

### Architecture

The e2e robot test framework includes 4 layers:

```
 ---------------------------------------------------------------------
|                                                                     |
|               tests/*.robot: Test Case Definition                   |
|                                                                     |
 ---------------------------------------------------------------------
|                                                                     |
|             keywords/*.resource: Keyword Definition                 |
|                                                                     |
 ---------------------------------------------------------------------
|                                                                     |
|              libs/keywords: Keyword Implementation                  |
|                                                                     |
 ---------------------------------------------------------------------
|                                                                     |
| libs/COMPONENT_NAME: Basic operations to manipulate each component  |
|                   (volume, replica, workload, node, etc.)           |
|                                                                     |
 ---------------------------------------------------------------------
```

 __* Each layer can only call functions from the next layer or the same layer. Skip-layer is strictly forbidden. For example, Keyword Definition layer can only call functions in Keyword Implementation layer or Keyword Definition layer, directly call functions in Basic operations layer is strictly forbidden.__
