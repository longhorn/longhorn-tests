---
title: Backup & Restore tests
---
Anytime we identify a backup & restore issue we should add it to the test scenarios below.
In general it's important to test concurrent backup & deletion & restoration operations.

# Test Setup
- create vol `bak` and attach to node
- connect to node via ssh and issue `dd if=/dev/urandom of=/dev/longhorn/bak status=progress`
- keep the dd running while doing all the tests below, that way you constantly have new data when backing up
- setup recurring backups every minute with retain count of `3`
- do all the tests for each currently supported backup store `nfs, s3`
