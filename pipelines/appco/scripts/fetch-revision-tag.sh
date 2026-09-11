#!/usr/bin/env bash

API_URL="https://api.apps.rancher.io/v1/artifacts"
PAGE_SIZE=100
SLEEP_SECONDS=0.2
CURL_TIMEOUT=10
MAX_PAGES_PER_COMPONENT=50
MAX_TOTAL_API_CALLS=500
TARGET_LONGHORN_VERSION="${TARGET_LONGHORN_VERSION:-1.11.2}"
TOTAL_API_CALLS=0

LONGHORN_COMPONENTS=(
  longhorn-backing-image-manager longhorn-engine longhorn-instance-manager
  longhorn-manager longhorn-share-manager longhorn-ui
)

DEPENDENCY_COMPONENTS=(
  kubernetes-csi-external-attacher kubernetes-csi-external-provisioner
  kubernetes-csi-external-resizer kubernetes-csi-external-snapshotter
  kubernetes-csi-livenessprobe kubernetes-csi-node-driver-registrar
  rancher-support-bundle-kit
)

declare -A COMPONENT_PATHS=(
  [kubernetes-csi-external-attacher]='.image.csi.attacher.tag'
  [kubernetes-csi-external-provisioner]='.image.csi.provisioner.tag'
  [kubernetes-csi-external-resizer]='.image.csi.resizer.tag'
  [kubernetes-csi-external-snapshotter]='.image.csi.snapshotter.tag'
  [kubernetes-csi-livenessprobe]='.image.csi.livenessProbe.tag'
  [kubernetes-csi-node-driver-registrar]='.image.csi.nodeDriverRegistrar.tag'
  [rancher-support-bundle-kit]='.image.longhorn.supportBundleKit.tag'
  [longhorn-backing-image-manager]='.image.longhorn.backingImageManager.tag'
  [longhorn-engine]='.image.longhorn.engine.tag'
  [longhorn-instance-manager]='.image.longhorn.instanceManager.tag'
  [longhorn-manager]='.image.longhorn.manager.tag'
  [longhorn-share-manager]='.image.longhorn.shareManager.tag'
  [longhorn-ui]='.image.longhorn.ui.tag'
)

declare -A COMPONENT_VERSIONS COMPONENT_TAGS COMPONENT_ARTIFACT_NAMES COMPONENT_CHART_TAGS

to_env_name() {
  echo "${1}_tag" | tr '[:lower:]-' '[:upper:]_'
}

get_chart_values() {
  local chart_version="${1%%-*}" values_output

  echo "INFO: Fetching Helm chart values for suse-storage version ${chart_version}" >&2
  if ! values_output="$(helm show values \
      "oci://dp.apps.rancher.io/charts/suse-storage" --version "$chart_version" 2>&1)"; then
    echo "ERROR: Failed to fetch Helm chart values for suse-storage version ${chart_version}" >&2
    echo "$values_output" >&2
    exit 1
  fi

  echo "$values_output" | grep -vE '^(Pulled|Digest):'
}

parse_component_versions() {
  local values component tag
  values="$(get_chart_values "$1")"

  for component in "${DEPENDENCY_COMPONENTS[@]}"; do
    tag="$(echo "$values" | yq eval "${COMPONENT_PATHS[$component]}" -)"
    COMPONENT_CHART_TAGS["$component"]="$tag"
    if [[ "$tag" =~ ^([0-9]+\.[0-9]+\.[0-9]+) ]]; then
      COMPONENT_VERSIONS["$component"]="${BASH_REMATCH[1]}"
    fi
  done

  for component in "${LONGHORN_COMPONENTS[@]}"; do
    COMPONENT_CHART_TAGS["$component"]="$(echo "$values" | yq eval "${COMPONENT_PATHS[$component]}" -)"
  done
}

fetch_page() {
  local component="$1" page="$2" version_filter="${3:-}"
  local response http_code
  local -a args=(
    --data-urlencode 'packaging_formats=CONTAINER'
    --data-urlencode "component_slug_name=${component}"
    --data-urlencode "page_number=${page}"
    --data-urlencode "page_size=${PAGE_SIZE}"
  )

  if [[ "$TOTAL_API_CALLS" -ge "$MAX_TOTAL_API_CALLS" ]]; then
    echo "ERROR: Exceeded maximum API calls ${MAX_TOTAL_API_CALLS}" >&2
    exit 1
  fi
  TOTAL_API_CALLS=$((TOTAL_API_CALLS + 1))
  [[ -n "$version_filter" ]] && args+=(--data-urlencode "version=${version_filter}")

  response="$(curl --max-time "$CURL_TIMEOUT" -sG -w "\n%{http_code}" \
    "$API_URL" "${args[@]}")"
  http_code="$(tail -n1 <<< "$response")"

  if [[ ! "$http_code" =~ ^2[0-9]{2}$ ]]; then
    echo "ERROR: API request failed with HTTP ${http_code} for component ${component}, page ${page}" >&2
    exit 1
  fi

  head -n -1 <<< "$response"
}

fetch_all_items() {
  local component="$1" version_filter="${2:-}"
  local first_resp total_pages page

  first_resp="$(fetch_page "$component" 1 "$version_filter")"
  if ! jq empty <<< "$first_resp" 2>/dev/null; then
    echo "ERROR: Invalid JSON response for component ${component}" >&2
    exit 1
  fi

  total_pages="$(jq -r '.total_pages // 1' <<< "$first_resp")"
  if [[ "$total_pages" -gt "$MAX_PAGES_PER_COMPONENT" ]]; then
    echo "ERROR: Component ${component} has ${total_pages} pages, exceeds limit ${MAX_PAGES_PER_COMPONENT}" >&2
    echo "ERROR: Refuse to continue because the latest revision may be missed." >&2
    echo "ERROR: Increase MAX_PAGES_PER_COMPONENT or add more specific API filters." >&2
    exit 1
  fi

  {
    jq '.items[]?' <<< "$first_resp"
    for ((page = 2; page <= total_pages; page++)); do
      sleep "$SLEEP_SECONDS"
      fetch_page "$component" "$page" "$version_filter" | jq '.items[]?'
    done
  } | jq -s '.'
}

get_latest_revision_for_version() {
  fetch_all_items "$1" "$2" | jq -r '
    unique_by((.version // "") + "-" + ((.revision // "0") | tostring))
    | sort_by(
        ((.revision // "0") | tostring)
        | split(".")
        | map(tonumber? // 0)
      )
    | reverse
    | if length == 0 then
        "NOT_FOUND|NOT_FOUND"
      else
        .[0] | "\(.version)-\(.revision)|\(.name)"
      end
  '
}

set_component_result() {
  local component="$1" target_version="$2"
  local result tag artifact_name env_name

  result="$(get_latest_revision_for_version "$component" "$target_version")"
  tag="${result%%|*}"
  artifact_name="${result#*|}"

  if [[ "$tag" == "NOT_FOUND" || -z "$tag" ]]; then
    echo "ERROR: Cannot find AppCo artifact for component=${component}, version=${target_version}" >&2
    exit 1
  fi

  COMPONENT_TAGS["$component"]="$tag"
  COMPONENT_ARTIFACT_NAMES["$component"]="$artifact_name"
  env_name="$(to_env_name "$component")"
  export "${env_name}=${tag}"
}

print_exported_variables() {
  local component env_name
  echo "Exported environment variables:"

  for component in "${DEPENDENCY_COMPONENTS[@]}" "${LONGHORN_COMPONENTS[@]}"; do
    env_name="$(to_env_name "$component")"
    echo "  export ${env_name}='${!env_name:-}'"
  done
  echo "  export CUSTOM_LONGHORN_ENGINE_IMAGE='${CUSTOM_LONGHORN_ENGINE_IMAGE}'"
}

print_tag_comparison() {
  local component chart_tag appco_tag env_name
  local all_current=true

  echo ""
  echo "=== AppCo Revision Tag Comparison ==="
  printf "%-50s %-25s %-25s %-12s\n" \
    "COMPONENT" "CHART TAG" "APPCO LATEST TAG" "STATUS"
  printf '%*s\n' 116 '' | tr ' ' '-'

  for component in "${DEPENDENCY_COMPONENTS[@]}" "${LONGHORN_COMPONENTS[@]}"; do
    chart_tag="${COMPONENT_CHART_TAGS[$component]:-N/A}"
    env_name="$(to_env_name "$component")"
    appco_tag="${!env_name:-N/A}"

    if [[ "$chart_tag" == "$appco_tag" ]]; then
      printf "%-50s %-25s %-25s %-12s\n" \
        "$component" "$chart_tag" "$appco_tag" "UP-TO-DATE"
    else
      printf "%-50s %-25s %-25s %-12s\n" \
        "$component" "$chart_tag" "$appco_tag" "OUTDATED"
      all_current=false
    fi
  done

  echo "======================================"
  echo ""
  [[ "$all_current" == true ]]
}

fetch_appco_revision_tags() {
  local target_version="${1:-${TARGET_LONGHORN_VERSION}}" component

  parse_component_versions "$target_version"

  for component in "${DEPENDENCY_COMPONENTS[@]}"; do
    if [[ -z "${COMPONENT_VERSIONS[$component]:-}" ]]; then
      echo "ERROR: Cannot find image version for dependency component ${component} from Helm chart version ${target_version}" >&2
      exit 1
    fi
    set_component_result "$component" "${COMPONENT_VERSIONS[$component]}"
  done

  for component in "${LONGHORN_COMPONENTS[@]}"; do
    set_component_result "$component" "$target_version"
  done

  export CUSTOM_LONGHORN_ENGINE_IMAGE="dp.apps.rancher.io/containers/longhorn-engine:${LONGHORN_ENGINE_TAG}"
  print_exported_variables

  if print_tag_comparison; then
    echo "INFO: All image tags in the chart already match the latest AppCo revision tags. No new revision images to test."
    export APPCO_REVISION_IMAGES_CURRENT=true
  else
    export APPCO_REVISION_IMAGES_CURRENT=false
  fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  set -euo pipefail
  TARGET_LONGHORN_VERSION="${1:-1.11.2}"
  fetch_appco_revision_tags "$TARGET_LONGHORN_VERSION"
fi