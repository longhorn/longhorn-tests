# Longhorn e2e tests

### Requirement

1. A Kubernetes cluster with 3 worker nodes.
   - And control node(s) with following taints:
      - `node-role.kubernetes.io/master=true:NoExecute`
      - `node-role.kubernetes.io/master=true:NoSchedule` 
1. Longhorn system has already been successfully deployed in the cluster.
1. Run the environment check script to check if each node in the cluster fulfills the requirements:
```
curl -sSfL https://raw.githubusercontent.com/longhorn/longhorn/master/scripts/environment_check.sh | bash
```

### Run the test

1. Deploy all backupstore servers (including `NFS` server and `Minio` as s3 server) for test purposes.
```
kubectl create -f https://raw.githubusercontent.com/longhorn/longhorn-tests/master/manager/integration/deploy/backupstores/minio-backupstore.yaml \
               -f https://raw.githubusercontent.com/longhorn/longhorn-tests/master/manager/integration/deploy/backupstores/nfs-backupstore.yaml
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