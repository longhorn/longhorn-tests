---
title: Test backing image
---

## Test upload
1. Prepare a large backing image file (make sure the size is greater than 1Gi and the uploading time is longer than 1 minute) in local.
2. Click the backing image creation button in UI, choose `Upload From Local`, select the file then start upload.
3. Wait for the initialization complete. Then the upload progress will be shown.
4. During the uploading, verify the corresponding backing image data source pod won't use too many CPU (50 ~ 200m) and memory(50 ~ 200Mi) resources.
5. Open another backing image UI page, the progress can be still found in the backing image detail page.
6. When the upload is in progress, refresh the UI page to interrupt the upload.
7. Verified that the upload failed without retry (typically the retry will happen after 1~2 minute). And there is a message indicates the failure.
8. Delete the failed one then restart the uploading by creating a new backing image.
9. Create and attach a volume with the backing image. Verify the data content is correct.
10. Do cleanup.

## Test CSI backing image
1. Create a valid backing image
2. Create a StorageClass, which use the same backing image name but different data source type/parameters.
3. Create a PVC with the StorageClass. 
   ==> The corresponding creation should fail. The longhorn-csi-plugin will repeatly print out error logs like this `existing backing image %v data source is different from the parameters in the creation request or StorageClass`.
4. Delete the PVC and the StorageClass.
5. Recreate a StorageClass in which the backing image fields match the existing backing image.
6. Create a PVC with the StorageClass.
   ==> The corresponding volume creation should succeed.
7. Delete the PVC and the backing image.
8. ReCreate a PVC with the StorageClass.
   ==> Longhorn will create a backing image then create the corresponding volume.
9. Do cleanup.

## Test backing image creation via YAML
1. Run 
    ```
    echo "
    apiVersion: longhorn.io/v1beta1
    kind: BackingImage
    metadata:
      name: bi-test
      namespace: longhorn-system
    spec:
      sourceType: download
      sourceParameters:
        url: https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
    " | kubectl -n longhorn-system apply -f -
    ```
2. Verify the backing image is created and ready for use.

Notice: It's better not to create a backing image with type `upload` via YAML. Otherwise, you need to find a way to send the upload HTTP request manually.
