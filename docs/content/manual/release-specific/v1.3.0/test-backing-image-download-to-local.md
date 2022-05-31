---
title: Test backing image download to local 
---

### Test step
1. Create and attach a volume (recommended volume size > 1Gi).
2. Write some data into the file then calculate the SHA512 checksum of the volume block device. 
3. Create a backing image from the above volume. And wait for the 1st backing image file ready.
4. Download the backing image to local via UI (Clicking button `Download` in `Operation` list of the backing image).
   => Verify the downloaded file checksum is the same as the volume checksum & the backing image current checksum (when `Exported Backing Image Type` is raw).
5. Create and attach the volume with the backing image. Wait for the attachment complete.
6. Re-download the backing image to local. => Verify the downloaded file checksum still matches.

---
GitHub Issue: https://github.com/longhorn/longhorn/issues/3155