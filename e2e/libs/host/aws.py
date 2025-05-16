import boto3
import time

from host.constant import NODE_REBOOT_DOWN_TIME_SECOND
from host.base import Base

from utility.utility import logging
from utility.utility import wait_for_cluster_ready
from utility.utility import get_retry_count_and_interval


class Aws(Base):

    def __init__(self):
        super().__init__()
        self.aws_client = boto3.client('ec2')
        self.aws_resource = boto3.resource('ec2')
        self.snapshot_ids = []
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def reboot_all_nodes(self, shut_down_time_in_sec=NODE_REBOOT_DOWN_TIME_SECOND):
        instance_ids = [value for value in self.mapping.values()]

        resp = self.aws_client.stop_instances(InstanceIds=instance_ids, Force=True)
        assert resp['ResponseMetadata']['HTTPStatusCode'] == 200, f"Failed to stop instances {instance_ids} response: {resp}"
        logging(f"Stopping instances {instance_ids}")
        waiter = self.aws_client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=instance_ids)

        logging(f"Wait for {shut_down_time_in_sec} seconds before starting instances")
        time.sleep(shut_down_time_in_sec)

        resp = self.aws_client.start_instances(InstanceIds=instance_ids)
        logging(f"Starting instances {instance_ids} response: {resp}")
        waiter = self.aws_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=instance_ids)

        wait_for_cluster_ready()

        logging(f"Started instances")

    def reboot_node(self, reboot_node_name, shut_down_time_in_sec=NODE_REBOOT_DOWN_TIME_SECOND):
        instance_ids = [self.mapping[reboot_node_name]]

        resp = self.aws_client.stop_instances(InstanceIds=instance_ids, Force=True)
        assert resp['ResponseMetadata']['HTTPStatusCode'] == 200, f"Failed to stop instances {instance_ids} response: {resp}"
        logging(f"Stopping instances {instance_ids}")
        waiter = self.aws_client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=instance_ids)
        logging(f"Stopped instances")

        time.sleep(shut_down_time_in_sec)

        resp = self.aws_client.start_instances(InstanceIds=instance_ids)
        logging(f"Starting instances {instance_ids} response: {resp}")
        waiter = self.aws_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=instance_ids)
        logging(f"Started instances")

    def reboot_all_worker_nodes(self, shut_down_time_in_sec=NODE_REBOOT_DOWN_TIME_SECOND):
        instance_ids = [self.mapping[value] for value in self.node.list_node_names_by_role("worker")]

        resp = self.aws_client.stop_instances(InstanceIds=instance_ids, Force=True)
        assert resp['ResponseMetadata']['HTTPStatusCode'] == 200, f"Failed to stop instances {instance_ids} response: {resp}"
        logging(f"Stopping instances {instance_ids}")
        waiter = self.aws_client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=instance_ids)
        logging(f"Stopped instances")

        time.sleep(shut_down_time_in_sec)

        resp = self.aws_client.start_instances(InstanceIds=instance_ids)
        logging(f"Starting instances {instance_ids} response: {resp}")
        waiter = self.aws_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=instance_ids)
        logging(f"Started instances")

    def power_off_node(self, power_off_node_name, waiting=True):
        instance_ids = [self.mapping[power_off_node_name]]
        resp = self.aws_client.stop_instances(InstanceIds=instance_ids, Force=True)
        assert resp['ResponseMetadata']['HTTPStatusCode'] == 200, f"Failed to stop instances {instance_ids} response: {resp}"
        logging(f"Stopping instances {instance_ids}")
        if waiting:
            waiter = self.aws_client.get_waiter('instance_stopped')
            waiter.wait(InstanceIds=instance_ids)
            logging(f"Stopped instances")
            self.node.wait_for_node_down(power_off_node_name)

    def power_on_node(self, power_on_node_name):
        instance_ids = [self.mapping[power_on_node_name]]

        resp = self.aws_client.start_instances(InstanceIds=instance_ids)
        logging(f"Starting instances {instance_ids} response: {resp}")
        waiter = self.aws_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=instance_ids)
        logging(f"Started instances")
        self.node.wait_for_node_up(power_on_node_name)

    def create_snapshot(self, node_name):
        instance_id = self.mapping[node_name]
        instance = self.aws_resource.Instance(instance_id)
        snapshot_ids = []

        logging(f"Creating vm snapshots for instance {instance_id}")

        # in aws, we cannot directly take a snapshot of an ec2 instance
        # we must snapshot the volumes attached to the instance
        for dev in instance.block_device_mappings:
            volume_id = dev.get('Ebs', {}).get('VolumeId')
            if volume_id:
                logging(f"Creating vm snapshot for volume {volume_id} from instance {instance_id}")
                description = f"volume {volume_id} from instance {instance_id}"
                res = self.aws_client.create_snapshot(
                    VolumeId=volume_id,
                    Description=description,
                    TagSpecifications=[{
                        'ResourceType': 'snapshot',
                        'Tags': [{'Key': 'CreatedBy', 'Value': 'SnapshotScript'}]
                    }]
                )
                snapshot_ids.append(res['SnapshotId'])
                logging(f"Created vm snapshot {res['SnapshotId']} for volume {volume_id} from instance {instance_id}")

        self.snapshot_ids.extend(snapshot_ids)

        for snapshot_id in snapshot_ids:
            completed = False
            for i in range(self.retry_count):
                resp = self.aws_client.describe_snapshots(SnapshotIds=[snapshot_id])
                snapshot = resp['Snapshots'][0]
                state = snapshot['State']
                progress = snapshot.get('Progress', '0%')
                logging(f"Waiting for vm snapshot {snapshot_id} to complete, current state={state}, progress={progress} ... ({i})")

                if state == 'completed':
                    completed = True
                    break
                else:
                    time.sleep(self.retry_interval)
            assert completed, f"Failed to wait for vm snapshot {snapshot_id} to complete"

    def cleanup_snapshots(self):
        for snapshot_id in self.snapshot_ids:
            print(f"Deleting vm snapshot {snapshot_id}")
            self.aws_client.delete_snapshot(SnapshotId=snapshot_id)
            for i in range(self.retry_count):
                logging(f"Waiting for vm snapshot {snapshot_id} deleted ... ({i})")
                try:
                    self.aws_resource.Snapshot(snapshot_id).load()
                except self.aws_client.exceptions.ClientError as e:
                    if "InvalidSnapshot.NotFound" in str(e):
                        logging(f"Deleted vm snapshot {snapshot_id}")
                        break
                    else:
                        raise
                time.sleep(self.retry_interval)
