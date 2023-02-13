## Best practices of testing features/issues

Longhorn has a lot of features and is versatile enough to offer various ways to do the same tasks/operations, in addition to that Longhorn is stable & resilient against involuntary factors and provides high availability; therefore we should keep the following in mind when testing any new features or potential problems. We can make sure that the testing includes every part of the feature and covers more impacted areas by adhering to the recommended practices listed below.

### 1. Read the LEP carefully.
Read the Longhorn enhancement proposal, understand the feature. Ask doubts and even log a bug if you think there is major issue in the design.

### 2. List the test cases for the feature and review the test plan in the LEP.
For QAs it is recommended to first list out the test cases they can think of and then review the test plan in the LEP.
Sometimes if we read test plan provided by the developer of the feature, we get biased with their opinion and might overlook possible edge cases.

### 3. Test data creation to test the feature.
Creating test data is important, so we should try to make sure that we are testing the feature on the resources/data created in every possible way Longhorn supports.
Remember that not every feature/issues will require below test data creation but that will depend on the nature of the feature.
We can test the feature by creating the data one by one first to verify the feature holds good for all and then together to verify feature works fine while handling multiple operations.  

#### Volumes
1. RWO volume created using Longhorn UI.
2. RWO volume using dynamic provisioning with storage class.
3. RWO volume attached with deployment, statefulSet workload.
4. RWX volume created using Longhorn UI.
5. RWX volume created using dynamic provisioning with storage class.
6. RWX volume is attached to daemonSet workload.

7. Volume with ext4 format.
8. Volume with xfs format.

9. Volume with backing image.
10. Encrypted volumes.

#### Backups and Restore
1. Backups on S3
2. Backups on NFS.

### 4. Testing feature with other operations running.
Testing the feature while other operations are in progress make sure that the feature doesn't interfere with running operations or become impacted by other features.
e.g. Online expansion feature: Have below operation running and then trigger online expansion.
1. Replica rebuilding
2. Disk/Replica eviction.
3. Backup/restoring of volume.
4. Live migration of volume.
5. Expansion of volume.

### 5. Trigger other operation while you're performing the feature operation.
This is tricky and similar to the point 4. If the feature involves a running operation we can trigger the below operation while the feature operation is running.
e.g. Online expansion feature: While online expansion is in progress, trigger the below operations.
1. Replica rebuilding
2. Disk/Replica eviction.
3. Backup/restoring of volume.
4. Live migration of volume.
5. Expansion of volume.

### 6. Testing the feature with combination of settings.
There are multiple settings available in Longhorn, we need to evaluate and enable/disable settings which might cause a different behavior for the feature. Below are few example
1. Data locality
2. Automatic salvage
3. Concurrent Automatic Engine Upgrade Per Node Limit
4. Replica Replenishment Wait Interval etc...

### 7. Interrupting the feature by internal factors.
Try to interrupt the feature operations by Longhorn internal factors like below.
1. Killing the replica instance manager pods.
2. Killing the engine instance manager pods.
3. Deleting the feature operation in middle.
4. Deleting the related CRDs.
5. Deleting the attached pod.
6. Engine not fully deployed.

### 8. Interrupting the feature by external factors.
Try to interrupt the feature operations by external factors like below.
1. Rebooting the node.
2. Power down the node for 10 min and then powering it on.
3. Deleting the node.
4. Disrupting the network of the node.
5. Kubelet restart.
6. Disk failure/deletion.


### 9. Testing the feature on an upgraded set up.
Create some data related to the feature on the previous version and upgrade the system. Now, verify the feature with those data.

### 10. Scalability of the feature.
Test the feature with more data. Like below 
1. Creating 50-100 volumes/backups and testing the feature with them.
2. Creating big volumes like 500 Gi and testing the feature with it.


Note: Depending on the nature of the feature or issue, the points mentioned above will apply. Therefore, you must evaluate and determine the requirements for each feature.
In general, it is strongly advised to test any feature with all types of data created from point 3 and also while doing an upgrade, sanity check, uninstallation.
