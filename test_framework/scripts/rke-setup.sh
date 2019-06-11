#!/usr/bin/env ash

set  -x

K8S_CONTROLLER_IP=`grep controller "${TF_VAR_tf_workspace}/terraform.output"  | awk '{print $3}'`
sed -i 's/K8S_CONTROLLER_IP/'${K8S_CONTROLLER_IP}'/' "${TF_VAR_tf_workspace}/templates/3-nodes-k8s.yml"

K8S_WORKER_1_IP=`grep worker-1 "${TF_VAR_tf_workspace}/terraform.output"  | awk '{print $3}'`
sed -i 's/K8S_WORKER_1_IP/'${K8S_WORKER_1_IP}'/' "${TF_VAR_tf_workspace}/templates/3-nodes-k8s.yml"

K8S_WORKER_2_IP=`grep worker-2 "${TF_VAR_tf_workspace}/terraform.output"  | awk '{print $3}'`
sed -i 's/K8S_WORKER_2_IP/'${K8S_WORKER_2_IP}'/' "${TF_VAR_tf_workspace}/templates/3-nodes-k8s.yml"

rke up --config "${TF_VAR_tf_workspace}/templates/3-nodes-k8s.yml"

