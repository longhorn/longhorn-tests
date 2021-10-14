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

### Upload via Rancher URI
<sup>Related issue: [3129](https://github.com/longhorn/longhorn/issues/3129) with fix in Longhorn v1.3.0+</sup>
1. With Rancher v2.6.x create a cluster and install Longhorn
   - or import an existing cluster with Longhorn installed
2. Go into the cluster
3. Click Longhorn from the Rancher menu, the sidebar on the left
4. Click on the Longhorn app to open the UI
   - An example URL: <small>`https://rancer.server.domain/k8s/clusters/CLUSTER-ID/api/v1/namespaces/longhorn-system/services/http:longhorn-frontend:80/proxy/#/backingImage`</small>
5. Create a new backing image with **Upload From Local**
6. Verify the uploaded image matches its size or checksum

### Upload via Ingress Controller
<sup>Related issue: [2937](https://github.com/longhorn/longhorn/issues/2937) with fix in v1.2.0+</sup>
1. Install and create Ingress Loadbalancer with proper hostname configuration
   - On Rancher v2.6.0 Explorer > into Cluster > Service and Discovery > Ingresses
2. Access Longhorn UI with the hostname URL
3. Create a new backing image with **Upload From Local**
4. Verify the uploaded image matches its size or checksum

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
