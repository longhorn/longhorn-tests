# Generate test data script
Generate RWO/RWX workloads, write data into `/mnt/data/data` in workloads and record md5 to data.output.

# Usage
Modify config.yaml
```yaml
storage: 1Gi # Each volume size
storageClass: longhorn-test # Need to prepare your own storage class first
dataSizeInMb: 500
namespace: default # Needs to prepare first before run script
statefulSet: # Single RWO/RWX statefulset and its replica counts
  rwo:
    replicas: 1 
  rwx:
    replicas: 0
deployment: # Number of RWO/RWX deployments, replica of RWO fixed to 1
  rwo:
    pvCounts: 0 
  rwx:
    pvCounts: 1
    deploymentReplicas: 2 # Replica count of each RWX deployment 
```

# Generate test data
 `./run.sh`

# Cleanup workloads and PVC
`./clean.sh`

# Output(example)
`cat data.output`

Can see worklad name and md5sum of mount point file
```
test-data-rwx-statefulset-0
2bccd99c8e35ccab2cd7620a200bc3e1

test-data-rwx-statefulset-1
8f96c74b8b990ff11e98d478fc65f77b

test-data-rwo-deployment-1-7f99f8bf76-cqblb
91fc370c81957d12f01581f78e4bdeba

test-data-rwo-deployment-2-549d6cb995-gvc79
883c98d04e2c54c89f979b20d3fa277e
```
