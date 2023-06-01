#!/usr/bin/env bash

set -eo pipefail

CURRENT_TIMESTAMP=$(date -u +%s)
echo "Current Time: $(date -u)"
THRESHOLD_IN_SEC=$((86400)) # if an instance exists more than 1 day, delete it.
SUFFIX_ARR=()

echo "[Step 1] Get all instances:"
ALL_INSTANCES=$(aws ec2 describe-instances --filters Name=tag:Owner,Values=longhorn-infra | jq '.Reservations[].Instances[] | select(.State.Name != "terminated") | {LaunchTime: .LaunchTime, InstanceId: .InstanceId, Tags: .Tags}' | jq -c)
for INSTANCE in ${ALL_INSTANCES[@]}; do
  INSTANCE_ID=$(echo "${INSTANCE}" | jq '.InstanceId' | tr -d '"')
  echo " * Instance ${INSTANCE_ID} ==>"
  LAUNCH_TIME=$(echo "${INSTANCE}" | jq '.LaunchTime' | tr -d '"')
  TIMESTAMP=$(date -D "%Y-%m-%dT%H:%M:%S+00:00" -d "${LAUNCH_TIME}" +%s)
  TIME_DIFF=$((CURRENT_TIMESTAMP-TIMESTAMP))
  echo "   Launch Time: ${LAUNCH_TIME} (${TIMESTAMP}), Diff: ${TIME_DIFF}"
  RESOURCE_SUFFIX=$(echo "$INSTANCE" | jq '.Tags[] | select(.Key == "Name").Value' | tr -d '"' | rev | cut -d- -f1 | rev)
  echo "   Resource Suffix: $RESOURCE_SUFFIX"
  if [[ $TIME_DIFF -gt $THRESHOLD_IN_SEC ]]; then SUFFIX_ARR+=("$RESOURCE_SUFFIX"); fi
done

echo "[Step 2] Get long-running resource suffixes:"
SUFFIX_ARR=($(echo "${SUFFIX_ARR[@]}" | tr ' ' '\n' | sort -u | tr '\n' ' '))
echo " * Unexpected Long-running Resource Suffixes: ${SUFFIX_ARR[*]}"
echo " * Unexpected Long-running Resource Suffixes Count = ${#SUFFIX_ARR[@]}"

echo "[Step 3] Prepare to delete long-running resources:"
for SUFFIX in ${SUFFIX_ARR[@]}; do

  echo " * Deal with Suffix ${SUFFIX} ==>"

  echo "   (1) delete instances:"
  INSTANCE_IDS=$(aws ec2 describe-instances --filters Name=tag:Name,Values=*"${SUFFIX}"* | jq '.Reservations[].Instances[].InstanceId' | tr -d '"')
  for INSTANCE_ID in ${INSTANCE_IDS}
  do
    aws ec2 terminate-instances --instance-ids "${INSTANCE_ID}"
    echo "   instance ${INSTANCE_ID} shutting-down"
  done
  while [[ -n $(aws ec2 describe-instances --filters Name=tag:Name,Values=*"${SUFFIX}"* | jq '.Reservations[].Instances[].State.Name' | grep -v "terminated") ]]; do
    echo "Wait for instances terminated ..."
    sleep 5s
  done

  echo "   (2) delete volumes:"
  VOLUME_IDS=$(aws ec2 describe-volumes --filters Name=tag:Name,Values=*"${SUFFIX}"* | jq '.Volumes[].VolumeId' | tr -d '"')
  for VOLUME_ID in ${VOLUME_IDS}
  do
    aws ec2 delete-volume --volume-id "${VOLUME_ID}"
    echo "   volume ${VOLUME_ID} deleted"
  done

  echo "   (3) delete load balancers:"
  LOAD_BALANCER_ARNS=$(aws elbv2 describe-load-balancers | jq ".LoadBalancers[] | select(.LoadBalancerArn | contains(\"${SUFFIX}\")).LoadBalancerArn" | tr -d '"')
  for LOAD_BALANCER_ARN in ${LOAD_BALANCER_ARNS}
  do
    aws elbv2 delete-load-balancer --load-balancer-arn "${LOAD_BALANCER_ARN}"
    echo "   load balancer ${LOAD_BALANCER_ARN} deleted"
  done

  echo "   (4) delete load balancer target groups:"
  TARGET_GROUP_ARNS=$(aws elbv2 describe-target-groups | jq ".TargetGroups[] | select(.TargetGroupArn | contains(\"${SUFFIX}\")).TargetGroupArn" | tr -d '"')
  for TARGET_GROUP_ARN in ${TARGET_GROUP_ARNS}
  do
    aws elbv2 delete-target-group --target-group-arn "${TARGET_GROUP_ARN}"
    echo "   load balancer target group ${TARGET_GROUP_ARN} deleted"
  done

  echo "   (5) delete route tables:"
  ROUTE_TABLE_ASSOCIATION_IDS=$(aws ec2 describe-route-tables --filters Name=tag:Name,Values=*"${SUFFIX}"* | jq '.RouteTables[].Associations[].RouteTableAssociationId' | tr -d '"')
  for ROUTE_TABEL_ASSOCIATION_ID in ${ROUTE_TABLE_ASSOCIATION_IDS}
  do
    aws ec2 disassociate-route-table --association-id "${ROUTE_TABEL_ASSOCIATION_ID}"
    echo "   route table association ${ROUTE_TABEL_ASSOCIATION_ID} deleted"
  done
  ROUTE_TABLE_IDS=$(aws ec2 describe-route-tables --filters Name=tag:Name,Values=*"${SUFFIX}"* | jq '.RouteTables[].RouteTableId' | tr -d '"')
  for ROUTE_TABLE_ID in ${ROUTE_TABLE_IDS}
  do
    aws ec2 delete-route-table --route-table-id "${ROUTE_TABLE_ID}"
    echo "   route table ${ROUTE_TABLE_ID} deleted"
  done

  echo "   (6) delete nat gateways:"
  NAT_GATEWAY_IDS=$(aws ec2 describe-nat-gateways --filter Name=tag:Name,Values=*"${SUFFIX}"* | jq '.NatGateways[].NatGatewayId' | tr -d '"')
  for NAT_GATEWAY_ID in ${NAT_GATEWAY_IDS}
  do
    aws ec2 delete-nat-gateway --nat-gateway-id "${NAT_GATEWAY_ID}"
    echo "   request to delete nat gateway ${NAT_GATEWAY_ID}"
  done
  while [[ -n $(aws ec2 describe-nat-gateways --filter Name=tag:Name,Values=*"${SUFFIX}"* | jq '.NatGateways[].State' | grep -v "deleted") ]]; do
    echo "Wait for NAT gateway deleted ..."
    sleep 5s
  done

  echo "   (7) delete allocation addresses:"
  ADDRESS_ALLOCATION_IDS=$(aws ec2 describe-addresses --filters Name=tag:Name,Values=*"${SUFFIX}"* | jq '.Addresses[].AllocationId' | tr -d '"')
  for ADDRESS_ALLOCATION_ID in ${ADDRESS_ALLOCATION_IDS}
  do
    aws ec2 release-address --allocation-id "${ADDRESS_ALLOCATION_ID}"
    echo "   allocation address ${ADDRESS_ALLOCATION_ID} released"
  done

  echo "   (8) delete internet gateways:"
  INTERNET_GATEWAY_IDS=$(aws ec2 describe-internet-gateways --filters Name=tag:Name,Values=*"${SUFFIX}"* | jq '.InternetGateways[].InternetGatewayId' | tr -d '"')
  INTERNET_GATEWAY_ATTACHMENT_VPC_IDS=$(aws ec2 describe-internet-gateways --filters Name=tag:Name,Values=*"${SUFFIX}"* | jq '.InternetGateways[].Attachments[].VpcId' | tr -d '"')
  for INTERNET_GATEWAY_ID in ${INTERNET_GATEWAY_IDS}
  do
    aws ec2 detach-internet-gateway --internet-gateway-id "${INTERNET_GATEWAY_ID}" --vpc-id "${INTERNET_GATEWAY_ATTACHMENT_VPC_IDS}"
    aws ec2 delete-internet-gateway --internet-gateway-id "${INTERNET_GATEWAY_ID}"
    echo "   internet gateway ${INTERNET_GATEWAY_ID} deleted"
  done

  echo "   (9) delete security groups:"
  SECURITY_GROUP_IDS=$(aws ec2 describe-security-groups --filters Name=tag:Name,Values=*"${SUFFIX}"* | jq '.SecurityGroups[].GroupId' | tr -d '"')
  for SECURITY_GROUP_ID in ${SECURITY_GROUP_IDS}
  do
    aws ec2 delete-security-group --group-id "${SECURITY_GROUP_ID}"
    echo "   security group ${SECURITY_GROUP_ID} deleted"
  done

  echo "   (10) delete subnets:"
  SUBNET_IDS=$(aws ec2 describe-subnets --filters Name=tag:Name,Values=*"${SUFFIX}"* | jq '.Subnets[].SubnetId' | tr -d '"')
  for SUBNET_ID in ${SUBNET_IDS}
  do
    aws ec2 delete-subnet --subnet-id "${SUBNET_ID}"
    echo "   subnet ${SUBNET_ID} deleted"
  done

  echo "   (11) delete vpc:"
  VPC_ID=$(aws ec2 describe-vpcs --filters Name=tag:Name,Values=*"${SUFFIX}"* | jq '.Vpcs[].VpcId' | tr -d '"')
  aws ec2 delete-vpc --vpc-id "${VPC_ID}"
  echo "   vpc ${VPC_ID} deleted"

  echo "   (12) delete key pairs:"
  KEY_NAMES=$(aws ec2 describe-key-pairs --filters Name=key-name,Values=*"${SUFFIX}"* | jq '.KeyPairs[].KeyName' | tr -d '"')
  for KEY_NAME in ${KEY_NAMES}
  do
    aws ec2 delete-key-pair --key-name "${KEY_NAME}"
    echo "   key pair ${KEY_NAME} deleted"
  done

done