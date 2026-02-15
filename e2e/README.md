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
export LONGHORN_BACKUPSTORE_POLL_INTERVAL=30
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
