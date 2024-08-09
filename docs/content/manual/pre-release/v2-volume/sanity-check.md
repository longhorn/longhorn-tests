---
title: v2 volume sanity check
---
## Related doc:
https://longhorn.io/docs/1.7.0/v2-data-engine/features/

## Tests Prerequisite

- Load the kernel modules on the each Longhorn node
  ```
  modprobe vfio_pci
  modprobe uio_pci_generic
  ```

### Test Items

#### 1. Support both AMD64 and AMD64
#### 2. Volume creation, attachment, detachment and deletion
#### 3. [Block disk management](https://github.com/longhorn/longhorn/issues/7672)
#### 4. [Orphaned replica management](https://github.com/longhorn/longhorn/issues/5827)
##### Creating a v2 Orphan Replica in Longhorn
1. **Execute the `go-spdk-helper` Command in the Instance Manager Pod**:
   - Use the following `kubectl` command to execute the `go-spdk-helper` tool directly within the specified instance manager pod. This command will create a new logical volume (LVOL) in the desired logical volume store (LVSTORE).
   - Command syntax:
     ```bash
     kubectl -n longhorn-system exec -it <instance-manager-pod-name> -- /bin/bash -c "go-spdk-helper lvol create --lvs-name <DISK_NAME> --lvol-name <LVOL_NAME> --size <LVOL_SIZE_IN_MIB>"
     ```
   - Replace the placeholders with your specific values:
     - `<instance-manager-pod-name>`: The name of your instance manager pod.
     - `<LVSTORE_NAME>`: The name of the volume where the replica will be created.
     - `<DISK_NAME>`: The name for the disk on the node.
     - `<LVOL_SIZE_IN_MIB>`: The size of the logical volume in MiB.

2. **Example**:
   - Here’s an example where an LVOL named `test001` is created in the LVSTORE `disk-2` with a size of `12400` MiB:
     ```bash
     kubectl -n longhorn-system exec -it instance-manager-cddd0dac94705fc3e267c2e157224257 -- /bin/bash -c "go-spdk-helper lvol create --lvs-name disk-2 --lvol-name test001 --size 12400"
     ```

3. **Verify the Creation**:
   - After executing the command, you should receive a JSON output similar to the following:
     ```json
     {
         "alias": "disk-2/test001",
         "uuid": "57666291-2516-4140-af6d-cc086c8ae98c"
     }
     ```
   - This output confirms that the LVOL was successfully created with the specified alias and UUID.

#### 5. Snapshot creation, deletion and reversion
#### 6. Volume backup and restoration
#### 7. [Selective v2 Data Engine activation](https://github.com/longhorn/longhorn/issues/7015)
#### 8. Upgrade Longhorn from previous version with v2 volume
#### 9. [v2 volume live upgrade for data plane](https://github.com/longhorn/longhorn/issues/6001)
   > **Note:**
   > 
   > In this item, it should be excluded.  
   >
   > Ref: https://github.com/longhorn/longhorn/issues/6001#issuecomment-2272532533
#### 10. [Filesystem trim](https://github.com/longhorn/longhorn/issues/7534)
#### 11. [Replica online rebuilding](https://github.com/longhorn/longhorn/issues/7199)