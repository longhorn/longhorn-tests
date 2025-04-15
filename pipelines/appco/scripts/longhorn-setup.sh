#!/usr/bin/env bash

set -x

source pipelines/utilities/run_longhorn_test.sh
source test_framework/scripts/kubeconfig.sh
source pipelines/utilities/longhorn_ui.sh
source pipelines/utilities/coredns.sh
source pipelines/utilities/create_aws_secret.sh
source pipelines/utilities/longhornctl.sh
source pipelines/utilities/create_longhorn_namespace.sh
source pipelines/utilities/create_registry_secret.sh
source pipelines/utilities/longhorn_manifest.sh

# create and clean tmpdir
TMPDIR="/tmp/longhorn"
mkdir -p ${TMPDIR}
rm -rf "${TMPDIR}/"

LONGHORN_NAMESPACE="longhorn-system"

# Longhorn version tag (e.g v1.1.0), use "master" for latest stable
# we will use this version as the base for upgrade
LONGHORN_STABLE_VERSION=${LONGHORN_STABLE_VERSION:-master}
LONGHORN_STABLE_MANIFEST_URL="https://raw.githubusercontent.com/longhorn/longhorn/${LONGHORN_STABLE_VERSION}/deploy/longhorn.yaml"

# for install Longhorn by manifest
LONGHORN_MANIFEST_URL="https://raw.githubusercontent.com/longhorn/longhorn/${LONGHORN_REPO_BRANCH}/deploy/longhorn.yaml"


apply_selinux_workaround(){
  kubectl apply -f "https://raw.githubusercontent.com/longhorn/longhorn/${LONGHORN_REPO_BRANCH}/deploy/prerequisite/longhorn-iscsi-selinux-workaround.yaml"
}


enable_mtls(){
  kubectl apply -f "${TF_VAR_tf_workspace}/templates/longhorn-grpc-tls.yml" -n ${LONGHORN_NAMESPACE}
}


install_csi_snapshotter_crds(){
    CSI_SNAPSHOTTER_REPO_URL="https://github.com/longhorn/csi-snapshotter.git"
    CSI_SNAPSHOTTER_REPO_DIR="${TMPDIR}/k8s-csi-external-snapshotter"

    [[ "${LONGHORN_REPO_URI}" =~ https://([^/]+)/([^/]+)/([^/.]+)(.git)? ]]
    wget "https://raw.githubusercontent.com/${BASH_REMATCH[2]}/${BASH_REMATCH[3]}/${LONGHORN_REPO_BRANCH}/deploy/longhorn-images.txt" -O "/tmp/longhorn-images.txt"
    IFS=: read -ra IMAGE_TAG_PAIR <<< $(grep csi-snapshotter /tmp/longhorn-images.txt)
    CSI_SNAPSHOTTER_REPO_BRANCH="${IMAGE_TAG_PAIR[1]}"

    git clone --single-branch \
              --branch "${CSI_SNAPSHOTTER_REPO_BRANCH}" \
            "${CSI_SNAPSHOTTER_REPO_URL}" \
            "${CSI_SNAPSHOTTER_REPO_DIR}"

    kubectl apply -f ${CSI_SNAPSHOTTER_REPO_DIR}/client/config/crd \
                  -f ${CSI_SNAPSHOTTER_REPO_DIR}/deploy/kubernetes/snapshot-controller
}


wait_longhorn_status_running(){
  local RETRY_COUNTS=10 # in minutes
  local RETRY_INTERVAL="1m"

  # csi and engine image components are installed after longhorn components.
  # it's possible that all longhorn components are running but csi components aren't created yet.
  RETRIES=0
  while [[ -z `kubectl get pods -n ${LONGHORN_NAMESPACE} --no-headers 2>&1 | awk '{print $1}' | grep csi-` ]] || \
    [[ -z `kubectl get pods -n ${LONGHORN_NAMESPACE} --no-headers 2>&1 | awk '{print $1}' | grep engine-image-` ]] || \
    [[ -n `kubectl get pods -n ${LONGHORN_NAMESPACE} --no-headers 2>&1 | awk '{print $3}' | grep -v Running` ]]; do
    echo "Longhorn is still installing ... re-checking in 1m"
    sleep ${RETRY_INTERVAL}
    RETRIES=$((RETRIES+1))

    if [[ ${RETRIES} -eq ${RETRY_COUNTS} ]]; then echo "Error: longhorn installation timeout"; exit 1 ; fi
  done

}


get_longhorn_manifest(){
  wget ${LONGHORN_MANIFEST_URL} -P ${TF_VAR_tf_workspace}
  sed -i ':a;N;$!ba;s/---\n---/---/g' "${TF_VAR_tf_workspace}/longhorn.yaml"
}


customize_longhorn_manifest_for_private_registry(){
  # (1) add secret name to imagePullSecrets.name
  yq -i 'select(.kind == "Deployment" and .metadata.name == "longhorn-driver-deployer").spec.template.spec.imagePullSecrets[0].name="docker-registry-secret"' "${TF_VAR_tf_workspace}/longhorn.yaml"
  yq -i 'select(.kind == "DaemonSet" and .metadata.name == "longhorn-manager").spec.template.spec.imagePullSecrets[0].name="docker-registry-secret"' "${TF_VAR_tf_workspace}/longhorn.yaml"
  yq -i 'select(.kind == "Deployment" and .metadata.name == "longhorn-ui").spec.template.spec.imagePullSecrets[0].name="docker-registry-secret"' "${TF_VAR_tf_workspace}/longhorn.yaml"
  yq -i 'select(.kind == "ConfigMap" and .metadata.name == "longhorn-default-setting").data."default-setting.yaml"="registry-secret: docker-registry-secret"' "${TF_VAR_tf_workspace}/longhorn.yaml"
}


generate_longhorn_yaml_manifest() {
  MANIFEST_BASEDIR="${1}"

  LONGHORN_REPO_URI=${LONGHORN_REPO_URI:-"https://github.com/longhorn/longhorn.git"}
  LONGHORN_REPO_BRANCH=${LONGHORN_REPO_BRANCH:-"master"}
  LONGHORN_REPO_DIR="${TMPDIR}/longhorn"

  CUSTOM_LONGHORN_MANAGER_IMAGE=${CUSTOM_LONGHORN_MANAGER_IMAGE:-"longhornio/longhorn-manager:master-head"}
  CUSTOM_LONGHORN_ENGINE_IMAGE=${CUSTOM_LONGHORN_ENGINE_IMAGE:-"longhornio/longhorn-engine:master-head"}
  CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE=${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE:-""}
  CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE=${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE:-""}
  CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE=${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE:-""}
  CUSTOM_LONGHORN_UI_IMAGE=${CUSTOM_LONGHORN_UI_IMAGE:-""}
  CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE=${CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE:-""}
  CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE=${CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE:-""}
  CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE=${CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE:-""}
  CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE=${CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE:-""}
  CUSTOM_LONGHORN_CSI_RESIZER_IMAGE=${CUSTOM_LONGHORN_CSI_RESIZER_IMAGE:-""}
  CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE=${CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE:-""}
  CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE=${CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE:-""}

  git clone --single-branch \
            --branch ${LONGHORN_REPO_BRANCH} \
            ${LONGHORN_REPO_URI} \
            ${LONGHORN_REPO_DIR}

  cat "${LONGHORN_REPO_DIR}/deploy/longhorn.yaml" > "${MANIFEST_BASEDIR}/longhorn.yaml"
  sed -i ':a;N;$!ba;s/---\n---/---/g' "${MANIFEST_BASEDIR}/longhorn.yaml"

  # get longhorn default images from yaml manifest
  LONGHORN_MANAGER_IMAGE=`grep -io "longhornio\/longhorn-manager:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_ENGINE_IMAGE=`grep -io "longhornio\/longhorn-engine:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_INSTANCE_MANAGER_IMAGE=`grep -io "longhornio\/longhorn-instance-manager:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_SHARE_MANAGER_IMAGE=`grep -io "longhornio\/longhorn-share-manager:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_BACKING_IMAGE_MANAGER_IMAGE=`grep -io "longhornio\/backing-image-manager:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_UI_IMAGE=`grep -io "longhornio\/longhorn-ui:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_SUPPORT_BUNDLE_IMAGE=`grep -io "longhornio\/support-bundle-kit:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_CSI_ATTACHER_IMAGE=`grep -io "longhornio\/csi-attacher:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_CSI_PROVISIONER_IMAGE=`grep -io "longhornio\/csi-provisioner:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE=`grep -io "longhornio\/csi-node-driver-registrar:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_CSI_RESIZER_IMAGE=`grep -io "longhornio\/csi-resizer:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_CSI_SNAPSHOTTER_IMAGE=`grep -io "longhornio\/csi-snapshotter:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`
  LONGHORN_CSI_LIVENESSPROBE_IMAGE=`grep -io "longhornio\/livenessprobe:.*$" "${MANIFEST_BASEDIR}/longhorn.yaml"| head -1 | sed -e 's/^"//' -e 's/"$//'`

  # replace longhorn images with custom images
  if [[ -z "${REGISTRY_URL}" ]]; then
    sed -i 's#'${LONGHORN_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    sed -i 's#'${LONGHORN_ENGINE_IMAGE}'#'${CUSTOM_LONGHORN_ENGINE_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  else
    sed -i 's#'${LONGHORN_MANAGER_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    sed -i 's#'${LONGHORN_ENGINE_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_ENGINE_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  fi

  # replace images if custom image is specified.
  if [[ ! -z ${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_INSTANCE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_INSTANCE_MANAGER_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE=${LONGHORN_INSTANCE_MANAGER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_SHARE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_SHARE_MANAGER_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE=${LONGHORN_SHARE_MANAGER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE=${LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_UI_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_UI_IMAGE}'#'${CUSTOM_LONGHORN_UI_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_UI_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_UI_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_UI_IMAGE=${LONGHORN_UI_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_SUPPORT_BUNDLE_IMAGE}'#'${CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_SUPPORT_BUNDLE_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE=${LONGHORN_SUPPORT_BUNDLE_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_CSI_ATTACHER_IMAGE}'#'${CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_CSI_ATTACHER_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE=${LONGHORN_CSI_ATTACHER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_CSI_PROVISIONER_IMAGE}'#'${CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_CSI_PROVISIONER_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE=${LONGHORN_CSI_PROVISIONER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE}'#'${CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE=${LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_RESIZER_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_CSI_RESIZER_IMAGE}'#'${CUSTOM_LONGHORN_CSI_RESIZER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_CSI_RESIZER_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_CSI_RESIZER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_CSI_RESIZER_IMAGE=${LONGHORN_CSI_RESIZER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_CSI_SNAPSHOTTER_IMAGE}'#'${CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_CSI_SNAPSHOTTER_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE=${LONGHORN_CSI_SNAPSHOTTER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE} ]]; then
    if [[ -z "${REGISTRY_URL}" ]]; then
      sed -i 's#'${LONGHORN_CSI_LIVENESSPROBE_IMAGE}'#'${CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    else
      sed -i 's#'${LONGHORN_CSI_LIVENESSPROBE_IMAGE}'#'${REGISTRY_URL}/${CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
    fi
  else
    CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE=${LONGHORN_CSI_LIVENESSPROBE_IMAGE}
  fi

}


install_longhorn_by_manifest(){
  LONGHORN_MANIFEST_FILE_PATH="${1}"
  kubectl apply -f "${LONGHORN_MANIFEST_FILE_PATH}"
  wait_longhorn_status_running
}


install_backupstores(){
  MINIO_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/backupstores/minio-backupstore.yaml"
  NFS_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/backupstores/nfs-backupstore.yaml"
  kubectl create -f ${MINIO_BACKUPSTORE_URL} \
               -f ${NFS_BACKUPSTORE_URL}
}


main(){
  set_kubeconfig

  if [[ ${DISTRO} == "rhel" ]] || [[ ${DISTRO} == "rockylinux" ]] || [[ ${DISTRO} == "oracle" ]]; then
    apply_selinux_workaround
  fi

  # set debugging mode off to avoid leaking aws secrets to the logs.
  # DON'T REMOVE!
  set +x
  create_aws_secret
  set -x

  create_longhorn_namespace
  if [[ ${CUSTOM_TEST_OPTIONS} != *"--include-cluster-autoscaler-test"* ]]; then
    install_backupstores
  fi
  install_csi_snapshotter_crds
  if [[ "${TF_VAR_enable_mtls}" == true ]]; then
    enable_mtls
  fi

  scale_up_coredns

  # https://github.com/rancherlabs/harvester-access-lab/issues/17
  if [ "$LONGHORN_TEST_CLOUDPROVIDER" == "harvester" ]; then
    echo "LONGHORN_TEST_CLOUDPROVIDER is harvester. Sleeping for 300 seconds..."
    sleep 300s
  fi

  # msg="failed to get package manager" error="operating systems (amzn, sl-micro) are not supported"
  if [[ "${TF_VAR_k8s_distro_name}" != "eks" ]] && \
    [[ "${DISTRO}" != "sle-micro" ]]; then
    longhornctl_check
  fi

  create_registry_secret
  get_longhorn_manifest
  generate_longhorn_yaml_manifest "${TF_VAR_tf_workspace}"
  if [[ "${AIR_GAP_INSTALLATION}" == true ]]; then
    customize_longhorn_manifest_for_private_registry
  fi
  install_longhorn_by_manifest "${TF_VAR_tf_workspace}/longhorn.yaml"
  setup_longhorn_ui_nodeport
  export_longhorn_ui_url
  run_longhorn_test

}

main
