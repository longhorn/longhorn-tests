install_csi_snapshotter(){
  CSI_SNAPSHOTTER_REPO_URL="https://github.com/kubernetes-csi/external-snapshotter.git"
  CSI_SNAPSHOTTER_REPO_BRANCH="v8.3.0"
  CSI_SNAPSHOTTER_REPO_DIR="${TMPDIR}/k8s-csi-external-snapshotter"

  git clone --single-branch \
            --branch "${CSI_SNAPSHOTTER_REPO_BRANCH}" \
            "${CSI_SNAPSHOTTER_REPO_URL}" \
            "${CSI_SNAPSHOTTER_REPO_DIR}"

  kubectl apply -f "${CSI_SNAPSHOTTER_REPO_DIR}/client/config/crd" \
                -f "${CSI_SNAPSHOTTER_REPO_DIR}/deploy/kubernetes/snapshot-controller"
}