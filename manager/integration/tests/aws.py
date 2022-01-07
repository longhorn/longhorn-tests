import time
import boto3
import os

from cloudprovider import cloudprovider


class aws(cloudprovider):
    ACTION_WAIT_TIMEOUT_SEC = 120
    ec2_client = None

    def __init__(self):
        access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        if access_key_id is None:
            print("AWS_ACCESS_KEY_ID env variable not defined")
            assert False

        secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        if access_key_id is None:
            print("AWS_SECRET_ACCESS_KEY env variable not defined")
            assert False

        default_region = os.getenv("AWS_DEFAULT_REGION")
        if access_key_id is None:
            print("AWS_DEFAULT_REGION env variable not defined")
            assert False

        aws.ec2_client = boto3.client(
            'ec2',
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=default_region)

    def instance_id_by_ip(self, instance_ip):
        response = aws.ec2_client.describe_instances(
            Filters=[
                {
                    'Name': 'private-ip-address',
                    'Values': [instance_ip]
                },
            ],
        )

        return response['Reservations'][0]['Instances'][0]['InstanceId']

    def instance_id(self, instance_name):
        response = aws.ec2_client.describe_instances(
            Filters=[
                {
                    'Name': 'tag:Name',
                    'Values': [instance_name]
                },
            ],
        )

        return response['Reservations'][0]['Instances'][0]['InstanceId']

    def instance_status(self, instance_id):
        response = aws.ec2_client.describe_instances(
            InstanceIds=[instance_id]
        )

        return response['Reservations'][0]['Instances'][0]['State']['Name']

    def instance_exec_action(self,
                             instance_id,
                             action,
                             expected_status,
                             desired_status):
        instance_current_status = self.instance_status(instance_id)
        if instance_current_status == expected_status:
            if action == "start":
                aws.ec2_client.start_instances(InstanceIds=[instance_id])
            elif action == "stop":
                aws.ec2_client.stop_instances(InstanceIds=[instance_id])

            action_ok = False
            for i in range(self.ACTION_WAIT_TIMEOUT_SEC):
                instance_status = self.instance_status(instance_id)
                if instance_status == desired_status:
                    action_ok = True
                    break
                elif instance_status == expected_status:
                    time.sleep(1)

            return action_ok

        elif instance_current_status == desired_status:
            return True

    def instance_start(self, instance_id):
        self.instance_exec_action(instance_id=instance_id,
                                  action="start",
                                  expected_status="stopped",
                                  desired_status="running")

    def instance_stop(self, instance_id):
        self.instance_exec_action(instance_id=instance_id,
                                  action="stop",
                                  expected_status="running",
                                  desired_status="stopped")
