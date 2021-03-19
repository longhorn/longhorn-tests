---
title: Test Volume Backup and Restore by AWS IAM role
---

## Related issue

https://github.com/longhorn/longhorn/issues/1526

Longhorn v1.1.1 should work with volume backup and restore by AWS IAM role

## Scenario
1. Install AWS CLI and configure your AWS credentials
```shell
curl "https://s3.amazonaws.com/aws-cli/awscli-bundle.zip" -o "awscli-bundle.zip"
unzip awscli-bundle.zip
./awscli-bundle/install -b ~/bin/aws
~/bin/aws configure
```
2. Create AWS S3 bucket
```shell
S3_BUCKET_NAME=<bucket-name>

~/bin/aws s3api create-bucket \
    --bucket $S3_BUCKET_NAME \
    --region us-west-2 \
    --create-bucket-configuration LocationConstraint=us-west-2
```
3. Create a new IAM instance profile `NodeInstanceProfile`
```shell
cat > node-instance-assume-role-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

~/bin/aws iam create-role \
    --role-name NodeInstanceRole \
    --assume-role-policy-document file://node-instance-assume-role-policy.json

~/bin/aws iam create-instance-profile \
    --instance-profile-name NodeInstanceProfile

~/bin/aws iam add-role-to-instance-profile \
    --instance-profile-name NodeInstanceProfile \
    --role-name NodeInstanceRole
```
4. Install RKE2 with CNI canal on top of AWS with IAM instance profile name `NodeInstanceProfile`
5. Prepare kube2iam-values.yaml
```yaml
host:
  iptables: true
  interface: "cali+"
  port: 8080
 
rbac:
  create: true
```
7. Install kube2iam on namespace kube2iam 
```shell
helm repo add kube2iam https://jtblin.github.io/kube2iam/
helm repo update
helm upgrade --install kube2iam kube2iam/kube2iam \
    -f kube2iam-values.yaml \
    -n kube2iam \
    --create-namespace
```
8. Create a new IAM role `k8s-longhorn` and attach a trust policy to it
```shell
NODE_INSTANCE_ROLE=`~/bin/aws iam get-role --role-name NodeInstanceRole | jq -r '.Role.Arn'`

cat > node-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    },
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "AWS": "$NODE_INSTANCE_ROLE"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
 
aws iam create-role \
    --role-name k8s-longhorn \
    --assume-role-policy-document \
    file://node-trust-policy.json
 
cat > s3-longhorn-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::$S3_BUCKET_NAME",
        "arn:aws:s3:::$S3_BUCKET_NAME/*"
      ]
    }
  ]
}
EOF
 
~/bin/aws iam put-role-policy \
    --role-name k8s-longhorn \
    --policy-name s3 \
    --policy-document file://s3-longhorn-policy.json
```
9. Create the secret `aws-secret` to longhorn-system
```shell
K8S_LONGHORN_ROLE=`~/bin/aws iam get-role --role-name k8s-longhorn | jq -r '.Role.Arn'`

kubectl create secret generic aws-secret \
    --from-literal=AWS_IAM_ROLE_ARN=$K8S_LONGHORN_ROLE \
    -n longhorn-system
```
10. On the Longhorn UI, click Settings. In the Backup section, set Backup Target to:
```shell
s3://<your-bucket-name>@<your-aws-region>/
```
11. In the Backup section, set Backup Target Credential Secret to:
```shell
aws-secret
```
