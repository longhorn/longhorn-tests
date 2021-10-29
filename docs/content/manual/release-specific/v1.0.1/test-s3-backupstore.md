---
title: Test S3 backupstore in a cluster sitting behind a HTTP proxy
---
<sup>Related issue: [3136](https://github.com/longhorn/longhorn/issues/3136)</sup>

Requirement:
- Set up a stand alone Squid, HTTP web proxy
  - To configure Squid proxy: [a comment about squid config](https://github.com/longhorn/longhorn/issues/1967#issuecomment-736959332)
  - If setting up instance on AWS: [a EC2 security group setting](https://user-images.githubusercontent.com/22139961/87112575-0ca3eb80-c221-11ea-86ef-91ed5f8384cc.png)
- S3 with existing backups

Steps:
1. Create credential for **Backup Target**
  * ```shell
     $ secret_name="aws-secret-proxy"
     $ proxy_ip=123.123.123.123
     $ no_proxy_params="localhost,127.0.0.1,0.0.0.0,10.0.0.0/8,192.168.0.0/16"

     $ kubectl create secret generic $secret_name \
     --from-literal=AWS_ACCESS_KEY_ID=$AWS_ID \
     --from-literal=AWS_SECRET_ACCESS_KEY=$AWS_KEY \
     --from-literal=HTTP_PROXY=$proxy_ip:3128 \
     --from-literal=HTTPS_PROXY=$proxy_ip:3128 \
     --from-literal=NO_PROXY=$no_proxy_params \
     -n longhorn-system
     ```
2. Open Longhorn UI
3. Click on *Setting*
4. Scroll down to *Backup Target Credential Secret*
5. Fill in `$secret_name` assigned in step 1. and save setting
6. Go to *Backup*
7. Restore from existing backups and watch the volume become ready
