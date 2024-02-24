#!/bin/bash
NAMESPACE=$(yq eval '.namespace' config.yaml)

kubectl get statefulset -n $NAMESPACE --no-headers | grep "test-data-" | awk '{print $1}' | xargs kubectl -n $NAMESPACE delete statefulset
kubectl get deployment -n $NAMESPACE --no-headers | grep "test-data-" | awk '{print $1}' | xargs kubectl -n $NAMESPACE delete deployment
kubectl get pvc -n $NAMESPACE --no-headers | grep "test-data-" | awk '{print $1}' | xargs kubectl -n $NAMESPACE delete pvc