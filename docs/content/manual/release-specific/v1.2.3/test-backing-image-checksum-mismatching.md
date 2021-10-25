---
title: Test backing image checksum mismatching 
---

### Test step
1. Modify setting `Backing Image Recovery Wait Interval` to a shorter value so that the backing image will start auto recovery eariler.
2. Create a backing image file with type `Download From URL`.
3. Launch a volume using the backing image file so that there are 2 disk records for the backing image.
4. Modify one disk file for the backing image and make sure the file size is not changed. This will lead to data inconsistency/corruption later. e.g.,
```bash
root@shuo-cluster-worker-2:/# echo test > /var/lib/longhorn/backing-images/bi-test-5cea928b/backing 
root@shuo-cluster-worker-2:/# truncate -s 500M /var/lib/longhorn/backing-images/bi-test-5cea928b/backing
```
5. Remove another disk file then crash backing image manager processes for **both** files **immediately and simultaneously**. e.g.
```bash
root@shuo-cluster-worker-2:/var/lib/longhorn/backing-images# ps aux | grep backing
root      577081  0.1  0.2 1454408 20740 ?       SLsl 10:00   0:06 backing-image-manager --debug daemon --listen 0.0.0.0:8000
root      650943  1.5  0.8 745556 71096 ?        SLsl 11:11   0:01 longhorn-manager -d daemon --engine-image longhornio/longhorn-engine:master-head --instance-manager-image longhornio/longhorn-instance-manager:v1_20210731 --share-manager-image longhornio/longhorn-share-manager:v1_20211020 --backing-image-manager-image shuowu/backing-image-manager:v2_20211025-1 --manager-image shuowu/longhorn-manager:4a8782e4-dirty-2 --service-account longhorn-service-account
root      653188  0.0  0.0   6432   740 pts/1    S+   11:13   0:00 grep --color=auto backing
```
```bash
root@shuo-cluster-worker-3:~# ps aux | grep backing
root     2198716  0.0  0.2 1528140 20600 ?       SLsl 10:00   0:03 backing-image-manager --debug daemon --listen 0.0.0.0:8000
root     2290980  1.5  0.9 745556 76248 ?        SLsl 11:11   0:01 longhorn-manager -d daemon --engine-image longhornio/longhorn-engine:master-head --instance-manager-image longhornio/longhorn-instance-manager:v1_20210731 --share-manager-image longhornio/longhorn-share-manager:v1_20211020 --backing-image-manager-image shuowu/backing-image-manager:v2_20211025-1 --manager-image shuowu/longhorn-manager:4a8782e4-dirty-2 --service-account longhorn-service-account
root     2293575  0.0  0.0   6432   676 pts/1    S+   11:13   0:00 grep --color=auto backing
root@shuo-cluster-worker-3:~# rm /var/lib/longhorn/backing-images/bi-test-5cea928b/backing && kill -9 2198716
```
6. Check the backing image:
   1. The state of both files will become `unknown` then `failed`.
   2. The error message of the modified file is like `backing image expected checksum xxx doesn't match the existing file checksum xxxx`) then `stat /data/backing-images/xxx/backing: no such file or directory`.
   3. The current checksum of the backing image keeps unchanged.
7. Wait for a while then there will be a backing image data source pod restarting the download. After re-downloading, the backing image will get recovered.
