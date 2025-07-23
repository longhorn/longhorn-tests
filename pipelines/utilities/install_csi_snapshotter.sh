install_csi_snapshotter(){
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
