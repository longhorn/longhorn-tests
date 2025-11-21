#!/bin/bash

# Longhorn Component Version Validation Test Script
# Test Objective: Verify Longhorn deployment component versions against dep-versions versions.json
#
# Usage: 
#   ./lh_ver_check.sh [version]
#   ./lh_ver_check.sh v1.10.x    # Check against v1.10.x
#   ./lh_ver_check.sh v1.9.x     # Check against v1.9.x
#   ./lh_ver_check.sh            # Default to v1.10.x

# Default version
DEFAULT_VERSION="v1.10.x"

# Get version from command line argument or use default
VERSION="${1:-$DEFAULT_VERSION}"

echo "=========================================="
echo "Longhorn Component Version Validation Test"
echo "Test Time: $(date)"
echo "Target Version: $VERSION"
echo "=========================================="

# Create result log file
RESULT_FILE="/tmp/longhorn_version_check_${VERSION}_$(date +%Y%m%d_%H%M%S).txt"
echo "Test results will be logged to: $RESULT_FILE"
echo "" > $RESULT_FILE

# Function: Log test results
log_result() {
    local component=$1
    local expected=$2
    local actual=$3
    local status=$4
    local location=$5
    
    echo "Component: $component" | tee -a $RESULT_FILE
    echo "Expected Version: $expected" | tee -a $RESULT_FILE
    echo "Actual Version: $actual" | tee -a $RESULT_FILE
    echo "Test Result: $status" | tee -a $RESULT_FILE
    echo "Query Location: $location" | tee -a $RESULT_FILE
    echo "----------------------------------------" | tee -a $RESULT_FILE
}

# Download version specification JSON from GitHub
echo "Downloading version specification..."
VERSIONS_URL="https://raw.githubusercontent.com/longhorn/dep-versions/${VERSION}/versions.json"
echo "Source: $VERSIONS_URL"
VERSIONS_JSON=$(curl -fsSL "$VERSIONS_URL" 2>/dev/null)

if [ -z "$VERSIONS_JSON" ]; then
    echo "❌ Failed to download version specification file, using default values"
    # Default values (fallback)
    EXPECTED_CSI_ATTACHER="v4.10.0-20251030"
    EXPECTED_CSI_PROVISIONER="v5.3.0-20251030"
    EXPECTED_CSI_RESIZER="v1.14.0-20251030"
    EXPECTED_CSI_SNAPSHOTTER="v8.4.0-20251030"
    EXPECTED_CSI_NODE_REGISTRAR="v2.15.0-20251030"
    EXPECTED_LIVENESSPROBE="v2.17.0-20251030"
    EXPECTED_NVME_CLI="v2.10.2"
    EXPECTED_NVME_CLI="v2.10.2"
    EXPECTED_TGT="v1.0.79+2"
    EXPECTED_SPDK="v25.05.0+4"
    EXPECTED_LIBJSONC="json-c-0.17-20230812"
    EXPECTED_LIBNVME="v1.10"
    EXPECTED_NFS_GANESHA="v7.3.0+1"
    EXPECTED_NTIRPC="v7.2"
    EXPECTED_LIBQCOW="v1.0.0"
else
    echo "✅ Successfully downloaded version specification"
    # Parse JSON using jq (jq must be installed)
    if command -v jq &> /dev/null; then
        EXPECTED_CSI_ATTACHER=$(echo "$VERSIONS_JSON" | jq -r '."csi-attacher".tag // "v4.10.0-20251030"')
        EXPECTED_CSI_PROVISIONER=$(echo "$VERSIONS_JSON" | jq -r '."csi-provisioner".tag // "v5.3.0-20251030"')
        EXPECTED_CSI_RESIZER=$(echo "$VERSIONS_JSON" | jq -r '."csi-resizer".tag // "v1.14.0-20251030"')
        EXPECTED_CSI_SNAPSHOTTER=$(echo "$VERSIONS_JSON" | jq -r '."csi-snapshotter".tag // "v8.4.0-20251030"')
        EXPECTED_CSI_NODE_REGISTRAR=$(echo "$VERSIONS_JSON" | jq -r '."csi-node-driver-registrar".tag // "v2.15.0-20251030"')
        EXPECTED_LIVENESSPROBE=$(echo "$VERSIONS_JSON" | jq -r '.livenessprobe.tag // "v2.17.0-20251030"')
        EXPECTED_NVME_CLI=$(echo "$VERSIONS_JSON" | jq -r '."nvme-cli".tag // "v2.10.2"')
        EXPECTED_TGT=$(echo "$VERSIONS_JSON" | jq -r '.tgt.tag // "v1.0.79+2"')
        EXPECTED_SPDK=$(echo "$VERSIONS_JSON" | jq -r '.spdk.tag // "v25.05.0+4"')
        EXPECTED_LIBJSONC=$(echo "$VERSIONS_JSON" | jq -r '.libjsonc.tag // "json-c-0.17-20230812"')
        EXPECTED_LIBNVME=$(echo "$VERSIONS_JSON" | jq -r '.libnvme.tag // "v1.10"')
        EXPECTED_NFS_GANESHA=$(echo "$VERSIONS_JSON" | jq -r '."nfs-ganesha".tag // "v7.3.0+1"')
        EXPECTED_NTIRPC=$(echo "$VERSIONS_JSON" | jq -r '.ntirpc.tag // "v7.2"')
        EXPECTED_LIBQCOW=$(echo "$VERSIONS_JSON" | jq -r '.libqcow.tag // "v1.0.0"')
    else
        echo "⚠️  jq not installed, using default version values"
        EXPECTED_CSI_ATTACHER="v4.10.0-20251030"
        EXPECTED_CSI_PROVISIONER="v5.3.0-20251030"
        EXPECTED_CSI_RESIZER="v1.14.0-20251030"
        EXPECTED_CSI_SNAPSHOTTER="v8.4.0-20251030"
        EXPECTED_CSI_NODE_REGISTRAR="v2.15.0-20251030"
        EXPECTED_LIVENESSPROBE="v2.17.0-20251030"
        EXPECTED_NVME_CLI="v2.10.2"
        EXPECTED_TGT="v1.0.79+2"
        EXPECTED_SPDK="v25.05.0+4"
        EXPECTED_LIBJSONC="json-c-0.17-20230812"
        EXPECTED_LIBNVME="v1.10"
        EXPECTED_NFS_GANESHA="v7.3.0+1"
        EXPECTED_NTIRPC="v7.2"
        EXPECTED_LIBQCOW="v1.0.0"
    fi
fi

echo ""
echo "Phase 1: Check CSI Component Image Versions"
echo "=========================================="

# Check CSI Attacher
echo "Checking csi-attacher..."
ATTACHER_IMAGE=$(kubectl -n longhorn-system get deploy csi-attacher -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null)
ATTACHER_TAG="${ATTACHER_IMAGE##*:}"
ATTACHER_BASE="${ATTACHER_TAG#v}"; ATTACHER_BASE="${ATTACHER_BASE%%-*}"

# Extract version and date from expected version
EXPECTED_ATTACHER_BASE="${EXPECTED_CSI_ATTACHER#v}"; EXPECTED_ATTACHER_BASE="${EXPECTED_ATTACHER_BASE%%-*}"
EXPECTED_ATTACHER_DATE="Not specified"
if [[ "$EXPECTED_CSI_ATTACHER" == *-* ]]; then 
    EXPECTED_ATTACHER_DATE="${EXPECTED_CSI_ATTACHER#*-}"
fi

if [[ "$ATTACHER_BASE" == "$EXPECTED_ATTACHER_BASE" ]]; then
    log_result "csi-attacher" "v$EXPECTED_ATTACHER_BASE | Date: $EXPECTED_ATTACHER_DATE" "Version: $ATTACHER_BASE | Full: $ATTACHER_IMAGE" "✅ PASS" "csi-attacher deployment"
else
    log_result "csi-attacher" "v$EXPECTED_ATTACHER_BASE | Date: $EXPECTED_ATTACHER_DATE" "Version: $ATTACHER_BASE | Full: $ATTACHER_IMAGE" "❌ FAIL" "csi-attacher deployment"
fi

# Check CSI Provisioner
echo "Checking csi-provisioner..."
PROVISIONER_IMAGE=$(kubectl -n longhorn-system get deploy csi-provisioner -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null)
PROVISIONER_TAG="${PROVISIONER_IMAGE##*:}"
PROVISIONER_BASE="${PROVISIONER_TAG#v}"; PROVISIONER_BASE="${PROVISIONER_BASE%%-*}"

# Extract version and date from expected version
EXPECTED_PROVISIONER_BASE="${EXPECTED_CSI_PROVISIONER#v}"; EXPECTED_PROVISIONER_BASE="${EXPECTED_PROVISIONER_BASE%%-*}"
EXPECTED_PROVISIONER_DATE="Not specified"
if [[ "$EXPECTED_CSI_PROVISIONER" == *-* ]]; then 
    EXPECTED_PROVISIONER_DATE="${EXPECTED_CSI_PROVISIONER#*-}"
fi

if [[ "$PROVISIONER_BASE" == "$EXPECTED_PROVISIONER_BASE" ]]; then
    log_result "csi-provisioner" "v$EXPECTED_PROVISIONER_BASE | Date: $EXPECTED_PROVISIONER_DATE" "Version: $PROVISIONER_BASE | Full: $PROVISIONER_IMAGE" "✅ PASS" "csi-provisioner deployment"
else
    log_result "csi-provisioner" "v$EXPECTED_PROVISIONER_BASE | Date: $EXPECTED_PROVISIONER_DATE" "Version: $PROVISIONER_BASE | Full: $PROVISIONER_IMAGE" "❌ FAIL" "csi-provisioner deployment"
fi

# Check CSI Resizer
echo "Checking csi-resizer..."
RESIZER_IMAGE=$(kubectl -n longhorn-system get deploy csi-resizer -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null)
RESIZER_TAG="${RESIZER_IMAGE##*:}"
RESIZER_BASE="${RESIZER_TAG#v}"; RESIZER_BASE="${RESIZER_BASE%%-*}"

# Extract version and date from expected version
EXPECTED_RESIZER_BASE="${EXPECTED_CSI_RESIZER#v}"; EXPECTED_RESIZER_BASE="${EXPECTED_RESIZER_BASE%%-*}"
EXPECTED_RESIZER_DATE="Not specified"
if [[ "$EXPECTED_CSI_RESIZER" == *-* ]]; then 
    EXPECTED_RESIZER_DATE="${EXPECTED_CSI_RESIZER#*-}"
fi

if [[ "$RESIZER_BASE" == "$EXPECTED_RESIZER_BASE" ]]; then
    log_result "csi-resizer" "v$EXPECTED_RESIZER_BASE | Date: $EXPECTED_RESIZER_DATE" "Version: $RESIZER_BASE | Full: $RESIZER_IMAGE" "✅ PASS" "csi-resizer deployment"
else
    log_result "csi-resizer" "v$EXPECTED_RESIZER_BASE | Date: $EXPECTED_RESIZER_DATE" "Version: $RESIZER_BASE | Full: $RESIZER_IMAGE" "❌ FAIL" "csi-resizer deployment"
fi

# Check CSI Snapshotter
echo "Checking csi-snapshotter..."
SNAPSHOTTER_IMAGE=$(kubectl -n longhorn-system get deploy csi-snapshotter -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null)
SNAPSHOTTER_TAG="${SNAPSHOTTER_IMAGE##*:}"
SNAPSHOTTER_BASE="${SNAPSHOTTER_TAG#v}"; SNAPSHOTTER_BASE="${SNAPSHOTTER_BASE%%-*}"

# Extract version and date from expected version
EXPECTED_SNAPSHOTTER_BASE="${EXPECTED_CSI_SNAPSHOTTER#v}"; EXPECTED_SNAPSHOTTER_BASE="${EXPECTED_SNAPSHOTTER_BASE%%-*}"
EXPECTED_SNAPSHOTTER_DATE="Not specified"
if [[ "$EXPECTED_CSI_SNAPSHOTTER" == *-* ]]; then 
    EXPECTED_SNAPSHOTTER_DATE="${EXPECTED_CSI_SNAPSHOTTER#*-}"
fi

if [[ "$SNAPSHOTTER_BASE" == "$EXPECTED_SNAPSHOTTER_BASE" ]]; then
    log_result "csi-snapshotter" "v$EXPECTED_SNAPSHOTTER_BASE | Date: $EXPECTED_SNAPSHOTTER_DATE" "Version: $SNAPSHOTTER_BASE | Full: $SNAPSHOTTER_IMAGE" "✅ PASS" "csi-snapshotter deployment"
else
    log_result "csi-snapshotter" "v$EXPECTED_SNAPSHOTTER_BASE | Date: $EXPECTED_SNAPSHOTTER_DATE" "Version: $SNAPSHOTTER_BASE | Full: $SNAPSHOTTER_IMAGE" "❌ FAIL" "csi-snapshotter deployment"
fi

# Check CSI Node Driver Registrar (in DaemonSet)
echo "Checking csi-node-driver-registrar..."
NODE_REGISTRAR_IMAGE=$(kubectl -n longhorn-system get ds longhorn-csi-plugin -o jsonpath='{.spec.template.spec.containers[?(@.name=="node-driver-registrar")].image}' 2>/dev/null)
NODE_REGISTRAR_TAG="${NODE_REGISTRAR_IMAGE##*:}"
NODE_REGISTRAR_BASE="${NODE_REGISTRAR_TAG#v}"; NODE_REGISTRAR_BASE="${NODE_REGISTRAR_BASE%%-*}"

# Extract version and date from expected version
EXPECTED_NODE_REGISTRAR_BASE="${EXPECTED_CSI_NODE_REGISTRAR#v}"; EXPECTED_NODE_REGISTRAR_BASE="${EXPECTED_NODE_REGISTRAR_BASE%%-*}"
EXPECTED_NODE_REGISTRAR_DATE="Not specified"
if [[ "$EXPECTED_CSI_NODE_REGISTRAR" == *-* ]]; then 
    EXPECTED_NODE_REGISTRAR_DATE="${EXPECTED_CSI_NODE_REGISTRAR#*-}"
fi

if [[ "$NODE_REGISTRAR_BASE" == "$EXPECTED_NODE_REGISTRAR_BASE" ]]; then
    log_result "csi-node-driver-registrar" "v$EXPECTED_NODE_REGISTRAR_BASE | Date: $EXPECTED_NODE_REGISTRAR_DATE" "Version: $NODE_REGISTRAR_BASE | Full: $NODE_REGISTRAR_IMAGE" "✅ PASS" "csi-plugin daemonset"
else
    log_result "csi-node-driver-registrar" "v$EXPECTED_NODE_REGISTRAR_BASE | Date: $EXPECTED_NODE_REGISTRAR_DATE" "Version: $NODE_REGISTRAR_BASE | Full: $NODE_REGISTRAR_IMAGE" "❌ FAIL" "csi-plugin daemonset"
fi

# Check Liveness Probe
echo "Checking livenessprobe..."
LIVENESS_IMAGE=$(kubectl -n longhorn-system get daemonset longhorn-csi-plugin -o jsonpath='{.spec.template.spec.containers[*].image}' | tr ' ' '\n' | grep livenessprobe 2>/dev/null)
LIVENESS_TAG="${LIVENESS_IMAGE##*:}"
LIVENESS_BASE="${LIVENESS_TAG#v}"; LIVENESS_BASE="${LIVENESS_BASE%%-*}"

# Extract version and date from expected version
EXPECTED_LIVENESS_BASE="${EXPECTED_LIVENESSPROBE#v}"; EXPECTED_LIVENESS_BASE="${EXPECTED_LIVENESS_BASE%%-*}"
EXPECTED_LIVENESS_DATE="Not specified"
if [[ "$EXPECTED_LIVENESSPROBE" == *-* ]]; then 
    EXPECTED_LIVENESS_DATE="${EXPECTED_LIVENESSPROBE#*-}"
fi

if [[ "$LIVENESS_BASE" == "$EXPECTED_LIVENESS_BASE" ]]; then
    log_result "livenessprobe" "v$EXPECTED_LIVENESS_BASE | Date: $EXPECTED_LIVENESS_DATE" "Version: $LIVENESS_BASE | Full: $LIVENESS_IMAGE" "✅ PASS" "longhorn-csi-plugin daemonset"
else
    log_result "livenessprobe" "v$EXPECTED_LIVENESS_BASE | Date: $EXPECTED_LIVENESS_DATE" "Version: $LIVENESS_BASE | Full: $LIVENESS_IMAGE" "❌ FAIL" "longhorn-csi-plugin daemonset"
fi

echo ""
echo "Phase 2: V2 Instance Manager Components Version Check"
echo "=========================================="

# Get a running v2 instance manager pod
V2_IM_POD=$(kubectl -n longhorn-system get pods -l longhorn.io/component=instance-manager -l longhorn.io/data-engine=v2 --no-headers | head -n 1 | awk '{print $1}' 2>/dev/null)
if [ -z "$V2_IM_POD" ]; then
    echo "❌ No running v2 instance-manager pod found"
    log_result "v2-instance-manager-check" "Running pod" "Not found" "❌ FAIL" "v2 instance-manager pods"
else
    echo "Using v2 instance manager pod: $V2_IM_POD"
    
    # Check nvme-cli
    echo "Checking nvme-cli version..."
    NVME_VERSION=$(kubectl -n longhorn-system exec $V2_IM_POD -- nvme version 2>/dev/null | head -1 || echo "Not found")
    EXPECTED_NVME_BASE="${EXPECTED_NVME_CLI#v}"
    if [[ $NVME_VERSION == *"$EXPECTED_NVME_BASE"* ]]; then
        log_result "nvme-cli" "$EXPECTED_NVME_CLI" "$NVME_VERSION" "✅ PASS" "$V2_IM_POD container"
    else
        log_result "nvme-cli" "$EXPECTED_NVME_CLI" "$NVME_VERSION" "❌ FAIL" "$V2_IM_POD container"
    fi

    # Check tgt (tgtd)
    echo "Checking tgt (tgtd) version..."
    TGT_VERSION=$(kubectl -n longhorn-system exec $V2_IM_POD -- tgtd --version 2>/dev/null || echo "Not found")
    EXPECTED_TGT_BASE="${EXPECTED_TGT#v}"; EXPECTED_TGT_BASE="${EXPECTED_TGT_BASE%%+*}"
    if [[ $TGT_VERSION == *"$EXPECTED_TGT_BASE"* ]]; then
        log_result "tgt" "$EXPECTED_TGT" "$TGT_VERSION" "✅ PASS" "$V2_IM_POD container"
    else
        log_result "tgt" "$EXPECTED_TGT" "$TGT_VERSION" "❌ FAIL" "$V2_IM_POD container"
    fi

    # Check spdk (spdk)
    echo "Checking spdk (spdk) version..."
    SPDK_VERSION=$(kubectl -n longhorn-system exec $V2_IM_POD -- spdk_tgt --version 2>/dev/null || echo "Not found")

    # Extract major version from expected version (v25.05.0+4 -> 25.05)
    EXPECTED_SPDK_BASE="${EXPECTED_SPDK#v}"                    # Remove v: 25.05.0+4
    EXPECTED_SPDK_BASE="${EXPECTED_SPDK_BASE%%+*}"             # Remove + suffix: 25.05.0
    EXPECTED_SPDK_MAJOR=$(echo "$EXPECTED_SPDK_BASE" | cut -d. -f1,2)  # Take first two segments: 25.05
    
    # Extract major version from actual version (SPDK v25.05 -> 25.05)
    ACTUAL_SPDK_MAJOR=$(echo "$SPDK_VERSION" | grep -oP 'v?\K\d+\.\d+' || echo "")
    
    if [[ "$ACTUAL_SPDK_MAJOR" == "$EXPECTED_SPDK_MAJOR" ]]; then
        log_result "spdk" "$EXPECTED_SPDK" "$SPDK_VERSION (Detected version: $ACTUAL_SPDK_MAJOR)" "✅ PASS" "$V2_IM_POD container"
    else
        log_result "spdk" "$EXPECTED_SPDK" "$SPDK_VERSION (Detected version: $ACTUAL_SPDK_MAJOR, Expected: $EXPECTED_SPDK_MAJOR)" "❌ FAIL" "$V2_IM_POD container"
    fi

#    # Check libjsonc
#    JSONC_VERSION=$(kubectl -n longhorn-system exec $V2_IM_POD -- pkg-config --modversion json-c 2>/dev/null || echo "未找到")
#    EXPECTED_JSONC_BASE=$(echo "$EXPECTED_LIBJSONC" | grep -oP '\d+\.\d+')
#    if [[ $JSONC_VERSION == *"$EXPECTED_JSONC_BASE"* ]]; then
#        log_result "libjsonc" "$EXPECTED_LIBJSONC" "$JSONC_VERSION" "✅ PASS" "$V2_IM_POD container"
#    else
#        log_result "libjsonc" "$EXPECTED_LIBJSONC" "$JSONC_VERSION" "❌ FAIL" "$V2_IM_POD container"
#    fi

    # Check libnvme
    LIBNVME_VERSION=$(kubectl -n longhorn-system exec $V2_IM_POD -- nvme version 2>/dev/null | grep libnvme || echo "Not found")
    EXPECTED_LIBNVME_BASE="${EXPECTED_LIBNVME#v}"
    if [[ $LIBNVME_VERSION == *"$EXPECTED_LIBNVME_BASE"* ]]; then
        log_result "libnvme" "$EXPECTED_LIBNVME" "$LIBNVME_VERSION" "✅ PASS" "$V2_IM_POD container"
    else
        log_result "libnvme" "$EXPECTED_LIBNVME" "$LIBNVME_VERSION" "❌ FAIL" "$V2_IM_POD container"
    fi

    # Check libqcow
    LIBQCOW_INFO=$(kubectl -n longhorn-system exec $V2_IM_POD -- find /usr -name "*libqcow*" -o -name "*qcow*" 2>/dev/null | grep -v proc || echo "")
    if [ ! -z "$LIBQCOW_INFO" ]; then
        LIBQCOW_DETAILS=$(kubectl -n longhorn-system exec $V2_IM_POD -- ls -la $LIBQCOW_INFO 2>/dev/null | head -5 || echo "Details unavailable")
        log_result "libqcow" "$EXPECTED_LIBQCOW" "$LIBQCOW_DETAILS" "✅ PASS" "$V2_IM_POD container"
    else
        log_result "libqcow" "$EXPECTED_LIBQCOW" "$LIBQCOW_DETAILS" "❌ FAIL" "$V2_IM_POD container"
    fi

fi


echo ""
echo "Phase 3: Check NFS Related Components (if enabled)"
echo "=========================================="

# Check if shared manager pod exists
SM_POD=$(kubectl -n longhorn-system get pods -l longhorn.io/component=share-manager --no-headers | head -n 1 | awk '{print $1}')

if [[ -z "$SM_POD" ]]; then
    echo "ℹ️  No shared-manager pod found (NFS feature may not be enabled)"
    log_result "nfs-ganesha" "$EXPECTED_NFS_GANESHA" "Not deployed" "⚠️  SKIP" "shared-manager pods"
    log_result "ntirpc" "$EXPECTED_NTIRPC" "Not deployed" "⚠️  SKIP" "shared-manager pods"
else
    echo "Using shared manager pod: $SM_POD"
    
    # Check NFS Ganesha
    echo "Checking nfs-ganesha version..."
    GANESHA_VERSION=$(kubectl exec -n longhorn-system "$SM_POD" -- ganesha.nfsd -v 2>/dev/null || echo "Not found")
    
    # Extract major version from expected version (v7.3.0+1 -> 7.3)
    EXPECTED_GANESHA_BASE="${EXPECTED_NFS_GANESHA#v}"           # Remove v: 7.3.0+1
    EXPECTED_GANESHA_BASE="${EXPECTED_GANESHA_BASE%%+*}"        # Remove + suffix: 7.3.0
    EXPECTED_GANESHA_MAJOR=$(echo "$EXPECTED_GANESHA_BASE" | cut -d. -f1,2)  # Take first two segments: 7.3
    
    # Extract major version from actual version (NFS-Ganesha Release = V7.3 -> 7.3)
    ACTUAL_GANESHA_MAJOR=$(echo "$GANESHA_VERSION" | grep -oP 'V?\K\d+\.\d+' || echo "")
    
    if [[ "$ACTUAL_GANESHA_MAJOR" == "$EXPECTED_GANESHA_MAJOR" ]]; then
        log_result "nfs-ganesha" "$EXPECTED_NFS_GANESHA" "$GANESHA_VERSION (Detected version: $ACTUAL_GANESHA_MAJOR)" "✅ PASS" "$SM_POD container"
    else
        log_result "nfs-ganesha" "$EXPECTED_NFS_GANESHA" "$GANESHA_VERSION (Detected version: $ACTUAL_GANESHA_MAJOR, Expected: $EXPECTED_GANESHA_MAJOR)" "❌ FAIL" "$SM_POD container"
    fi
fi

echo ""
echo "=========================================="
echo "Test completed!"
echo "Detailed results can be found at: $RESULT_FILE"
echo "=========================================="

# Statistics
PASS_COUNT=$(grep -c "✅ PASS" $RESULT_FILE)
FAIL_COUNT=$(grep -c "❌ FAIL" $RESULT_FILE)
SKIP_COUNT=$(grep -c "⚠️  SKIP" $RESULT_FILE)

echo ""
echo "Test Statistics:"
echo "Passed: $PASS_COUNT"
echo "Failed: $FAIL_COUNT"
echo "Skipped: $SKIP_COUNT"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo "🎉 All checked component versions match the specification!"
    exit 0
else
    echo "⚠️  $FAIL_COUNT component version(s) do not match the specification, please check test results."
    exit 1
fi