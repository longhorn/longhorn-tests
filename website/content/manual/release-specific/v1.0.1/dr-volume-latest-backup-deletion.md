---
title: DR volume related latest backup deletion test
---
DR volume keeps getting the latest update from the related backups. Edge cases where the latest backup is deleted can be test as below.
## Case 1:
1. Create a volume and take multiple backups for the same.
2. Delete the latest backup.
3. Create another cluster and set the same backup store to access the backups created in step 1.
4. Go to backup page and click on the backup. Verify the ```Create Disaster Recovery``` option is enabled for it.
## Case 2:
1. Create a volume V1 and take multiple backups for the same.
2. Create another cluster and set the same backup store to access the backups created in step 1.
4. Go to backup page and Create a Disaster Recovery Volume for the backups created in step 1.
5. Create more backup(s) for volume V1 from step 1.
6. Delete the latest backup before the DR volume starts the incremental restore process.
7. Verify the DR Volume still remains healthy.
8. Activate the DR Volume to verify the data.
