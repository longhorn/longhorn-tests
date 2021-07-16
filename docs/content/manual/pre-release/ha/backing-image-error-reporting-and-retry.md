---
title: Backing Image Error Reporting and Retry
---

## Backing image with an invalid URL schema
1. Create a backing image via a invalid download URL. e.g., `httpsinvalid://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2`, `https://longhorn-backing-image.s3-us-west-1.amazonaws.invalid.com/parrot.raw`.
2. Wait for the download start. The backing image data source pod, which is used to download the file from the URL, should become `Failed` then be cleaned up immediately.
3. The corresponding and only entry in the disk file status should be `failed`. The error message in this entry should explain why the downloading or the pod becomes failed. 
4. Check if there is a backoff window for the downloading retry. The initial duration is 1 minute. The max interval is 5 minute. This can be verified by checking the timestamp of the error message or the logs in the longhorn manager pods.   

## Backing image with sync failure
1. Create a backing image. Then create and attach a volume using this backing image.
2. Exec into the host of a worker node. remove the content of the backing image work directory then set the directory as immutable. This operation should fail one file of the backing image as well as keeping failing the following sync retries.
    ```shell
    rm -r /var/lib/longhorn/backing-images/<backing image name>-<backing image UUID>/
    chattr +i /var/lib/longhorn/backing-images/<backing image name>-<backing image UUID>/
    ```
3. Monitor the backing image manager pod log. Verify the backoff works for the sync retry as well.
4. Unset the immutable flag for the backing image directory. Then the retry should succeed, and the volume should become `healthy` again after the backing image re-sync complete.
    ```shell
    chattr -i /var/lib/longhorn/backing-images/<backing image name>-<backing image UUID>/
    ```