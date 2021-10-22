---
title: Test backing image space usage with sparse files 
---

### Prerequisite
A sparse file should be prepared before test. e.g.:
```bash
~ touch empty-filesystem.raw
~ truncate -s 500M empty-filesystem.raw
~ mkfs.ext4 empty-filesystem.raw
mke2fs 1.46.1 (9-Feb-2021)
Creating filesystem with 512000 1k blocks and 128016 inodes
Filesystem UUID: fe6cfb58-134a-42b3-afab-59474d9515e0
Superblock backups stored on blocks:
	8193, 24577, 40961, 57345, 73729, 204801, 221185, 401409

Allocating group tables: done
Writing inode tables: done
Creating journal (8192 blocks): done
Writing superblocks and filesystem accounting information: done

~ shasum -a 512 empty-filesystem.raw
4277f6174bf43d1f03f328eaf507f4baf84a645d79239b3ef4593a87b5127ceb097d540281e1f3557d9ad1d2591135bbcf24db480c1bd732b633b93cf4fe50c9  empty-filesystem.raw
```
For convenience, the above example file is already uploaded to the S3 server. The URL is `https://longhorn-backing-image.s3.us-west-1.amazonaws.com/empty-filesystem.raw`.

Of course, you can generate your own test file as well.

### Test step
1. Create a backing image via one of the following ways:
   1. Select source type `Download From URL` and input the S3 URL of your test file.
   2. Upload your test file to the cluster as the backing image.
2. Wait for the backing image ready.
3. Enter into the backing image manager pod. Verify the following of the backing image file:
   1. the apparent size is the same as that of the test file.
   2. the actual size is much smaller than the apparent size.
   3. the SHA512 checksum matches.
4. Create a volume using this backing image file.
5. Attach the volume then verify the content. 
   For the example backing image, you can verify it by directly mounting the volume without making a filesystem and see if the volume already contains an empty EXT4 filesystem
6. Verify the volume work fine.
7. Do cleanup.
