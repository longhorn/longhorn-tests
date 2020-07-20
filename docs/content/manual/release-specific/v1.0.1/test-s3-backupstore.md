---
title: Test S3 backupstore in a cluster sitting behind a Http Proxy
---
1. Create a new instance on Linode and setup an Http Proxy server on the instance as in [this instruction](https://rancher.atlassian.net/wiki/spaces/EN/pages/92831879/Proxy+Setup) (you will have to log in to see the instruction)
1. Create a cluster using Rancher as below:
     1. Choose AWS EC2 `t2.medium` as the node template. The reason to chose EC2 is that its `security group` makes our lives easier to block the outgoing traffic from the instance and all k8s Pods running inside the instance. I tried Linode and was able to manually block outbound traffic from the host, but fail to block the outbound traffic from k8s's pods. I would be very thankful if somebody can explain to me how to do it on Linode :D.
     1. Using the template, create a cluster of 1 node. Again, having only 1 node make it easier to block outgoing traffic from k8s pods.
     1. Install Longhorn to the cluster. Remember to change the `#replica` to 1 bc we only have 1 node in the cluster.
     1. Wait for Longhorn to finish the installation.
     1. deploy `s3-secret` to `longhorn-system` namespace and setup backupstore target to point to your s3 bucket. Create a volume, attach to a pod, write some data into it, and create a backup. At this time, everything should work fine because the EC2 node still has access to the public internet. The `s3-secret` must have HTTP_PROXY, HTTPS_PROXY, and NO_PROXY as below (remember to convert the values to base64):
    ```shell
    AWS_ACCESS_KEY_ID: <your_aws_access_key_id>
    AWS_SECRET_ACCESS_KEY: <your_aws_secret_access_key>
    HTTP_PROXY: "http://proxy_ip:proxy_port"
    HTTPS_PROXY: "http://proxy_ip:proxy_port"
    NO_PROXY: "localhost,127.0.0.1,0.0.0.0,10.0.0.0/8,192.168.0.0/16"
    ```
1. Next, we will simulate the setup in the issue by blocking all the outbound traffic from the EC2 instance. Navigate to AWS EC2 console and find the EC2 instance of the cluster. Open the security group for the EC2. Set the outbound traffic as below:<img width="1637" alt="Screen Shot 2020-07-09 at 8 16 00 PM" src="https://user-images.githubusercontent.com/22139961/87112575-0ca3eb80-c221-11ea-86ef-91ed5f8384cc.png">
     1. Now the cluster is isolated from the outside world. It can only send outgoing traffic to your personal computer, the rancher node server, and the Http_Proxy. Therefore, the only way to access the internet is through the Proxy because only the Proxy forwards the packets.
     1. Go back and check the `backup` in Longhorn UI. We should see that Longhorn UI successfully to retrieve the backup list.
     1. Try to create a new backup, we should see that the operation success
     1. If we check the log of the proxy server, we can see every request which was sent by longhorn `manager` and longhorn `engine` sent to AWS S3.
