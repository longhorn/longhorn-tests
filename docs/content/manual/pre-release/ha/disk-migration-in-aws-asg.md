---
title: Disk migration in AWS ASG
---

## Some Longhorn worker nodes in AWS Auto Scaling group is in replacement
1. Launch a Kubernetes cluster with the nodes in AWS Auto Scaling group. Make sure there is an additional EBS attached to instance with setting `Delete on Termination` disabled. 
2. Deploy Longhorn v1.1.0 on the cluster and Set `ReplicaReplenishmentWaitInterval`. Make sure it's longer than the time needs for node replacement.
3. Deploy some workloads using Longhorn volumes.
4. Trigger the ASG instance refresh in AWS.
5. Manually attach EBS to new instance and mount the disk.
6. Add the disk in longhorn to make the existing replica available to be identified by Longhorn.
7. Verify new replicas won't be created before reaching `ReplicaReplenishmentWaitInterval`.
8. Verify the failed replicas are reused after the node recovery.
9. Verify if workloads still work fine with the volumes after the recovery.

## EBS migration in AWS in a ASG set up using script
1. Launch a Kubernetes cluster with 1 node in AWS Auto Scaling group. Make sure there is an additional EBS attached to instance with setting `Delete on Termination` disabled.
2. Deploy Longhorn v1.1.0 on the cluster and Set `ReplicaReplenishmentWaitInterval`. Make sure it's longer than the time needs for node replacement.
3. Deploy some workloads using Longhorn volumes.
4. Modify launch template of ASG and provide mount command for EBS.
    ```
    sudo mkdir -p /data
    sudo mount /dev/xvdh /data
5.  Trigger ASG instance refresh with below script using AWS Cli, which will attach the existing EBS volume to the new instance.
    ```
    AWS_REGION=<Your aws region>
    INSTANCE_NAME=<Instance name>
    VOLUME_STATUS=''
    INSTANCE_ID=$(aws --region=$AWS_REGION ec2 describe-instances --filters 'Name=tag:Name,Values=$INSTANCE_NAME' | jq -r '.Reservations[].Instances[].InstanceId')
    VOLUME_ID= $(aws --region=$AWS_REGION ec2 describe-volumes --filters 'Name='attachment.instance-id',Values='$INSTANCE_ID'' | jq -r '.Volumes[1].VolumeId')

    aws autoscaling start-instance-refresh --auto-scaling-group-name my-asg --preferences '{"InstanceWarmup": 300, "MinHealthyPercentage": 90}'

    until [ "x$VOLUME_STATUS" == "xattached" ]; do
        VOL_STATUS=$(aws ec2 describe-volumes --volume-ids $VOL_ID --query 'Volumes[0].State')
        sleep 5
    done
    INSTANCE_ID=$(aws --region=$AWS_REGION ec2 describe-instances --filters 'Name=tag:Name,Values=$INSTANCE_NAME' | jq -r '.Reservations[].Instances[].InstanceId')
    aws ec2 attach-volume --volume-id $VOLUME_ID --instance-id $INSTANCE_ID --device /dev/sdh'
6. Add the disk in longhorn to make the existing replica available to be identified by Longhorn.
7. Verify new replicas won't be created before reaching `ReplicaReplenishmentWaitInterval`.
8. Verify the failed replicas are reused after the node recovery.
9. Verify if workloads still work fine with the volumes after the recovery.

Note: 1 node cluster is taken only for testing purpose, in real scenario more complex script would be needed for cluster having multiple nodes.
