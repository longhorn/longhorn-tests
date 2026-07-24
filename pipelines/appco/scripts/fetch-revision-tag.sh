#!/usr/bin/env bash

API_URL="https://api.apps.rancher.io/v1/artifacts"
PAGE_SIZE=100
SLEEP_SECONDS=0.2
CURL_TIMEOUT=10

MAX_PAGES_PER_COMPONENT=50
MAX_TOTAL_API_CALLS=500

TARGET_LONGHORN_VERSION="${TARGET_LONGHORN_VERSION:-1.11.2}"
TOTAL_API_CALLS=0

# These always use TARGET_LONGHORN_VERSION when querying AppCo API.
LONGHORN_COMPONENTS=(
  longhorn-backing-image-manager
  longhorn-engine
  longhorn-instance-manager
  longhorn-manager
  longhorn-share-manager
  longhorn-ui
)

# Their target versions are parsed from Helm chart values.
DEPENDENCY_COMPONENTS=(
  kubernetes-csi-external-attacher
  kubernetes-csi-external-provisioner
  kubernetes-csi-external-resizer
  kubernetes-csi-external-snapshotter
  kubernetes-csi-livenessprobe
  kubernetes-csi-node-driver-registrar
  rancher-support-bundle-kit
)

declare -A COMPONENT_VERSIONS
declare -A COMPONENT_TAGS
declare -A COMPONENT_ARTIFACT_NAMES

################################################################################
# Utility Functions
################################################################################

to_env_name() {
  local component="$1"
  echo "${component}_tag" | tr '[:lower:]-' '[:upper:]_'
}

get_chart_values() {
  local version="$1"
  local chart_version
  local values_output

  # Extract base version (e.g., 1.11.2 from 1.11.2-1)
  chart_version="$(echo "$version" | cut -d'-' -f1)"

  echo "INFO: Fetching Helm chart values for suse-storage version ${chart_version}" >&2

  values_output="$(helm show values "oci://dp.apps.rancher.io/charts/suse-storage" --version "$chart_version" 2>&1)"

  if [[ $? -ne 0 ]]; then
    echo "ERROR: Failed to fetch Helm chart values for suse-storage version ${chart_version}" >&2
    echo "$values_output" >&2
    exit 1
  fi

  # Remove the "Pulled:" and "Digest:" lines from helm output
  echo "$values_output" | grep -v '^Pulled:' | grep -v '^Digest:'
}

parse_component_versions() {
  local version="$1"
  local values
  local tag

  values="$(get_chart_values "$version")"

  # Extract version from each component tag using yq
  # CSI components
  tag="$(echo "$values" | yq eval '.image.csi.attacher.tag' -)"
  if [[ "$tag" =~ ^([0-9]+\.[0-9]+\.[0-9]+) ]]; then
    COMPONENT_VERSIONS["kubernetes-csi-external-attacher"]="${BASH_REMATCH[1]}"
  fi

  tag="$(echo "$values" | yq eval '.image.csi.provisioner.tag' -)"
  if [[ "$tag" =~ ^([0-9]+\.[0-9]+\.[0-9]+) ]]; then
    COMPONENT_VERSIONS["kubernetes-csi-external-provisioner"]="${BASH_REMATCH[1]}"
  fi

  tag="$(echo "$values" | yq eval '.image.csi.resizer.tag' -)"
  if [[ "$tag" =~ ^([0-9]+\.[0-9]+\.[0-9]+) ]]; then
    COMPONENT_VERSIONS["kubernetes-csi-external-resizer"]="${BASH_REMATCH[1]}"
  fi

  tag="$(echo "$values" | yq eval '.image.csi.snapshotter.tag' -)"
  if [[ "$tag" =~ ^([0-9]+\.[0-9]+\.[0-9]+) ]]; then
    COMPONENT_VERSIONS["kubernetes-csi-external-snapshotter"]="${BASH_REMATCH[1]}"
  fi

  tag="$(echo "$values" | yq eval '.image.csi.livenessProbe.tag' -)"
  if [[ "$tag" =~ ^([0-9]+\.[0-9]+\.[0-9]+) ]]; then
    COMPONENT_VERSIONS["kubernetes-csi-livenessprobe"]="${BASH_REMATCH[1]}"
  fi

  tag="$(echo "$values" | yq eval '.image.csi.nodeDriverRegistrar.tag' -)"
  if [[ "$tag" =~ ^([0-9]+\.[0-9]+\.[0-9]+) ]]; then
    COMPONENT_VERSIONS["kubernetes-csi-node-driver-registrar"]="${BASH_REMATCH[1]}"
  fi

  tag="$(echo "$values" | yq eval '.image.longhorn.supportBundleKit.tag' -)"
  if [[ "$tag" =~ ^([0-9]+\.[0-9]+\.[0-9]+) ]]; then
    COMPONENT_VERSIONS["rancher-support-bundle-kit"]="${BASH_REMATCH[1]}"
  fi
}

fetch_page() {
  local component="$1"
  local page="$2"
  local version_filter="${3:-}"

  local response
  local http_code

  if [[ "$TOTAL_API_CALLS" -ge "$MAX_TOTAL_API_CALLS" ]]; then
    echo "ERROR: Exceeded maximum API calls ${MAX_TOTAL_API_CALLS}" >&2
    exit 1
  fi

  TOTAL_API_CALLS=$((TOTAL_API_CALLS + 1))

  if [[ -n "$version_filter" ]]; then
    response="$(curl --max-time "${CURL_TIMEOUT}" -sG -w "\n%{http_code}" "${API_URL}" \
      --data-urlencode 'packaging_formats=CONTAINER' \
      --data-urlencode "component_slug_name=${component}" \
      --data-urlencode "version=${version_filter}" \
      --data-urlencode "page_number=${page}" \
      --data-urlencode "page_size=${PAGE_SIZE}")"
  else
    response="$(curl --max-time "${CURL_TIMEOUT}" -sG -w "\n%{http_code}" "${API_URL}" \
      --data-urlencode 'packaging_formats=CONTAINER' \
      --data-urlencode "component_slug_name=${component}" \
      --data-urlencode "page_number=${page}" \
      --data-urlencode "page_size=${PAGE_SIZE}")"
  fi

  http_code="$(echo "$response" | tail -n1)"

  if [[ ! "$http_code" =~ ^2[0-9]{2}$ ]]; then
    echo "ERROR: API request failed with HTTP ${http_code} for component ${component}, page ${page}" >&2
    exit 1
  fi

  echo "$response" | head -n -1
}

fetch_all_items() {
  local component="$1"
  local version_filter="${2:-}"

  local first_resp
  local total_pages

  first_resp="$(fetch_page "$component" 1 "$version_filter")"

  if ! echo "$first_resp" | jq empty 2>/dev/null; then
    echo "ERROR: Invalid JSON response for component ${component}" >&2
    exit 1
  fi

  total_pages="$(echo "$first_resp" | jq -r '.total_pages // 1')"

  if [[ "$total_pages" -gt "$MAX_PAGES_PER_COMPONENT" ]]; then
    echo "ERROR: Component ${component} has ${total_pages} pages, exceeds limit ${MAX_PAGES_PER_COMPONENT}" >&2
    echo "ERROR: Refuse to continue because the latest revision may be missed." >&2
    echo "ERROR: Increase MAX_PAGES_PER_COMPONENT or add more specific API filters." >&2
    exit 1
  fi

  {
    echo "$first_resp" | jq '.items[]?'

    if [[ "$total_pages" -gt 1 ]]; then
      for page in $(seq 2 "$total_pages"); do
        sleep "$SLEEP_SECONDS"
        fetch_page "$component" "$page" "$version_filter" | jq '.items[]?'
      done
    fi
  } | jq -s '.'
}

get_latest_revision_for_version() {
  local component="$1"
  local target_version="$2"

  fetch_all_items "$component" "$target_version" | jq -r '
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
  local component="$1"
  local target_version="$2"

  local result
  local tag
  local artifact_name
  local env_name

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
  local component
  local env_name

  echo "Exported environment variables:"

  for component in "${DEPENDENCY_COMPONENTS[@]}"; do
    env_name="$(to_env_name "$component")"
    echo "  export ${env_name}='${!env_name:-}'"
  done

  for component in "${LONGHORN_COMPONENTS[@]}"; do
    env_name="$(to_env_name "$component")"
    echo "  export ${env_name}='${!env_name:-}'"
  done

  echo "  export CUSTOM_LONGHORN_ENGINE_IMAGE='dp.apps.rancher.io/containers/longhorn-engine:${LONGHORN_ENGINE_TAG}'"

}

# Main function to fetch revision tags for all components and export them as environment variables.
fetch_appco_revision_tags() {
  local target_version="${1:-${TARGET_LONGHORN_VERSION}}"
  local component
  local env_file="${TMPDIR:-/tmp}/appco_revision_tags.env"

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
}

# Direct Execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  set -euo pipefail

  TARGET_LONGHORN_VERSION="${1:-1.11.2}"
  fetch_appco_revision_tags "$TARGET_LONGHORN_VERSION"
fi
