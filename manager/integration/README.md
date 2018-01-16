# Longhorn Manager tests

## Integration test

The tests are written in python using pytest and will be ran as a pod against an existing Longhorn system.

### Requirement
1. An existing Kubernetes cluster.
2. An deployed Longhorn system in the cluster.
3. No existing volume in the Longhorn system.

### Run the test
1. Deploy the NFS server for test purpose, acting as the backupstore
```
kubectl create -f integration/deploy/backupstore.yaml
```
2. Deploy the test script to the Kubernetes cluster.
```
kubectl create -f integration/deploy/test.yaml
```
3. Watch the result:
```
kubectl logs -f longhorn-test
```
4. Teardown the test
```
kubectl delete -f integration/deploy/test.yaml
```
5. Teardown the backupstore for testing
```
kubectl delete -f integration/deploy/backupstore.yaml
```

### Development
1. The testing codes are at `integration/tests`.
2. After updated the testing codes, use `integration/build-image.sh` to build a new Docker image for the test, then push the image to the Docker hub.
3. Update `integration/deploy/test.yaml` to point to the new test image.
4. Run the new test.
