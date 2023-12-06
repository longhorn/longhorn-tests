#!/usr/bin/env bash

set -x

export FLEET_REPO_URI="${1}"
export FLEET_REPO_VERSION="${2}"

source pipelines/utilities/fleet.sh

export LONGHORN_NAMESPACE="longhorn-system"

create_fleet_git_repo
