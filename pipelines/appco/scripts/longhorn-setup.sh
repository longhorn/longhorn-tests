#!/usr/bin/env bash

set -x

source pipelines/utilities/kubeconfig.sh
source pipelines/utilities/longhorn_manifest.sh
source pipelines/utilities/longhorn_ui.sh
source pipelines/utilities/install_metrics_server.sh
source pipelines/utilities/coredns.sh

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
LONGHORN_MANIFEST_URL="https://raw.githubusercontent.com/longhorn/longhorn/${LONGHORN_INSTALL_VERSION}/deploy/longhorn.yaml"

# for install Longhorn by helm chart
LONGHORN_REPO_URL="https://github.com/longhorn/longhorn"
LONGHORN_REPO_DIR="${TMPDIR}/longhorn"


create_admin_service_account(){
  kubectl apply -f "${TF_VAR_tf_workspace}/templates/kubeconfig_service_account.yaml"
  TOKEN=$(kubectl -n kube-system get secret/kubeconfig-cluster-admin-token -o=go-template='{{.data.token}}' | base64 -d)
  yq -i ".users[0].user.token=\"${TOKEN}\""  "${TF_VAR_tf_workspace}/eks.yml"
}


apply_selinux_workaround(){
  kubectl apply -f "https://raw.githubusercontent.com/longhorn/longhorn/${LONGHORN_REPO_BRANCH}/deploy/prerequisite/longhorn-iscsi-selinux-workaround.yaml"
}


install_iscsi(){
  kubectl apply -f "https://raw.githubusercontent.com/longhorn/longhorn/${LONGHORN_REPO_BRANCH}/deploy/prerequisite/longhorn-iscsi-installation.yaml"
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


get_longhorn_chart(){
  git clone --single-branch \
            --branch "${LONGHORN_REPO_BRANCH}" \
            "${LONGHORN_REPO_URI}" \
            "${LONGHORN_REPO_DIR}"
}


create_registry_secret(){
  kubectl -n ${LONGHORN_NAMESPACE} create secret docker-registry docker-registry-secret --docker-server=${REGISTRY_URL} --docker-username=${REGISTRY_USERNAME} --docker-password=${REGISTRY_PASSWORD}
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
  sed -i 's#'${LONGHORN_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  sed -i 's#'${LONGHORN_ENGINE_IMAGE}'#'${CUSTOM_LONGHORN_ENGINE_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"

  # replace images if custom image is specified.
  if [[ ! -z ${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_INSTANCE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  else
    # use instance-manager image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE=${LONGHORN_INSTANCE_MANAGER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_SHARE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  else
    # use share-manager image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE=${LONGHORN_SHARE_MANAGER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}'#'${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  else
    # use backing-image-manager image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE=${LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_UI_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_UI_IMAGE}'#'${CUSTOM_LONGHORN_UI_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  else
    # use ui image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_UI_IMAGE=${LONGHORN_UI_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_SUPPORT_BUNDLE_IMAGE}'#'${CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  else
    # use support bundle image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE=${LONGHORN_SUPPORT_BUNDLE_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_CSI_ATTACHER_IMAGE}'#'${CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  else
    # use csi attacher image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE=${LONGHORN_CSI_ATTACHER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_CSI_PROVISIONER_IMAGE}'#'${CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  else
    # use csi provisioner image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE=${LONGHORN_CSI_PROVISIONER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE}'#'${CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  else
    # use csi node driver registrar image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE=${LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_RESIZER_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_CSI_RESIZER_IMAGE}'#'${CUSTOM_LONGHORN_CSI_RESIZER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  else
    # use csi resizer image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_CSI_RESIZER_IMAGE=${LONGHORN_CSI_RESIZER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_CSI_SNAPSHOTTER_IMAGE}'#'${CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  else
    # use csi snapshotter image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE=${LONGHORN_CSI_SNAPSHOTTER_IMAGE}
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE} ]]; then
    sed -i 's#'${LONGHORN_CSI_LIVENESSPROBE_IMAGE}'#'${CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE}'#' "${MANIFEST_BASEDIR}/longhorn.yaml"
  else
    # use csi liveness probe image specified in yaml file if custom image is not specified
    CUSTOM_LONGHORN_BACKING_IMACUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGEGE_MANAGER_IMAGE=${LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}
  fi

}


install_longhorn_by_manifest(){
  LONGHORN_MANIFEST_FILE_PATH="${1}"
  kubectl apply -f "${LONGHORN_MANIFEST_FILE_PATH}"
  wait_longhorn_status_running
}


install_longhorn_by_chart(){
  CUSTOM_LONGHORN_MANAGER_IMAGE=${CUSTOM_LONGHORN_MANAGER_IMAGE:-"longhornio/longhorn-manager:master-head"}
  CUSTOM_LONGHORN_ENGINE_IMAGE=${CUSTOM_LONGHORN_ENGINE_IMAGE:-"longhornio/longhorn-engine:master-head"}

  CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE=${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE:-""}
  CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE=${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE:-""}
  CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE=${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE:-""}

  HELM_VARIABLES=("--set enableGoCoverDir=true")
  CUSTOM_LONGHORN_MANAGER_IMAGE_REPO=$(echo $CUSTOM_LONGHORN_MANAGER_IMAGE | cut -d ":" -f 1)
  CUSTOM_LONGHORN_MANAGER_IMAGE_TAG=$(echo $CUSTOM_LONGHORN_MANAGER_IMAGE | cut -d ":" -f 2)
  HELM_VARIABLES+=("--set image.longhorn.manager.repository=${CUSTOM_LONGHORN_MANAGER_IMAGE_REPO}")
  HELM_VARIABLES+=("--set image.longhorn.manager.tag=${CUSTOM_LONGHORN_MANAGER_IMAGE_TAG}")

  CUSTOM_LONGHORN_ENGINE_IMAGE_REPO=$(echo $CUSTOM_LONGHORN_ENGINE_IMAGE | cut -d ":" -f 1)
  CUSTOM_LONGHORN_ENGINE_IMAGE_TAG=$(echo $CUSTOM_LONGHORN_ENGINE_IMAGE | cut -d ":" -f 2)
  HELM_VARIABLES+=("--set image.longhorn.engine.repository=${CUSTOM_LONGHORN_ENGINE_IMAGE_REPO}")
  HELM_VARIABLES+=("--set image.longhorn.engine.tag=${CUSTOM_LONGHORN_ENGINE_IMAGE_TAG}")

  # replace images if custom image is specified.
  if [[ ! -z ${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE} ]]; then
    CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE_REPO=$(echo $CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE | cut -d ":" -f 1)
    CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE_TAG=$(echo $CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE | cut -d ":" -f 2)
    HELM_VARIABLES+=("--set image.longhorn.instanceManager.repository=${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE_REPO}")
    HELM_VARIABLES+=("--set image.longhorn.instanceManager.tag=${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE_TAG}")
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE} ]]; then
    CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE_REPO=$(echo $CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE | cut -d ":" -f 1)
    CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE_TAG=$(echo $CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE | cut -d ":" -f 2)
    HELM_VARIABLES+=("--set image.longhorn.shareManager.repository=${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE_REPO}")
    HELM_VARIABLES+=("--set image.longhorn.shareManager.tag=${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE_TAG}")
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE} ]]; then
    CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE_REPO=$(echo $CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE | cut -d ":" -f 1)
    CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE_TAG=$(echo $CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE | cut -d ":" -f 2)
    HELM_VARIABLES+=("--set image.longhorn.backingImageManager.repository=${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE_REPO}")
    HELM_VARIABLES+=("--set image.longhorn.backingImageManager.tag=${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE_TAG}")
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_UI_IMAGE} ]]; then
    CUSTOM_LONGHORN_UI_IMAGE_REPO=$(echo $CUSTOM_LONGHORN_UI_IMAGE | cut -d ":" -f 1)
    CUSTOM_LONGHORN_UI_IMAGE_TAG=$(echo $CUSTOM_LONGHORN_UI_IMAGE | cut -d ":" -f 2)
    HELM_VARIABLES+=("--set image.longhorn.ui.repository=${CUSTOM_LONGHORN_UI_IMAGE_REPO}")
    HELM_VARIABLES+=("--set image.longhorn.ui.tag=${CUSTOM_LONGHORN_UI_IMAGE_TAG}")
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE} ]]; then
    CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE_REPO=$(echo $CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE | cut -d ":" -f 1)
    CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE_TAG=$(echo $CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE | cut -d ":" -f 2)
    HELM_VARIABLES+=("--set image.longhorn.supportBundleKit.repository=${CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE_REPO}")
    HELM_VARIABLES+=("--set image.longhorn.supportBundleKit.tag=${CUSTOM_LONGHORN_SUPPORT_BUNDLE_IMAGE_TAG}")
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE} ]]; then
    CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE_REPO=$(echo $CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE | cut -d ":" -f 1)
    CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE_TAG=$(echo $CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE | cut -d ":" -f 2)
    HELM_VARIABLES+=("--set image.csi.attacher.repository=${CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE_REPO}")
    HELM_VARIABLES+=("--set image.csi.attacher.tag=${CUSTOM_LONGHORN_CSI_ATTACHER_IMAGE_TAG}")
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE} ]]; then
    CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE_REPO=$(echo $CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE | cut -d ":" -f 1)
    CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE_TAG=$(echo $CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE | cut -d ":" -f 2)
    HELM_VARIABLES+=("--set image.csi.provisioner.repository=${CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE_REPO}")
    HELM_VARIABLES+=("--set image.csi.provisioner.tag=${CUSTOM_LONGHORN_CSI_PROVISIONER_IMAGE_TAG}")
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE} ]]; then
    CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE_REPO=$(echo $CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE | cut -d ":" -f 1)
    CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE_TAG=$(echo $CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE | cut -d ":" -f 2)
    HELM_VARIABLES+=("--set image.csi.nodeDriverRegistrar.repository=${CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE_REPO}")
    HELM_VARIABLES+=("--set image.csi.nodeDriverRegistrar.tag=${CUSTOM_LONGHORN_CSI_NODE_DRIVER_REGISTRAR_IMAGE_TAG}")
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_RESIZER_IMAGE} ]]; then
    CUSTOM_LONGHORN_CSI_RESIZER_IMAGE_REPO=$(echo $CUSTOM_LONGHORN_CSI_RESIZER_IMAGE | cut -d ":" -f 1)
    CUSTOM_LONGHORN_CSI_RESIZER_IMAGE_TAG=$(echo $CUSTOM_LONGHORN_CSI_RESIZER_IMAGE | cut -d ":" -f 2)
    HELM_VARIABLES+=("--set image.csi.resizer.repository=${CUSTOM_LONGHORN_CSI_RESIZER_IMAGE_REPO}")
    HELM_VARIABLES+=("--set image.csi.resizer.tag=${CUSTOM_LONGHORN_CSI_RESIZER_IMAGE_TAG}")
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE} ]]; then
    CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE_REPO=$(echo $CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE | cut -d ":" -f 1)
    CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE_TAG=$(echo $CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE | cut -d ":" -f 2)
    HELM_VARIABLES+=("--set image.csi.snapshotter.repository=${CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE_REPO}")
    HELM_VARIABLES+=("--set image.csi.snapshotter.tag=${CUSTOM_LONGHORN_CSI_SNAPSHOTTER_IMAGE_TAG}")
  fi

  if [[ ! -z ${CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE} ]]; then
    CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE_REPO=$(echo $CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE | cut -d ":" -f 1)
    CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE_TAG=$(echo $CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE | cut -d ":" -f 2)
    HELM_VARIABLES+=("--set image.csi.livenessProbe.repository=${CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE_REPO}")
    HELM_VARIABLES+=("--set image.csi.livenessProbe.tag=${CUSTOM_LONGHORN_CSI_LIVENESSPROBE_IMAGE_TAG}")
  fi

  HELM_VARIABLE_STR=$( printf " %s" "${HELM_VARIABLES[@]}" )
  echo ${HELM_VARIABLE_STR}

  helm install longhorn "${LONGHORN_REPO_DIR}/chart/" --namespace longhorn-system --create-namespace $HELM_VARIABLE_STR
  wait_longhorn_status_running
}

uninstall_longhorn_by_chart() {
  kubectl patch lhs -n longhorn-system deleting-confirmation-flag --type=json --patch-file=/dev/stdin <<-EOF
[
  {
    "op": "replace",
    "path": "/value",
    "value": "true"
  }
]
EOF
  helm uninstall longhorn --namespace longhorn-system
}

install_longhorn_stable(){
  install_longhorn_by_manifest "${LONGHORN_STABLE_MANIFEST_URL}"
}


create_longhorn_namespace(){
  kubectl create ns ${LONGHORN_NAMESPACE}
  if [[ "${TF_VAR_cis_hardening}" == true ]] || [[ "${DISTRO}" == "talos" ]]; then
    kubectl label ns default ${LONGHORN_NAMESPACE} pod-security.kubernetes.io/enforce=privileged
    kubectl label ns default ${LONGHORN_NAMESPACE} pod-security.kubernetes.io/enforce-version=latest
    kubectl label ns default ${LONGHORN_NAMESPACE} pod-security.kubernetes.io/audit=privileged
    kubectl label ns default ${LONGHORN_NAMESPACE} pod-security.kubernetes.io/audit-version=latest
    kubectl label ns default ${LONGHORN_NAMESPACE} pod-security.kubernetes.io/warn=privileged
    kubectl label ns default ${LONGHORN_NAMESPACE} pod-security.kubernetes.io/warn-version=latest
  fi
}


install_backupstores(){
  MINIO_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn-tests/${LONGHORN_REPO_BRANCH}/manager/integration/deploy/backupstores/minio-backupstore.yaml"
  NFS_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn-tests/${LONGHORN_REPO_BRANCH}/manager/integration/deploy/backupstores/nfs-backupstore.yaml"
  CIFS_BACKUPSTORE_URL="https://raw.githubusercontent.com/longhorn/longhorn/${LONGHORN_REPO_BRANCH}/deploy/backupstores/cifs-backupstore.yaml"
  kubectl create -f ${MINIO_BACKUPSTORE_URL} \
               -f ${NFS_BACKUPSTORE_URL} \
               -f ${CIFS_BACKUPSTORE_URL}
}


create_aws_secret(){
  AWS_ACCESS_KEY_ID_BASE64=`echo -n "${TF_VAR_lh_aws_access_key}" | base64`
  AWS_SECRET_ACCESS_KEY_BASE64=`echo -n "${TF_VAR_lh_aws_secret_key}" | base64`
  AWS_DEFAULT_REGION_BASE64=`echo -n "${TF_VAR_aws_region}" | base64`

  yq e -i '.data.AWS_ACCESS_KEY_ID |= "'${AWS_ACCESS_KEY_ID_BASE64}'"' "${TF_VAR_tf_workspace}/templates/aws_cred_secrets.yml"
  yq e -i '.data.AWS_SECRET_ACCESS_KEY |= "'${AWS_SECRET_ACCESS_KEY_BASE64}'"' "${TF_VAR_tf_workspace}/templates/aws_cred_secrets.yml"
  yq e -i '.data.AWS_DEFAULT_REGION |= "'${AWS_DEFAULT_REGION_BASE64}'"' "${TF_VAR_tf_workspace}/templates/aws_cred_secrets.yml"

  kubectl apply -f "${TF_VAR_tf_workspace}/templates/aws_cred_secrets.yml"
  kubectl apply -f "${TF_VAR_tf_workspace}/templates/aws_cred_secrets.yml" -n kube-system
}


longhornctl_check(){
  curl -L https://github.com/longhorn/cli/releases/download/v1.7.2/longhornctl-linux-amd64 -o longhornctl
  chmod +x longhornctl
  ./longhornctl install preflight
  ./longhornctl check preflight
  if [[ -n $(./longhornctl check preflight 2>&1 | grep error) ]]; then
    exit 1
  fi
}


run_longhorn_upgrade_test(){
  LONGHORN_TESTS_CUSTOM_IMAGE=${LONGHORN_TESTS_CUSTOM_IMAGE:-"longhornio/longhorn-manager-test:master-head"}

  LONGHORN_TESTS_MANIFEST_FILE_PATH="${WORKSPACE}/manager/integration/deploy/test.yaml"
  LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH="${WORKSPACE}/manager/integration/deploy/upgrade_test.yaml"

  LONGHORN_JUNIT_REPORT_PATH=`yq e '.spec.containers[0].env[] | select(.name == "LONGHORN_JUNIT_REPORT_PATH").value' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"`

  local PYTEST_COMMAND_ARGS='''"-s",
                                 "--junitxml='${LONGHORN_JUNIT_REPORT_PATH}'",
                                 "--include-upgrade-test",
                                 "-k", "test_upgrade",
                                 "--upgrade-lh-transient-version", "'${UPGRADE_LH_TRANSIENT_VERSION}'",
                                 "--upgrade-lh-repo-url", "'${UPGRADE_LH_REPO_URL}'",
                                 "--upgrade-lh-repo-branch", "'${UPGRADE_LH_REPO_BRANCH}'",
                                 "--upgrade-lh-manager-image", "'${UPGRADE_LH_MANAGER_IMAGE}'",
                                 "--upgrade-lh-engine-image", "'${UPGRADE_LH_ENGINE_IMAGE}'",
                                 "--upgrade-lh-instance-manager-image", "'${UPGRADE_LH_INSTANCE_MANAGER_IMAGE}'",
                                 "--upgrade-lh-share-manager-image", "'${UPGRADE_LH_SHARE_MANAGER_IMAGE}'",
                                 "--upgrade-lh-backing-image-manager-image", "'${UPGRADE_LH_BACKING_IMAGE_MANAGER_IMAGE}'"
                              '''

  ## generate upgrade_test pod manifest
  yq e 'select(.spec.containers[0] != null).spec.containers[0].args=['"${PYTEST_COMMAND_ARGS}"']' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}" > ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].image="'${LONGHORN_TESTS_CUSTOM_IMAGE}'"' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}
  yq e -i 'select(.spec.containers[0] != null).metadata.name="'${LONGHORN_UPGRADE_TEST_POD_NAME}'"' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}

  if [[ $BACKUP_STORE_TYPE = "s3" ]]; then
    BACKUP_STORE_FOR_TEST=`yq e 'select(.spec.containers[0] != null).spec.containers[0].env[1].value' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH} | awk -F ',' '{print $1}' | sed 's/ *//'`
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[1].value="'${BACKUP_STORE_FOR_TEST}'"' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}
  elif [[ $BACKUP_STORE_TYPE = "nfs" ]]; then
    BACKUP_STORE_FOR_TEST=`yq e 'select(.spec.containers[0] != null).spec.containers[0].env[1].value' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH} | awk -F ',' '{print $2}' | sed 's/ *//'`
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[1].value="'${BACKUP_STORE_FOR_TEST}'"' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}
  elif [[ $BACKUP_STORE_TYPE = "cifs" ]]; then
    BACKUP_STORE_FOR_TEST=`yq e 'select(.spec.containers[0] != null).spec.containers[0].env[1].value' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH} | awk -F ',' '{print $3}' | sed 's/ *//'`
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[1].value="'${BACKUP_STORE_FOR_TEST}'"' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}
  elif [[ $BACKUP_STORE_TYPE = "azurite" ]]; then
    BACKUP_STORE_FOR_TEST=`yq e 'select(.spec.containers[0] != null).spec.containers[0].env[1].value' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH} | awk -F ',' '{print $4}' | sed 's/ *//'`
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[1].value="'${BACKUP_STORE_FOR_TEST}'"' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}
  fi

  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[4].value="'${LONGHORN_UPGRADE_TYPE}'"' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}

  RESOURCE_SUFFIX=$(terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw resource_suffix)
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[7].value="'${RESOURCE_SUFFIX}'"' ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}

  ## for v2 volume test
  yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "RUN_V2_TEST", "value": "'${RUN_V2_TEST}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"
  yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "LONGHORN_TEST_CLOUDPROVIDER", "value": "'${LONGHORN_TEST_CLOUDPROVIDER}'"}' "${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}"

  kubectl apply -f ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}

  # wait upgrade test pod to start running
  while [[ -n "`kubectl get pod ${LONGHORN_UPGRADE_TEST_POD_NAME} -o=jsonpath='{.status.containerStatuses[?(@.name=="longhorn-test")].state}' | grep -v \"running\|terminated\"`"  ]]; do
    echo "waiting upgrade test pod to be in running state ... rechecking in 10s"
    sleep 10s
  done

    # wait upgrade test to complete
  while [[ -n "`kubectl get pod ${LONGHORN_UPGRADE_TEST_POD_NAME} -o=jsonpath='{.status.containerStatuses[?(@.name=="longhorn-test")].state}' | grep \"running\"`"  ]]; do
    kubectl logs ${LONGHORN_UPGRADE_TEST_POD_NAME} -c longhorn-test -f --since=10s
  done

  # get upgrade test junit xml report
  kubectl cp ${LONGHORN_UPGRADE_TEST_POD_NAME}:${LONGHORN_JUNIT_REPORT_PATH} "${TF_VAR_tf_workspace}/${LONGHORN_UPGRADE_TEST_POD_NAME}-junit-report.xml" -c longhorn-test-report

  # delete upgrade test pod
  kubectl delete -f ${LONGHORN_UPGRADE_TESTS_MANIFEST_FILE_PATH}
}


run_longhorn_tests(){
  LONGHORN_TESTS_CUSTOM_IMAGE=${LONGHORN_TESTS_CUSTOM_IMAGE:-"longhornio/longhorn-manager-test:master-head"}

  LONGHORN_TESTS_MANIFEST_FILE_PATH="${WORKSPACE}/manager/integration/deploy/test.yaml"

  LONGHORN_JUNIT_REPORT_PATH=`yq e '.spec.containers[0].env[] | select(.name == "LONGHORN_JUNIT_REPORT_PATH").value' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"`

  local PYTEST_COMMAND_ARGS='"-s", "--junitxml='${LONGHORN_JUNIT_REPORT_PATH}'"'
  if [[ -n ${PYTEST_CUSTOM_OPTIONS} ]]; then
    PYTEST_CUSTOM_OPTIONS=(${PYTEST_CUSTOM_OPTIONS})
    for OPT in "${PYTEST_CUSTOM_OPTIONS[@]}"; do
      PYTEST_COMMAND_ARGS=${PYTEST_COMMAND_ARGS}', "'${OPT}'"'
    done
  fi

  ## generate test pod manifest
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].args=['"${PYTEST_COMMAND_ARGS}"']' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].image="'${LONGHORN_TESTS_CUSTOM_IMAGE}'"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}

  if [[ $BACKUP_STORE_TYPE = "s3" ]]; then
    BACKUP_STORE_FOR_TEST=`yq e 'select(.spec.containers[0] != null).spec.containers[0].env[1].value' ${LONGHORN_TESTS_MANIFEST_FILE_PATH} | awk -F ',' '{print $1}' | sed 's/ *//'`
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[1].value="'${BACKUP_STORE_FOR_TEST}'"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  elif [[ $BACKUP_STORE_TYPE = "nfs" ]]; then
    BACKUP_STORE_FOR_TEST=`yq e 'select(.spec.containers[0] != null).spec.containers[0].env[1].value' ${LONGHORN_TESTS_MANIFEST_FILE_PATH} | awk -F ',' '{print $2}' | sed 's/ *//'`
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[1].value="'${BACKUP_STORE_FOR_TEST}'"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  elif [[ $BACKUP_STORE_TYPE = "cifs" ]]; then
    BACKUP_STORE_FOR_TEST=`yq e 'select(.spec.containers[0] != null).spec.containers[0].env[1].value' ${LONGHORN_TESTS_MANIFEST_FILE_PATH} | awk -F ',' '{print $3}' | sed 's/ *//'`
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[1].value="'${BACKUP_STORE_FOR_TEST}'"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  elif [[ $BACKUP_STORE_TYPE = "azurite" ]]; then
    BACKUP_STORE_FOR_TEST=`yq e 'select(.spec.containers[0] != null).spec.containers[0].env[1].value' ${LONGHORN_TESTS_MANIFEST_FILE_PATH} | awk -F ',' '{print $4}' | sed 's/ *//'`
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[1].value="'${BACKUP_STORE_FOR_TEST}'"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  fi

  if [[ "${TF_VAR_use_hdd}" == true ]]; then
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[3].value="hdd"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  fi

  if [[ "${TF_VAR_k8s_distro_name}" == "eks" ]] || [[ "${TF_VAR_k8s_distro_name}" == "aks" ]]; then
    yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[6].value="true"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}
  fi

  set +x
  ## inject aws cloudprovider and credentials env variables from created secret
  yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "CLOUDPROVIDER", "value": "aws"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "AWS_ACCESS_KEY_ID", "valueFrom": {"secretKeyRef": {"name": "aws-cred-secret", "key": "AWS_ACCESS_KEY_ID"}}}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "AWS_SECRET_ACCESS_KEY", "valueFrom": {"secretKeyRef": {"name": "aws-cred-secret", "key": "AWS_SECRET_ACCESS_KEY"}}}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "AWS_DEFAULT_REGION", "valueFrom": {"secretKeyRef": {"name": "aws-cred-secret", "key": "AWS_DEFAULT_REGION"}}}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  set -x

  ## for v2 volume test
  yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "RUN_V2_TEST", "value": "'${RUN_V2_TEST}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"
  yq e -i 'select(.spec.containers[0].env != null).spec.containers[0].env += {"name": "LONGHORN_TEST_CLOUDPROVIDER", "value": "'${LONGHORN_TEST_CLOUDPROVIDER}'"}' "${LONGHORN_TESTS_MANIFEST_FILE_PATH}"

  LONGHORN_TEST_POD_NAME=`yq e 'select(.spec.containers[0] != null).metadata.name' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}`

  RESOURCE_SUFFIX=$(terraform -chdir=${TF_VAR_tf_workspace}/terraform/${LONGHORN_TEST_CLOUDPROVIDER}/${DISTRO} output -raw resource_suffix)
  yq e -i 'select(.spec.containers[0] != null).spec.containers[0].env[7].value="'${RESOURCE_SUFFIX}'"' ${LONGHORN_TESTS_MANIFEST_FILE_PATH}

  kubectl apply -f ${LONGHORN_TESTS_MANIFEST_FILE_PATH}


  local RETRY_COUNTS=60
  local RETRIES=0
  # wait longhorn tests pod to start running
  while [[ -n "`kubectl get pod longhorn-test -o=jsonpath='{.status.containerStatuses[?(@.name=="longhorn-test")].state}' | grep -v \"running\|terminated\"`"  ]]; do
    echo "waiting longhorn test pod to be in running state ... rechecking in 10s"
    sleep 10s
    RETRIES=$((RETRIES+1))

    if [[ ${RETRIES} -eq ${RETRY_COUNTS} ]]; then echo "Error: longhorn test pod start timeout"; exit 1 ; fi
  done

  # wait longhorn tests to complete
  while [[ "`kubectl get pod longhorn-test -o=jsonpath='{.status.containerStatuses[?(@.name=="longhorn-test")].state}' 2>&1 | grep -v \"terminated\"`"  ]]; do
    kubectl logs ${LONGHORN_TEST_POD_NAME} -c longhorn-test -f --since=10s
  done

  kubectl cp ${LONGHORN_TEST_POD_NAME}:${LONGHORN_JUNIT_REPORT_PATH} "${TF_VAR_tf_workspace}/longhorn-test-junit-report.xml" -c longhorn-test-report
}


main(){

  set_kubeconfig

  create_longhorn_namespace

  if [[ ${DISTRO} == "rhel" ]] || [[ ${DISTRO} == "rockylinux" ]] || [[ ${DISTRO} == "oracle" ]]; then
    apply_selinux_workaround
  fi

  # set debugging mode off to avoid leaking aws secrets to the logs.
  # DON'T REMOVE!
  set +x
  create_aws_secret
  set -x

  install_backupstores
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

  # msg="failed to get package manager" error="operating systems amzn are not supported"
  if [[ "${TF_VAR_k8s_distro_name}" != "eks" ]] && \
    [[ "${DISTRO}" != "talos" ]]; then
    longhornctl_check
  fi

  generate_longhorn_yaml_manifest "${TF_VAR_tf_workspace}"
  # set debugging mode off to avoid leaking docker secrets to the logs.
  # DON'T REMOVE!
  set +x
  create_registry_secret
  set -x
  customize_longhorn_manifest_registry

  if [[ "${LONGHORN_UPGRADE_TEST}" == true ]]; then
    install_longhorn_stable
    LONGHORN_UPGRADE_TEST_POD_NAME="longhorn-test-upgrade"
    UPGRADE_LH_TRANSIENT_VERSION="${LONGHORN_TRANSIENT_VERSION}"
    UPGRADE_LH_REPO_URL="${LONGHORN_REPO_URI}"
    UPGRADE_LH_REPO_BRANCH="${LONGHORN_REPO_BRANCH}"
    UPGRADE_LH_MANAGER_IMAGE="${CUSTOM_LONGHORN_MANAGER_IMAGE}"
    UPGRADE_LH_ENGINE_IMAGE="${CUSTOM_LONGHORN_ENGINE_IMAGE}"
    UPGRADE_LH_INSTANCE_MANAGER_IMAGE="${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}"
    UPGRADE_LH_SHARE_MANAGER_IMAGE="${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE}"
    UPGRADE_LH_BACKING_IMAGE_MANAGER_IMAGE="${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}"
    setup_longhorn_ui_nodeport
    export_longhorn_ui_url
    run_longhorn_upgrade_test
    run_longhorn_tests
  else
    install_longhorn_by_manifest "${TF_VAR_tf_workspace}/longhorn.yaml"
    setup_longhorn_ui_nodeport
    export_longhorn_ui_url
    run_longhorn_tests
  fi
}

main
