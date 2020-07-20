---
title: Test access style for S3 compatible backupstore
---
### Case 1: Using Alibaba Cloud OSS bucket as backupstore
1. Create an OSS bucket within Region China in Alibaba Cloud(Aliyun).
2. Create a secret without `VIRTUAL_HOSTED_STYLE` for the OSS bucket.
3. Set backup target and the secret in Longhorn UI.
4. Try to list backup. Then the error `error: AWS Error: SecondLevelDomainForbidden Please use virtual hosted style to access.` is triggered.
5. Add `VIRTUAL_HOSTED_STYLE: dHJ1ZQ== # true` to the secret.
6. Backup list/create/delete/restore work fine after the configuration.


### Case 2: Using AWS S3 bucket as backupstore
1. Create a secret without `VIRTUAL_HOSTED_STYLE` for the S3 bucket.
2. Set backup target and the secret in Longhorn UI.
3. Verify backup list/create/delete/restore work fine without the configuration.
4. Add `VIRTUAL_HOSTED_STYLE: dHJ1ZQ== # true` to the secret.
5. Verify backup list/create/delete/restore still work fine after the configuration.
