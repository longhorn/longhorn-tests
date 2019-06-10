#!/usr/bin/env ash

set  -x

K8S_CONTROLLER_IP=`grep controller "${WORKSPACE}/terraform.output"  | awk '{print $3}'`
sed -i 's/K8S_CONTROLLER_IP/'${K8S_CONTROLLER_IP}'/' "${WORKSPACE}/templates/3-nodes-k8s.yml"

K8S_WORKER_1_IP=`grep worker-1 "${WORKSPACE}/terraform.output"  | awk '{print $3}'`
sed -i 's/K8S_WORKER_1_IP/'${K8S_WORKER_1_IP}'/' "${WORKSPACE}/templates/3-nodes-k8s.yml"

K8S_WORKER_2_IP=`grep worker-2 ${WORKSPACE}/terraform.output  | awk '{print $3}'`
sed -i 's/K8S_WORKER_2_IP/'${K8S_WORKER_2_IP}'/' "${WORKSPACE}/templates/3-nodes-k8s.yml"

rke up --config "${WORKSPACE}/templates/3-nodes-k8s.yml"

