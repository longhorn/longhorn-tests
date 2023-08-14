source pipelines/utilities/longhorn_status.sh


get_longhorn_chart(){
  CHART_VERSION="${1:-$LONGHORN_REPO_BRANCH}"
  git clone --single-branch \
            --branch "${CHART_VERSION}" \
            "${LONGHORN_REPO_URI}" \
            "${LONGHORN_REPO_DIR}"
}


customize_longhorn_chart_registry(){
  # specify private registry secret in chart/values.yaml
  yq -i '.privateRegistry.createSecret=true' "${LONGHORN_REPO_DIR}/chart/values.yaml"
  yq -i ".privateRegistry.registryUrl=\"${REGISTRY_URL}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
  yq -i ".privateRegistry.registryUser=\"${REGISTRY_USERNAME}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
  yq -i ".privateRegistry.registryPasswd=\"${REGISTRY_PASSWORD}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
  yq -i '.privateRegistry.registrySecret="docker-registry-secret"' "${LONGHORN_REPO_DIR}/chart/values.yaml"
}


customize_longhorn_chart(){
  # customize longhorn components repository and tag (version) in chart/values.yaml
  IFS=':'
  if [[ -n "${CUSTOM_LONGHORN_MANAGER_IMAGE}" ]]; then
    read -ra ARR <<< "${CUSTOM_LONGHORN_MANAGER_IMAGE}"
    yq -i ".image.longhorn.manager.repository=\"${ARR[0]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
    yq -i ".image.longhorn.manager.tag=\"${ARR[1]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
  fi
  if [[ -n "${CUSTOM_LONGHORN_ENGINE_IMAGE}" ]]; then
    read -ra ARR <<< "${CUSTOM_LONGHORN_ENGINE_IMAGE}"
    yq -i ".image.longhorn.engine.repository=\"${ARR[0]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
    yq -i ".image.longhorn.engine.tag=\"${ARR[1]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
  fi
  if [[ -n "${CUSTOM_LONGHORN_UI_IMAGE}" ]]; then
    read -ra ARR <<< "${CUSTOM_LONGHORN_UI_IMAGE}"
    yq -i ".image.longhorn.ui.repository=\"${ARR[0]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
    yq -i ".image.longhorn.ui.tag=\"${ARR[1]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
  fi
  if [[ -n "${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}" ]]; then
    read -ra ARR <<< "${CUSTOM_LONGHORN_INSTANCE_MANAGER_IMAGE}"
    yq -i ".image.longhorn.instanceManager.repository=\"${ARR[0]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
    yq -i ".image.longhorn.instanceManager.tag=\"${ARR[1]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
  fi
  if [[ -n "${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE}" ]]; then
    read -ra ARR <<< "${CUSTOM_LONGHORN_SHARE_MANAGER_IMAGE}"
    yq -i ".image.longhorn.shareManager.repository=\"${ARR[0]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
    yq -i ".image.longhorn.shareManager.tag=\"${ARR[1]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
  fi
  if [[ -n "${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}" ]]; then
    read -ra ARR <<< "${CUSTOM_LONGHORN_BACKING_IMAGE_MANAGER_IMAGE}"
    yq -i ".image.longhorn.backingImageManager.repository=\"${ARR[0]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
    yq -i ".image.longhorn.backingImageManager.tag=\"${ARR[1]}\"" "${LONGHORN_REPO_DIR}/chart/values.yaml"
  fi
}


install_longhorn(){
  helm upgrade --install longhorn "${LONGHORN_REPO_DIR}/chart/" --namespace "${LONGHORN_NAMESPACE}"
  wait_longhorn_status_running
}