#!/bin/bash
#
# Based on: https://github.com/WebberHuang1118/misc-tools/blob/main/volumes/csi-mount/reproduce-mount-issue.sh
# Updated to work on SLES: instead of bind-mounting onto the broken symlink (which
# succeeds on SLES and overwrites it), we bind-mount the staging directory itself
# to produce EBUSY on cleanup, then create the broken symlink afterwards.
#
# Script to reproduce CSI mount issue with broken symlinks
# Simulates the scenario where mount fails with ENOENT and cleanup fails with EBUSY
#
# Usage:
#   sudo ./corrupt-csi-block-mount.sh [VOLUME_ID] [MODE]
#
# Modes:
#   corrupt - Create the corrupted state (no cleanup)
#   clean   - Clean up test volumes

set +e

# Parse arguments
VOLUME_ID="${1:-pvc-test-$(date +%s)}"
MODE="${2:-corrupt}"

# Validate mode
if [ "$MODE" != "corrupt" ] && [ "$MODE" != "clean" ]; then
    echo "ERROR: Invalid mode. Use 'corrupt' or 'clean'"
    echo "Usage: sudo $0 [VOLUME_ID] [MODE]"
    exit 1
fi

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Must run as root"
    exit 1
fi

STAGING_BASE="/var/lib/kubelet/plugins/kubernetes.io/csi/volumeDevices/staging"
STAGING_PATH="${STAGING_BASE}/${VOLUME_ID}"
TARGET_FILE="${STAGING_PATH}/${VOLUME_ID}"
FAKE_DEVICE="/dev/longhorn/${VOLUME_ID}"

# Clean mode
if [ "$MODE" = "clean" ]; then
    echo "Cleaning up volume: $VOLUME_ID"

    # Unmount if needed
    if mountpoint -q "$TARGET_FILE" 2>/dev/null; then
        echo "Unmounting $TARGET_FILE"
        umount -l "$TARGET_FILE" 2>/dev/null || true
    fi

    if mountpoint -q "$STAGING_PATH" 2>/dev/null; then
        echo "Unmounting $STAGING_PATH"
        umount -l "$STAGING_PATH" 2>/dev/null || true
    fi

    # Remove files
    rm -rf "$STAGING_PATH" 2>/dev/null || true
    rm -f "$FAKE_DEVICE" 2>/dev/null || true

    echo "Cleanup complete"
    exit 0
fi

# Corrupt mode - create the broken state
echo "Creating corrupted mount state for volume: $VOLUME_ID"
echo ""

# Create fake device
echo "1. Creating fake device: $FAKE_DEVICE"
mkdir -p /dev/longhorn
ln -sf /dev/zero "$FAKE_DEVICE"

# Create staging directory
echo "2. Creating staging directory: $STAGING_PATH"
mkdir -p "$STAGING_PATH"

# Bind mount the staging directory to itself to make cleanup fail with EBUSY
echo "3. Bind mounting staging directory to create busy state..."
mount --bind "$STAGING_PATH" "$STAGING_PATH" 2>&1 | head -1

# Create broken symlink (must be AFTER the bind mount so it's not destroyed)
echo "4. Creating broken symlink at: $TARGET_FILE"
ln -s "/nonexistent/path/file.$$" "$TARGET_FILE"

echo ""
echo "Corrupted state created."
echo ""
echo "Details:"
echo "  Volume ID: $VOLUME_ID"
echo "  Staging:   $STAGING_PATH"
echo "  Target:    $TARGET_FILE (broken symlink)"
echo "  Device:    $FAKE_DEVICE"
echo ""
echo "This state reproduces the production issue:"
echo "  - makeFile() succeeds (symlink exists)"
echo "  - mount --bind fails with: No such file or directory"
echo "  - os.Remove() may fail with: device or resource busy"
echo ""
echo "To verify:"
echo "  ls -la $TARGET_FILE"
echo "  file $TARGET_FILE"
echo "  mount | grep $VOLUME_ID"
echo ""
echo "To clean up:"
echo "  sudo $0 $VOLUME_ID clean"
echo ""
