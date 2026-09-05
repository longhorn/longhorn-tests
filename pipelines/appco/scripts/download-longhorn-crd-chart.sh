#!/bin/bash

set -euo pipefail

# Script Identity - pinned to the commit SHA when this version was established
SCRIPT_COMMIT_SHA="484871a"
echo "Running download script version: ${SCRIPT_COMMIT_SHA}"

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    echo "Usage: $0 <version> [github_token]"
    exit 1
fi

REPO="rancher/charts"
VERSION="$1"
TARGET_PATH="charts/longhorn-crd/${VERSION}"
LOCAL_DIR="${VERSION}"

# GitHub Token is optional — prefer explicit $2, fall back to GITHUB_TOKEN env var
{ set +x; } 2>/dev/null  # suppress xtrace while handling credentials
if [ $# -eq 2 ]; then
    GITHUB_TOKEN="$2"
fi
if [ -n "${GITHUB_TOKEN:-}" ]; then
    AUTH_HEADER="Authorization: token ${GITHUB_TOKEN}"
else
    AUTH_HEADER=""
fi
{ set -x; } 2>/dev/null || true  # restore xtrace if it was active

# Get all release-* branches and sort by latest first
branches=""
page=1

while true; do
    if [ -n "$AUTH_HEADER" ]; then
        page_data=$(curl -s -H "${AUTH_HEADER}" \
            "https://api.github.com/repos/${REPO}/branches?per_page=100&page=${page}")
    else
        page_data=$(curl -s \
            "https://api.github.com/repos/${REPO}/branches?per_page=100&page=${page}")
    fi

    # Stop when there are no more branches
    if [ "$(echo "$page_data" | jq 'length')" -eq 0 ]; then
        break
    fi

    branches+=$'\n'"$(echo "$page_data" | jq -r '.[].name')"

    page=$((page + 1))
done

branches=$(echo "$branches" | grep '^release-' | sort -r)

# Function to recursively download files and folders using a Locked Commit SHA
download_directory() {
    local remote_path=$1
    local local_path=$2
    local commit_sha=$3
    echo "Fetching content from: ${remote_path} (Locked Commit: ${commit_sha})"
    if [ -n "$AUTH_HEADER" ]; then
        response=$(curl -s -w "%{http_code}" -H "${AUTH_HEADER}" -o /tmp/api_response.json "https://api.github.com/repos/${REPO}/contents/${remote_path}?ref=${commit_sha}")
    else
        response=$(curl -s -w "%{http_code}" -o /tmp/api_response.json "https://api.github.com/repos/${REPO}/contents/${remote_path}?ref=${commit_sha}")
    fi
    http_code="${response: -3}"
    body=$(cat /tmp/api_response.json)
    if [[ "$http_code" != "200" ]]; then
        echo "Error fetching directory: ${remote_path}"
        echo "HTTP status: $http_code"
        echo "Response: $body"
        exit 1
    fi
    if ! echo "$body" | jq -e '. | type == "array"' > /dev/null; then
        echo "Unexpected API response format for ${remote_path}"
        echo "Response: $body"
        exit 1
    fi
    for row in $(echo "${body}" | jq -r '.[] | @base64'); do
        _jq() {
            echo "${row}" | base64 --decode | jq -r "${1}"
        }
        name=$(_jq '.name')
        type=$(_jq '.type')
        path=$(_jq '.path')
        if [[ "${type}" == "file" ]]; then
            # Using the immutable commit_sha in the URL instead of the branch name
            file_url="https://raw.githubusercontent.com/${REPO}/${commit_sha}/${path}"
            echo "Downloading file: ${path}"
            mkdir -p "${local_path}"
            curl -s -L -o "${local_path}/${name}" "${file_url}"
        elif [[ "${type}" == "dir" ]]; then
            echo "Entering directory: ${path}"
            mkdir -p "${local_path}/${name}"
            # Pass the commit_sha down into the recursion
            download_directory "${path}" "${local_path}/${name}" "${commit_sha}"
        fi
    done
}

for branch in $branches; do
    echo "Checking branch: $branch"

    # Resolve the branch name to a specific Commit SHA
    if [ -n "$AUTH_HEADER" ]; then
        branch_data=$(curl -s -H "${AUTH_HEADER}" "https://api.github.com/repos/${REPO}/branches/${branch}")
    else
        branch_data=$(curl -s "https://api.github.com/repos/${REPO}/branches/${branch}")
    fi

    COMMIT_SHA=$(echo "$branch_data" | jq -r '.commit.sha')

    # Check if the target path exists at this specific SHA
    url="https://api.github.com/repos/${REPO}/contents/${TARGET_PATH}?ref=${COMMIT_SHA}"
    if [ -n "$AUTH_HEADER" ]; then
        response=$(curl -s -w "%{http_code}" -H "${AUTH_HEADER}" -o /tmp/check_response.json "$url")
    else
        response=$(curl -s -w "%{http_code}" -o /tmp/check_response.json "$url")
    fi

    http_code="${response: -3}"
    body=$(cat /tmp/check_response.json)

    if [[ "$http_code" == "200" ]]; then
        echo "Found target in branch: $branch (Locked to SHA: $COMMIT_SHA)"
        mkdir -p "${LOCAL_DIR}"
        # Start the download using the immutable COMMIT_SHA
        download_directory "${TARGET_PATH}" "${LOCAL_DIR}" "${COMMIT_SHA}"
        echo "Download completed to ${LOCAL_DIR} using immutable commit ${COMMIT_SHA}."
        exit 0
    elif [[ "$http_code" != "404" ]]; then
        echo "Error checking branch: ${branch}"
        echo "HTTP status: $http_code"
        echo "Response: $body"
        exit 1
    fi
done

echo "Target not found in any release-* branch."
exit 1
