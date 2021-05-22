---
title: Test backing image upload
---

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
